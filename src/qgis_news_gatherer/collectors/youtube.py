# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Collectors for QGIS-related YouTube videos and Shorts.

YouTube has no free, key-less API for search, so this module parses the
``ytInitialData`` JSON blob embedded in the search results page. The parser
deliberately walks the whole document looking for known renderer keys rather
than following a fixed path: YouTube reshuffles the surrounding envelope
frequently, but the leaf renderers change far more slowly.

Two collectors share the parsing code:

* :class:`YouTubeVideosCollector` - long form videos (section ``youtube``)
* :class:`YouTubeShortsCollector` - Shorts (section ``youtube_shorts``)
"""

from __future__ import annotations

import contextlib
import json
import re
from collections.abc import Iterator
from datetime import date as date_type
from datetime import timedelta
from pathlib import Path
from typing import Any

from qgis_news_gatherer.collectors.base import (
    BaseCollector,
    CollectorResult,
    NewsItem,
    strip_emoji,
)
from qgis_news_gatherer.config import settings

# Renderer keys that describe a single long form video result.
VIDEO_RENDERERS = ("videoRenderer",)

# Renderer keys that describe a single Short. ``reelItemRenderer`` is the
# older shape; ``shortsLockupViewModel`` is the current one.
SHORT_RENDERERS = ("reelItemRenderer", "shortsLockupViewModel")

_ALL_RENDERERS = VIDEO_RENDERERS + SHORT_RENDERERS

# Shorts are capped at three minutes; anything at or under this that YouTube
# served from a /shorts/ URL is treated as a Short.
SHORT_MAX_SECONDS = 180

# Title/description keywords that mark a video as instructional content.
TUTORIAL_KEYWORDS = (
    "tutorial",
    "how to",
    "how-to",
    "howto",
    "guide",
    "walkthrough",
    "walk through",
    "getting started",
    "beginner",
    "beginners",
    "introduction to",
    "intro to",
    "learn",
    "lesson",
    "course",
    "step by step",
    "step-by-step",
    "tips and tricks",
    "explained",
    "demo",
    "workshop",
)

_RELATIVE_DATE_RE = re.compile(
    r"(\d+)\s*(second|minute|hour|day|week|month|year)s?\s+ago",
    re.IGNORECASE,
)

_UNIT_DAYS = {
    "second": 0,
    "minute": 0,
    "hour": 0,
    "day": 1,
    "week": 7,
    "month": 30,
    "year": 365,
}

_VIEW_COUNT_RE = re.compile(r"([\d][\d.,]*)\s*([KMB])?", re.IGNORECASE)

_MULTIPLIERS = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}


def extract_initial_data(html: str) -> dict[str, Any] | None:
    """Extract the ``ytInitialData`` JSON object from a YouTube page.

    Scans for the matching closing brace rather than using a regex, so
    braces inside string values cannot truncate the payload.

    Args:
        html: Raw HTML of a YouTube page.

    Returns:
        The decoded object, or None if it is absent or unparseable.
    """
    marker = re.search(r"ytInitialData\s*=\s*\{", html)
    if not marker:
        return None

    start = marker.end() - 1
    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(html)):
        char = html[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[start : index + 1])
                except json.JSONDecodeError:
                    return None
    return None


def iter_renderers(node: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(renderer_key, renderer)`` pairs found anywhere in ``node``.

    Walking the whole tree keeps the parser working when YouTube changes the
    shelf/section envelope around the individual results.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _ALL_RENDERERS and isinstance(value, dict):
                yield key, value
            else:
                yield from iter_renderers(value)
    elif isinstance(node, list):
        for entry in node:
            yield from iter_renderers(entry)


def node_text(value: Any) -> str:
    """Read a string out of any of YouTube's text node shapes."""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    if isinstance(value.get("simpleText"), str):
        return value["simpleText"]
    # viewModel style: {"content": "..."}
    if isinstance(value.get("content"), str):
        return value["content"]
    runs = value.get("runs")
    if isinstance(runs, list):
        return "".join(
            str(run.get("text", "")) for run in runs if isinstance(run, dict)
        )
    if isinstance(value.get("accessibilityText"), str):
        return value["accessibilityText"]
    return ""


