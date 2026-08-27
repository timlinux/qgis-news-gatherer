# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for the YouTube video and Shorts collectors."""

import json
from datetime import date

import httpx
import pytest

from qgis_news_gatherer.collectors.youtube import (
    YouTubeShortsCollector,
    YouTubeVideosCollector,
    extract_initial_data,
    is_tutorial,
    iter_renderers,
    node_text,
    parse_duration,
    parse_relative_date,
    parse_view_count,
    previous_month_key,
)
from qgis_news_gatherer.config import ReportConfig, settings


def _video_renderer(
    video_id: str,
    title: str,
    length: str = "12:34",
    published: str = "3 days ago",
    views: str = "1,234 views",
    channel: str = "QGIS Channel",
) -> dict:
    """Build a videoRenderer node shaped like YouTube's search response."""
    return {
        "videoRenderer": {
            "videoId": video_id,
            "title": {"runs": [{"text": title}]},
            "lengthText": {"simpleText": length},
            "publishedTimeText": {"simpleText": published},
            "viewCountText": {"simpleText": views},
            "ownerText": {"runs": [{"text": channel}]},
            "navigationEndpoint": {
                "commandMetadata": {
                    "webCommandMetadata": {"url": f"/watch?v={video_id}"}
                }
            },
        }
    }


def _shorts_lockup(video_id: str, title: str, views: str = "5.2K views") -> dict:
    """Build a shortsLockupViewModel node (current Shorts shape)."""
    return {
        "shortsLockupViewModel": {
            "onTap": {
                "innertubeCommand": {"reelWatchEndpoint": {"videoId": video_id}}
            },
            "overlayMetadata": {
                "primaryText": {"content": title},
                "secondaryText": {"content": views},
            },
        }
    }


def _reel_item(video_id: str, title: str, views: str = "900 views") -> dict:
    """Build a reelItemRenderer node (legacy Shorts shape)."""
    return {
        "reelItemRenderer": {
            "videoId": video_id,
            "headline": {"simpleText": title},
            "viewCountText": {"simpleText": views},
        }
    }


def _search_page(*nodes: dict) -> str:
    """Wrap renderer nodes in a page body containing ytInitialData."""
    payload = {
        "contents": {
            "twoColumnSearchResultsRenderer": {
                "primaryContents": {
                    "sectionListRenderer": {
                        "contents": [{"itemSectionRenderer": {"contents": list(nodes)}}]
                    }
                }
            }
        }
    }
    return (
        "<html><script>var ytInitialData = "
        + json.dumps(payload)
        + ";</script></html>"
    )


