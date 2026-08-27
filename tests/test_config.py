"""Tests for configuration module."""

from datetime import date

import pytest

from qgis_news_gatherer.config import ReportConfig, Settings


class TestSettings:
    """Tests for Settings class."""

    def test_default_settings(self) -> None:
        """Test that default settings are loaded."""
        settings = Settings()
        assert settings.github_api_url == "https://api.github.com"
        assert settings.qgis_repo == "qgis/QGIS"

    def test_github_headers_without_token(self) -> None:
        """Test GitHub headers when no token is set."""
        settings = Settings(github_token=None)
        headers = settings.get_github_headers()
        assert "Authorization" not in headers
        assert "Accept" in headers

    def test_github_headers_with_token(self) -> None:
        """Test GitHub headers when token is set."""
        settings = Settings(github_token="test-token")
        headers = settings.get_github_headers()
        assert headers["Authorization"] == "Bearer test-token"


class TestReportConfig:
    """Tests for ReportConfig class."""

    def test_default_month(self) -> None:
        """Test that default month is current month."""
        config = ReportConfig()
        today = date.today()
        assert config.target_month.year == today.year
        assert config.target_month.month == today.month
        assert config.target_month.day == 1

    def test_custom_month(self) -> None:
        """Test setting a custom target month."""
        target = date(2026, 3, 15)
        config = ReportConfig(target_month=target)
        assert config.target_month == target

    def test_month_start(self) -> None:
        """Test month_start returns first day of month."""
        config = ReportConfig(target_month=date(2026, 3, 15))
        assert config.month_start() == date(2026, 3, 1)

    def test_month_end(self) -> None:
        """Test month_end returns last day of month."""
        config = ReportConfig(target_month=date(2026, 3, 15))
        assert config.month_end() == date(2026, 3, 31)

    def test_month_end_february(self) -> None:
        """Test month_end for February."""
        config = ReportConfig(target_month=date(2024, 2, 1))  # Leap year
        assert config.month_end() == date(2024, 2, 29)

    def test_month_end_december(self) -> None:
        """Test month_end for December (year boundary)."""
        config = ReportConfig(target_month=date(2026, 12, 1))
        assert config.month_end() == date(2026, 12, 31)

    def test_default_sections(self) -> None:
        """Test default sections list."""
        config = ReportConfig()
        sections = config.sections
        assert "releases" in sections
        assert "notable_fixes" in sections

    def test_custom_sections(self) -> None:
        """Test custom sections list."""
        config = ReportConfig(sections=["releases", "news_feed"])
        assert config.sections == ["releases", "news_feed"]

    def test_available_sections(self) -> None:
        """Test available_sections returns dict with descriptions."""
        sections = ReportConfig.available_sections()
        assert isinstance(sections, dict)
        assert "releases" in sections
        assert isinstance(sections["releases"], str)

    def test_to_dict(self) -> None:
        """Test configuration serialization."""
        config = ReportConfig(
            target_month=date(2026, 3, 1),
            sections=["releases"],
            verbose=True,
        )
        data = config.to_dict()
        assert data["target_month"] == "2026-03-01"
        assert data["sections"] == ["releases"]
        assert data["verbose"] is True