def parse_view_count(text: str) -> int:
    """Parse a YouTube view count string into an integer.

    Handles ``"12,345 views"``, ``"1.2K views"``, ``"3.4M views"`` and
    ``"No views"``. Returns 0 when nothing parseable is present.
    """
    if not text:
        return 0
    match = _VIEW_COUNT_RE.search(text.strip())
    if not match:
        return 0

    number, suffix = match.group(1), match.group(2)
    if suffix:
        # "1.2K" - strip grouping commas, keep the decimal point.
        try:
            value = float(number.replace(",", ""))
        except ValueError:
            return 0
        return int(value * _MULTIPLIERS[suffix.lower()])

    try:
        return int(number.replace(",", "").replace(".", ""))
    except ValueError:
        return 0


def parse_duration(text: str) -> int | None:
    """Parse ``"M:SS"`` or ``"H:MM:SS"`` into seconds, or None."""
    if not text:
        return None
    parts = text.strip().split(":")
    if not all(part.isdigit() for part in parts) or not 2 <= len(parts) <= 3:
        return None
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return seconds


def parse_relative_date(text: str, today: date_type) -> date_type | None:
    """Convert ``"3 days ago"`` style text into an approximate date."""
    if not text:
        return None
    match = _RELATIVE_DATE_RE.search(text)
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2).lower()
    return today - timedelta(days=amount * _UNIT_DAYS[unit])


def is_tutorial(title: str, description: str = "") -> bool:
    """Return True when the title/description reads as instructional."""
    haystack = f"{title} {description}".lower()
    return any(keyword in haystack for keyword in TUTORIAL_KEYWORDS)


def history_path() -> Path:
    """Path of the cross-month YouTube counts file."""
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    return settings.cache_dir / "youtube_history.json"


def load_history() -> dict[str, dict[str, int]]:
    """Load per-month YouTube counts recorded by previous runs."""
    path = history_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        month: counts
        for month, counts in data.items()
        if isinstance(counts, dict)
    }


def record_history(month_key: str, counts: dict[str, int]) -> dict[str, dict[str, int]]:
    """Merge this month's counts into the history file and return it.

    The history file is what makes the month-on-month infographic possible:
    a single run only ever sees the current month, so each run leaves its
    counts behind for the next one.
    """
    history = load_history()
    existing = history.get(month_key, {})
    existing.update(counts)
    history[month_key] = existing
    with contextlib.suppress(OSError):
        history_path().write_text(json.dumps(history, indent=2, sort_keys=True))
    return history


def previous_month_key(month: date_type) -> str:
    """Return the ``YYYY-MM`` key of the month before ``month``."""
    first = month.replace(day=1)
    previous = first - timedelta(days=1)
    return previous.strftime("%Y-%m")


