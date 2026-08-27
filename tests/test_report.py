"""Tests for report and show notes generation."""

import json
from datetime import date

import pytest

from qgis_news_gatherer.collectors.base import CollectorResult, NewsItem
from qgis_news_gatherer.report import ShowNotesGenerator


class TestShowNotesGenerator:
    """Tests for ShowNotesGenerator class."""

    def test_add_result(self) -> None:
        """Test adding results to the report."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        result = CollectorResult(
            section_name="test",
            section_title="Test Section",
            items=[NewsItem(title="Item 1")],
        )
        report.add_result(result)
        assert len(report.results) == 1

    def test_format_timestamp_minutes(self) -> None:
        """Test timestamp formatting for minutes."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        assert report._format_timestamp(0) == "0:00"
        assert report._format_timestamp(65) == "1:05"
        assert report._format_timestamp(600) == "10:00"

    def test_format_timestamp_hours(self) -> None:
        """Test timestamp formatting for hours."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        assert report._format_timestamp(3600) == "1:00:00"
        assert report._format_timestamp(3665) == "1:01:05"
        assert report._format_timestamp(7200) == "2:00:00"

    def test_calculate_chapters(self) -> None:
        """Test chapter calculation."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        report.add_result(
            CollectorResult(
                section_name="releases",
                section_title="Releases",
                items=[NewsItem(title="v1.0")],
            )
        )
        chapters = report._calculate_chapters()

        assert len(chapters) >= 2  # At least intro and outro
        assert chapters[0]["title"] == "Introduction"
        assert chapters[-1]["title"] == "Wrap-up & Next Month"

    def test_calculate_chapters_includes_sections(self) -> None:
        """Test that chapters include sections with content."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        report.add_result(
            CollectorResult(
                section_name="releases",
                section_title="Releases",
                items=[NewsItem(title="v1.0")],
            )
        )
        report.add_result(
            CollectorResult(
                section_name="empty",
                section_title="Empty Section",
                items=[],
            )
        )

        chapters = report._calculate_chapters()
        chapter_titles = [ch["title"] for ch in chapters]

        assert "Releases" in chapter_titles
        assert "Empty Section" not in chapter_titles

    def test_collect_all_links(self) -> None:
        """Test link collection and deduplication."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        report.add_result(
            CollectorResult(
                section_name="test",
                section_title="Test",
                items=[
                    NewsItem(title="Item 1", url="https://example.com/1"),
                    NewsItem(title="Item 2", url="https://example.com/2"),
                    NewsItem(title="Item 3", url="https://example.com/1"),  # Duplicate
                ],
            )
        )

        links = report._collect_all_links()
        assert len(links) == 2  # Deduped

    def test_generate_youtube_description(self) -> None:
        """Test YouTube description generation."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        report.add_result(
            CollectorResult(
                section_name="releases",
                section_title="Releases",
                items=[NewsItem(title="QGIS 3.40", url="https://qgis.org")],
            )
        )

        desc = report.generate_youtube_description()

        assert "March 2026" in desc
        assert "CHAPTERS" in desc
        assert "LINKS" in desc
        assert "qgis.org" in desc
        assert "Kartoza" in desc

    def test_generate_markdown_shownotes(self) -> None:
        """Test markdown show notes generation."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        report.add_result(
            CollectorResult(
                section_name="releases",
                section_title="Releases",
                items=[
                    NewsItem(
                        title="QGIS 3.40",
                        url="https://qgis.org",
                        description="New release",
                        date=date(2026, 3, 15),
                    )
                ],
            )
        )

        md = report.generate_markdown_shownotes()

        assert "# QGIS Monthly News Show Notes - March 2026" in md
        assert "## Video Chapters" in md
        assert "## Releases" in md
        assert "### Talking Points" in md
        assert "QGIS 3.40" in md
        assert "YouTube Description" in md

    def test_generate_markdown_with_error(self) -> None:
        """Test markdown generation handles errors."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        report.add_result(
            CollectorResult(
                section_name="test",
                section_title="Test Section",
                error="Something went wrong",
            )
        )

        md = report.generate_markdown_shownotes()
        assert "Error" in md
        assert "Something went wrong" in md

    def test_generate_markdown_footer(self) -> None:
        """Test markdown includes Kartoza footer."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        md = report.generate_markdown_shownotes()
        assert "Kartoza" in md
        assert "kartoza.com" in md

    def test_generate_json(self) -> None:
        """Test JSON report generation."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        report.add_result(
            CollectorResult(
                section_name="test",
                section_title="Test Section",
                items=[NewsItem(title="Item 1", url="https://example.com")],
            )
        )

        json_str = report.generate_json()
        data = json.loads(json_str)

        assert data["target_month"] == "2026-03-01"
        assert "chapters" in data
        assert "sections" in data
        assert "all_links" in data
        assert "youtube_description" in data
        assert data["summary"]["total_items"] == 1

    def test_generate_html(self) -> None:
        """Test HTML generation."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        report.add_result(
            CollectorResult(
                section_name="releases",
                section_title="Releases",
                items=[NewsItem(title="QGIS 3.40")],
            )
        )

        html = report.generate_html()

        assert "<!DOCTYPE html>" in html
        assert "QGIS Monthly News" in html
        assert "March 2026" in html
        assert "Releases" in html
        assert "QGIS 3.40" in html
        assert "Kartoza" in html

    def test_custom_chapter_timing(self) -> None:
        """Test setting custom section duration."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        report.set_chapter_timing("releases", 300)  # 5 minutes
        assert report.section_durations["releases"] == 300

    def test_add_custom_chapter(self) -> None:
        """Test adding custom chapter markers."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        report.add_custom_chapter("Sponsor Message", 120, "Thank our sponsors")

        assert len(report.custom_chapters) == 1
        assert report.custom_chapters[0]["title"] == "Sponsor Message"
        assert report.custom_chapters[0]["timestamp_seconds"] == 120

    def test_chapters_sorted_by_timestamp(self) -> None:
        """Test that chapters are sorted by timestamp."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        report.add_result(
            CollectorResult(
                section_name="releases",
                section_title="Releases",
                items=[NewsItem(title="v1.0")],
            )
        )
        report.add_custom_chapter("Mid-video Message", 30)

        chapters = report._calculate_chapters()

        timestamps = [ch["timestamp_seconds"] for ch in chapters]
        assert timestamps == sorted(timestamps)

    def test_summary_statistics(self) -> None:
        """Test summary statistics in markdown."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        report.add_result(
            CollectorResult(
                section_name="success",
                section_title="Success",
                items=[NewsItem(title="Item 1"), NewsItem(title="Item 2")],
            )
        )
        report.add_result(
            CollectorResult(
                section_name="error",
                section_title="Error",
                error="Failed",
            )
        )

        md = report.generate_markdown_shownotes()

        assert "Total Items:** 2" in md
        assert "Sources:** 1/2" in md

    def test_json_summary_statistics(self) -> None:
        """Test JSON report summary statistics."""
        report = ShowNotesGenerator(date(2026, 3, 1))
        report.add_result(
            CollectorResult(
                section_name="success",
                section_title="Success",
                items=[NewsItem(title="Item 1"), NewsItem(title="Item 2")],
            )
        )
        report.add_result(
            CollectorResult(
                section_name="error",
                section_title="Error",
                error="Failed",
            )
        )

        json_str = report.generate_json()
        data = json.loads(json_str)

        assert data["summary"]["total_sections"] == 2
        assert data["summary"]["successful_sections"] == 1
        assert data["summary"]["total_items"] == 2


class TestBackwardsCompatibility:
    """Test backwards compatibility with old API."""

    def test_report_generator_alias(self) -> None:
        """Test that ReportGenerator alias works."""
        from qgis_news_gatherer.report import ReportGenerator

        report = ReportGenerator(date(2026, 3, 1))
        assert isinstance(report, ShowNotesGenerator)