class TestParsingHelpers:
    """Tests for the standalone parsing helpers."""

    def test_extract_initial_data(self) -> None:
        """Test ytInitialData extraction from a page body."""
        data = extract_initial_data(_search_page(_video_renderer("abc", "Hello")))
        assert data is not None
        assert "contents" in data

    def test_extract_initial_data_survives_braces_in_strings(self) -> None:
        """Braces inside string values must not truncate the payload."""
        html = 'var ytInitialData = {"title": "a }; b", "ok": true};</script>'
        data = extract_initial_data(html)
        assert data == {"title": "a }; b", "ok": True}

    def test_extract_initial_data_missing(self) -> None:
        """Test a page with no ytInitialData."""
        assert extract_initial_data("<html>nothing here</html>") is None

    def test_iter_renderers_finds_nested_nodes(self) -> None:
        """Renderers are found regardless of the surrounding envelope."""
        page = {"a": {"b": [{"c": _video_renderer("x", "T")}, _shorts_lockup("y", "S")]}}
        found = dict(iter_renderers(page))
        assert set(found) == {"videoRenderer", "shortsLockupViewModel"}

    def test_node_text_shapes(self) -> None:
        """Test every text node shape YouTube uses."""
        assert node_text({"simpleText": "plain"}) == "plain"
        assert node_text({"runs": [{"text": "a"}, {"text": "b"}]}) == "ab"
        assert node_text({"content": "viewmodel"}) == "viewmodel"
        assert node_text({"accessibilityText": "alt"}) == "alt"
        assert node_text(None) == ""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("12,345 views", 12345),
            ("1.2K views", 1200),
            ("3.4M views", 3400000),
            ("1 view", 1),
            ("No views", 0),
            ("", 0),
        ],
    )
    def test_parse_view_count(self, text: str, expected: int) -> None:
        """Test view count parsing across YouTube's formats."""
        assert parse_view_count(text) == expected

    @pytest.mark.parametrize(
        ("text", "expected"),
        [("0:45", 45), ("12:34", 754), ("1:02:03", 3723), ("LIVE", None), ("", None)],
    )
    def test_parse_duration(self, text: str, expected: int | None) -> None:
        """Test duration parsing."""
        assert parse_duration(text) == expected

    def test_parse_relative_date(self) -> None:
        """Test relative upload date parsing."""
        today = date(2026, 8, 20)
        assert parse_relative_date("3 days ago", today) == date(2026, 8, 17)
        assert parse_relative_date("2 weeks ago", today) == date(2026, 8, 6)
        assert parse_relative_date("1 hour ago", today) == today
        assert parse_relative_date("", today) is None
        assert parse_relative_date("Streamed live", today) is None

    def test_is_tutorial(self) -> None:
        """Test tutorial classification."""
        assert is_tutorial("QGIS Tutorial: Buffers") is True
        assert is_tutorial("How to georeference in QGIS") is True
        assert is_tutorial("QGIS 4.0 release announcement") is False

    def test_previous_month_key(self) -> None:
        """Test previous-month key derivation, including year rollover."""
        assert previous_month_key(date(2026, 8, 1)) == "2026-07"
        assert previous_month_key(date(2026, 1, 15)) == "2025-12"


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Point the collector cache and history file at a temp directory."""
    monkeypatch.setattr(settings, "cache_dir", tmp_path)
    return tmp_path


def _collector(
    cls,
    page: str,
    month: date = date(2026, 8, 1),
    today: date = date(2026, 8, 20),
):
    """Build a collector whose HTTP client serves a canned search page."""
    collector = cls(ReportConfig(target_month=month))
    collector.today = lambda: today
    collector._client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=page)
        )
    )
    return collector


class TestYouTubeVideosCollector:
    """Tests for the long form video collector."""

    @pytest.mark.asyncio
    async def test_collects_videos_only(self, isolated_cache) -> None:
        """Long form videos are collected; Shorts are left to the other section."""
        page = _search_page(
            _video_renderer("v1", "QGIS 4.0 tour", views="5,000 views"),
            _video_renderer("v2", "QGIS Tutorial: joins", views="900 views"),
            _shorts_lockup("s1", "Quick QGIS tip"),
        )
        collector = _collector(YouTubeVideosCollector, page)
        result = await collector.collect()
        await collector.close()

        videos = [i for i in result.items if i.category == "Video"]
        assert [i.metadata["video_id"] for i in videos] == ["v1", "v2"]
        assert all("watch?v=" in i.url for i in videos)
        assert videos[1].metadata["is_tutorial"] is True
        assert videos[0].date == date(2026, 8, 17)
        # Too few items for "most watched" to mean anything.
        assert all(i.metadata["highlight"] is False for i in videos)

    @pytest.mark.asyncio
    async def test_top_videos_highlighted(self, isolated_cache) -> None:
        """The most watched videos are flagged once there is a field to lead."""
        page = _search_page(
            *(
                _video_renderer(f"v{n}", f"QGIS video {n}", views=f"{n},000 views")
                for n in range(1, 6)
            )
        )
        collector = _collector(YouTubeVideosCollector, page)
        result = await collector.collect()
        await collector.close()

        videos = [i for i in result.items if i.category == "Video"]
        flags = [i.metadata["highlight"] for i in videos]
        assert flags == [True, True, True, False, False]
        # Highest view count first.
        assert videos[0].metadata["views"] == 5000

    @pytest.mark.asyncio
    async def test_emits_summary_item(self, isolated_cache) -> None:
        """A summary item carries the counts that drive the infographic."""
        page = _search_page(
            _video_renderer("v1", "QGIS Tutorial: joins"),
            _video_renderer("v2", "QGIS news"),
        )
        collector = _collector(YouTubeVideosCollector, page)
        result = await collector.collect()
        await collector.close()

        summary = [i for i in result.items if i.category == "summary"]
        assert len(summary) == 1
        meta = summary[0].metadata
        assert meta["metric"] == "youtube_summary"
        assert meta["count"] == 2
        assert meta["tutorials"] == 1
        assert "2026-08" in meta["history"]

    @pytest.mark.asyncio
    async def test_previous_month_count_from_history(
        self, isolated_cache, monkeypatch
    ) -> None:
        """Counts recorded by an earlier run drive the month-on-month delta."""
        (isolated_cache / "youtube_history.json").write_text(
            json.dumps({"2026-07": {"videos": 5, "tutorials": 2}})
        )
        collector = _collector(
            YouTubeVideosCollector, _search_page(_video_renderer("v1", "QGIS news"))
        )
        result = await collector.collect()
        await collector.close()

        summary = next(i for i in result.items if i.category == "summary")
        assert summary.metadata["previous_count"] == 5

    @pytest.mark.asyncio
    async def test_unparseable_page_is_an_error(self, isolated_cache) -> None:
        """A page without ytInitialData surfaces as a collector error."""
        collector = _collector(YouTubeVideosCollector, "<html>blocked</html>")
        result = await collector.collect()
        await collector.close()

        assert result.success is False
        assert result.items == []

    @pytest.mark.asyncio
    async def test_old_videos_excluded(self, isolated_cache) -> None:
        """Videos published outside the target month are dropped."""
        page = _search_page(
            _video_renderer("old", "QGIS retrospective", published="4 months ago")
        )
        collector = _collector(YouTubeVideosCollector, page)
        result = await collector.collect()
        await collector.close()

        assert result.items == []


class TestYouTubeShortsCollector:
    """Tests for the Shorts collector."""

    @pytest.mark.asyncio
    async def test_collects_both_shorts_shapes(
        self, isolated_cache, monkeypatch
    ) -> None:
        """Both the viewModel and legacy reel shapes are parsed."""
        page = _search_page(
            _shorts_lockup("s1", "Quick QGIS tip", views="5.2K views"),
            _reel_item("s2", "QGIS how to buffer", views="900 views"),
            _video_renderer("v1", "Long QGIS talk"),
        )
        collector = _collector(YouTubeShortsCollector, page)
        result = await collector.collect()
        await collector.close()

        shorts = [i for i in result.items if i.category == "Short"]
        assert [i.metadata["video_id"] for i in shorts] == ["s1", "s2"]
        assert all("/shorts/" in i.url for i in shorts)
        assert shorts[0].metadata["views"] == 5200

    @pytest.mark.asyncio
    async def test_short_video_renderer_counted_as_short(
        self, isolated_cache, monkeypatch
    ) -> None:
        """A sub-3-minute videoRenderer is treated as a Short."""
        page = _search_page(_video_renderer("v1", "QGIS in 60 seconds", length="0:58"))
        collector = _collector(YouTubeShortsCollector, page)
        result = await collector.collect()
        await collector.close()

        assert [i.metadata["video_id"] for i in result.items if i.category == "Short"] == [
            "v1"
        ]

    @pytest.mark.asyncio
    async def test_undated_shorts_dropped_for_past_months(
        self, isolated_cache, monkeypatch
    ) -> None:
        """Shorts carry no date, so they are only kept for the current month."""
        collector = _collector(
            YouTubeShortsCollector,
            _search_page(_shorts_lockup("s1", "Quick QGIS tip")),
            month=date(2026, 5, 1),
        )
        result = await collector.collect()
        await collector.close()

        assert result.items == []