class _YouTubeSearchCollector(BaseCollector):
    """Shared search-page scraping for the video and Shorts collectors."""

    #: "Video" or "Short" - also used as the NewsItem category.
    kind = "Video"

    #: Number of content items kept in the report.
    max_items = 8

    @property
    def search_queries(self) -> list[str]:
        """Search terms to run for this collector."""
        return settings.youtube_search_queries

    @staticmethod
    def today() -> date_type:
        """Today's date. Overridable so tests can pin relative dates."""
        return date_type.today()

    def _search_url(self, query: str) -> str:
        """Build a search URL restricted to uploads from this month."""
        from urllib.parse import quote_plus

        return (
            f"{settings.youtube_search_url}?search_query={quote_plus(query)}"
            f"&sp={settings.youtube_search_filter}"
        )

    async def _fetch(self, query: str) -> dict[str, Any] | None:
        """Fetch one search page and return its ytInitialData."""
        response = await self.client.get(
            self._search_url(query),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        response.raise_for_status()
        return extract_initial_data(response.text)

    def _parse_video(self, renderer: dict[str, Any]) -> dict[str, Any] | None:
        """Build a raw record from a ``videoRenderer`` node."""
        video_id = renderer.get("videoId")
        title = node_text(renderer.get("title"))
        if not video_id or not title:
            return None

        length_text = node_text(renderer.get("lengthText"))
        duration = parse_duration(length_text)
        channel = node_text(renderer.get("ownerText")) or node_text(
            renderer.get("longBylineText")
        )
        published_text = node_text(renderer.get("publishedTimeText"))
        views = parse_view_count(
            node_text(renderer.get("viewCountText"))
            or node_text(renderer.get("shortViewCountText"))
        )
        description = node_text(renderer.get("detailedMetadataSnippets"))

        # A /shorts/ navigation URL or a sub-3-minute runtime means YouTube
        # served this as a Short even though it used the video renderer.
        nav_url = (
            renderer.get("navigationEndpoint", {})
            .get("commandMetadata", {})
            .get("webCommandMetadata", {})
            .get("url", "")
        )
        looks_short = "/shorts/" in nav_url or (
            duration is not None and duration <= SHORT_MAX_SECONDS
        )

        return {
            "video_id": video_id,
            "title": title,
            "channel": channel,
            "views": views,
            "published_text": published_text,
            "duration": duration,
            "description": description,
            "kind": "Short" if looks_short else "Video",
        }

    def _parse_short(
        self, key: str, renderer: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Build a raw record from a Shorts renderer node."""
        if key == "reelItemRenderer":
            video_id = renderer.get("videoId")
            title = node_text(renderer.get("headline"))
            views = parse_view_count(
                node_text(renderer.get("viewCountText"))
                or node_text(renderer.get("accessibility"))
            )
        else:  # shortsLockupViewModel
            video_id = (
                renderer.get("onTap", {})
                .get("innertubeCommand", {})
                .get("reelWatchEndpoint", {})
                .get("videoId", "")
            ) or renderer.get("videoId", "")
            overlay = renderer.get("overlayMetadata", {})
            title = node_text(overlay.get("primaryText")) or node_text(
                renderer.get("accessibilityText")
            )
            views = parse_view_count(node_text(overlay.get("secondaryText")))

        if not video_id or not title:
            return None

        return {
            "video_id": video_id,
            "title": title,
            # Shorts results carry no channel or upload date. They are only
            # ever surfaced by an upload-date-filtered search, so the month
            # is inferred rather than read.
            "channel": "",
            "views": views,
            "published_text": "",
            "duration": None,
            "description": "",
            "kind": "Short",
        }

    async def _gather_records(
        self, warnings: list[str]
    ) -> tuple[list[dict[str, Any]], int]:
        """Run every search query and return deduplicated raw records."""
        records: dict[str, dict[str, Any]] = {}
        parsed_pages = 0

        for query in self.search_queries:
            self.log_verbose(f"Searching YouTube for {query!r}...")
            try:
                data = await self._fetch(query)
            except Exception as error:  # network/HTTP problems on one query
                self.log_verbose(f"Query {query!r} failed: {error}")
                warnings.append(f"YouTube search for {query!r} failed")
                continue

            if data is None:
                warnings.append(f"Could not parse YouTube results for {query!r}")
                continue

            parsed_pages += 1
            for key, renderer in iter_renderers(data):
                if key in VIDEO_RENDERERS:
                    record = self._parse_video(renderer)
                else:
                    record = self._parse_short(key, renderer)
                if record and record["video_id"] not in records:
                    records[record["video_id"]] = record

        return list(records.values()), parsed_pages

    def _to_news_item(self, record: dict[str, Any]) -> NewsItem:
        """Convert a raw record into a NewsItem."""
        published = parse_relative_date(record["published_text"], self.today())
        estimated = published is None
        if estimated:
            # Upload-date-filtered search only returns this month's uploads.
            published = None

        title = strip_emoji(record["title"]).strip()
        channel = strip_emoji(record["channel"]).strip()
        tutorial = is_tutorial(title, record["description"])

        if record["kind"] == "Short":
            url = f"https://www.youtube.com/shorts/{record['video_id']}"
        else:
            url = f"https://www.youtube.com/watch?v={record['video_id']}"

        parts = []
        if channel:
            parts.append(f"by {channel}")
        if record["views"]:
            parts.append(f"{record['views']:,} views")
        if record["published_text"]:
            parts.append(record["published_text"])
        if tutorial:
            parts.append("Tutorial")

        return NewsItem(
            title=title,
            url=url,
            description=" · ".join(parts),
            date=published,
            author=channel or None,
            category=record["kind"],
            metadata={
                "video_id": record["video_id"],
                "kind": record["kind"],
                "views": record["views"],
                "channel": channel,
                "duration_seconds": record["duration"],
                "published_text": record["published_text"],
                "date_estimated": estimated,
                "is_tutorial": tutorial,
            },
        )

    def _in_target_window(self, item: NewsItem) -> bool:
        """Month filter that tolerates the missing dates on Shorts.

        Results come from an upload-date-filtered search, so an undated item
        is known to be recent but not which calendar month it lands in. Keep
        those only when the report targets the current month.
        """
        if item.date is not None:
            return self.is_in_month(item.date)
        today = self.today()
        return (
            self.config.month_start().year == today.year
            and self.config.month_start().month == today.month
        )

    def _summary_item(self, items: list[NewsItem]) -> NewsItem:
        """Build the infographic item for this section.

        Carries the counts for this month plus the recorded counts for
        previous months, which :mod:`qgis_news_gatherer.charts` renders as a
        month-on-month grouped bar chart.
        """
        month_key = self.config.target_month.strftime("%Y-%m")
        tutorials = sum(1 for i in items if i.metadata.get("is_tutorial"))
        total_views = sum(i.metadata.get("views", 0) for i in items)
        count_key = "shorts" if self.kind == "Short" else "videos"
        tutorial_key = "short_tutorials" if self.kind == "Short" else "tutorials"

        history = record_history(
            month_key,
            {count_key: len(items), tutorial_key: tutorials},
        )

        previous = history.get(previous_month_key(self.config.target_month), {})
        previous_count = previous.get(count_key)
        previous_tutorials = previous.get(tutorial_key)

        noun = "Shorts" if self.kind == "Short" else "videos"
        tutorial_noun = "tutorial" if tutorials == 1 else "tutorials"

        return NewsItem(
            title=f"{len(items)} QGIS {noun} published this month",
            description=(
                f"{len(items)} {noun} · {tutorials} {tutorial_noun} · "
                f"{total_views:,} views"
            ),
            category="summary",
            metadata={
                "metric": "youtube_summary",
                "kind": self.kind,
                "count": len(items),
                "tutorials": tutorials,
                "total_views": total_views,
                "previous_count": previous_count,
                "previous_tutorials": previous_tutorials,
                "count_key": count_key,
                "tutorial_key": tutorial_key,
                "history": history,
            },
        )

    async def collect(self) -> CollectorResult:
        """Search YouTube and build this section's items."""
        warnings: list[str] = []
        records, parsed_pages = await self._gather_records(warnings)

        if parsed_pages == 0:
            return CollectorResult(
                section_name=self.section_name,
                section_title=self.section_title,
                items=[],
                error="Could not parse any YouTube search results",
                warnings=warnings,
            )

        items = [
            self._to_news_item(record)
            for record in records
            if record["kind"] == self.kind
        ]
        items = [item for item in items if self._in_target_window(item)]

        # Most watched first, and flag the standouts for the report.
        items.sort(key=lambda i: i.metadata.get("views", 0), reverse=True)
        items = items[: self.max_items]
        # Only flag standouts when there is a field to stand out from -
        # badging every card in a three item section says nothing.
        highlight_count = settings.youtube_highlight_count
        if len(items) <= highlight_count:
            highlight_count = 0
        for index, item in enumerate(items):
            item.metadata["highlight"] = index < highlight_count

        self.log_verbose(f"Found {len(items)} {self.kind.lower()} items")

        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=[*items, self._summary_item(items)] if items else [],
            warnings=warnings,
        )


class YouTubeVideosCollector(_YouTubeSearchCollector):
    """Collect QGIS-related long form YouTube videos for the month."""

    section_name = "youtube"
    section_title = "QGIS on YouTube"
    kind = "Video"

    @property
    def max_items(self) -> int:
        return settings.youtube_max_videos


class YouTubeShortsCollector(_YouTubeSearchCollector):
    """Collect QGIS-related YouTube Shorts for the month."""

    section_name = "youtube_shorts"
    section_title = "QGIS Shorts"
    kind = "Short"

    @property
    def max_items(self) -> int:
        return settings.youtube_max_shorts

    @property
    def search_queries(self) -> list[str]:
        """Shorts need their own query set to surface reliably."""
        return settings.youtube_shorts_search_queries
