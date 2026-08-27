# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for collector modules."""

from datetime import date, datetime

import pytest

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem
from qgis_news_gatherer.config import ReportConfig


class TestNewsItem:
    """Tests for NewsItem dataclass."""

    def test_basic_item(self) -> None:
        """Test creating a basic news item."""
        item = NewsItem(title="Test Item")
        assert item.title == "Test Item"
        assert item.url is None
        assert item.tags == []

    def test_full_item(self) -> None:
        """Test creating a fully populated news item."""
        item = NewsItem(
            title="Test Item",
            url="https://example.com",
            description="A test description",
            date=date(2026, 3, 15),
            author="tester",
            category="Test",
            tags=["test", "example"],
            metadata={"key": "value"},
        )
        assert item.title == "Test Item"
        assert item.url == "https://example.com"
        assert item.author == "tester"
        assert "test" in item.tags

    def test_to_dict(self) -> None:
        """Test NewsItem serialization."""
        item = NewsItem(
            title="Test",
            date=date(2026, 3, 15),
            tags=["tag1"],
        )
        data = item.to_dict()
        assert data["title"] == "Test"
        assert data["date"] == "2026-03-15"
        assert data["tags"] == ["tag1"]


class TestCollectorResult:
    """Tests for CollectorResult dataclass."""

    def test_successful_result(self) -> None:
        """Test a successful result."""
        result = CollectorResult(
            section_name="test",
            section_title="Test Section",
            items=[NewsItem(title="Item 1")],
        )
        assert result.success is True
        assert result.has_items is True
        assert len(result.items) == 1

    def test_error_result(self) -> None:
        """Test an error result."""
        result = CollectorResult(
            section_name="test",
            section_title="Test Section",
            error="Something went wrong",
        )
        assert result.success is False
        assert result.has_items is False

    def test_empty_result(self) -> None:
        """Test an empty result."""
        result = CollectorResult(
            section_name="test",
            section_title="Test Section",
        )
        assert result.success is True
        assert result.has_items is False

    def test_to_dict(self) -> None:
        """Test CollectorResult serialization."""
        result = CollectorResult(
            section_name="test",
            section_title="Test Section",
            items=[NewsItem(title="Item")],
            warnings=["Warning 1"],
        )
        data = result.to_dict()
        assert data["section_name"] == "test"
        assert data["success"] is True
        assert data["item_count"] == 1
        assert "Warning 1" in data["warnings"]


class TestBaseCollector:
    """Tests for BaseCollector class."""

    def test_is_in_month_with_date(self) -> None:
        """Test is_in_month with date object."""
        config = ReportConfig(target_month=date(2026, 3, 1))

        class TestCollector(BaseCollector):
            section_name = "test"
            section_title = "Test"

            async def collect(self) -> CollectorResult:
                return CollectorResult(
                    section_name=self.section_name,
                    section_title=self.section_title,
                )

        collector = TestCollector(config)

        # In month
        assert collector.is_in_month(date(2026, 3, 15)) is True
        assert collector.is_in_month(date(2026, 3, 1)) is True
        assert collector.is_in_month(date(2026, 3, 31)) is True

        # Out of month
        assert collector.is_in_month(date(2026, 2, 28)) is False
        assert collector.is_in_month(date(2026, 4, 1)) is False
        assert collector.is_in_month(None) is False

    def test_is_in_month_with_datetime(self) -> None:
        """Test is_in_month with datetime object."""
        config = ReportConfig(target_month=date(2026, 3, 1))

        class TestCollector(BaseCollector):
            section_name = "test"
            section_title = "Test"

            async def collect(self) -> CollectorResult:
                return CollectorResult(
                    section_name=self.section_name,
                    section_title=self.section_title,
                )

        collector = TestCollector(config)

        assert collector.is_in_month(datetime(2026, 3, 15, 12, 30)) is True
        assert collector.is_in_month(datetime(2026, 2, 15, 12, 30)) is False
