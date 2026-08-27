"""Configuration management for QGIS News Gatherer."""

from datetime import date
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API tokens
    github_token: str | None = Field(
        default=None,
        description="GitHub personal access token for increased rate limits",
    )
    transifex_token: str | None = Field(
        default=None,
        description="Transifex API token for translation statistics",
    )

    # Output settings
    output_format: str = Field(
        default="markdown",
        description="Output format: markdown, json, or terminal",
    )
    output_file: Path | None = Field(
        default=None,
        description="Output file path (stdout if not specified)",
    )

    # Cache settings
    cache_dir: Path = Field(
        default=Path.home() / ".cache" / "qgis-news-gatherer",
        description="Directory for caching API responses",
    )
    cache_ttl_hours: int = Field(
        default=1,
        description="Cache time-to-live in hours",
    )

    # Request settings
    request_timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds",
    )
    max_concurrent_requests: int = Field(
        default=5,
        description="Maximum concurrent HTTP requests",
    )

    # GitHub settings
    github_api_url: str = Field(
        default="https://api.github.com",
        description="GitHub API base URL",
    )
    qgis_repo: str = Field(
        default="qgis/QGIS",
        description="Main QGIS repository",
    )
    qgis_website_repo: str = Field(
        default="qgis/QGIS-Website",
        description="QGIS Website repository",
    )
    qgis_qeps_repo: str = Field(
        default="qgis/QGIS-Enhancement-Proposals",
        description="QGIS Enhancement Proposals repository",
    )

    # Feed URLs
    qgis_blog_feed: str = Field(
        default="https://blog.qgis.org/feed/",
        description="QGIS blog RSS feed URL",
    )
    qgis_planet_feed: str = Field(
        default="https://plugins.qgis.org/planet/feed/atom/",
        description="QGIS Planet feed URL",
    )
    feed_qgis_url: str = Field(
        default="https://feed.qgis.org/?json=1",
        description="feed.qgis.org JSON URL",
    )

    # Other URLs
    changelog_url: str = Field(
        default="https://changelog.qgis.org/en/qgis/",
        description="QGIS changelog URL",
    )
    analytics_url: str = Field(
        default="https://analytics.qgis.org",
        description="QGIS analytics URL",
    )
    conference_url: str = Field(
        default="https://uc2025.qgis.org",
        description="QGIS User Conference URL",
    )
    mailing_list_url: str = Field(
        default="https://lists.osgeo.org/pipermail/qgis-user/",
        description="QGIS mailing list archive URL",
    )

    def get_github_headers(self) -> dict[str, str]:
        """Get headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers


class ReportConfig:
    """Configuration for report generation."""

    def __init__(
        self,
        target_month: date | None = None,
        sections: list[str] | None = None,
        verbose: bool = False,
    ):
        self.target_month = target_month or date.today().replace(day=1)
        self.sections = sections or self.default_sections()
        self.verbose = verbose

    @staticmethod
    def default_sections() -> list[str]:
        """Return the default list of sections to include."""
        return [
            "releases",
            "notable_fixes",
            "merged_prs",
            "grant_proposals",
            "conferences",
            "news_feed",
            "blog_posts",
            "planet",
            "website_updates",
            "qeps",
            "mailing_lists",
            "user_groups",
            "sustaining_members",
            "analytics",
            "plugin_stats",
            "youtube",
            "mastodon",
            "psc_minutes",
            "translations",
            "discussions",
        ]

    @staticmethod
    def available_sections() -> dict[str, str]:
        """Return available sections with descriptions."""
        return {
            "releases": "QGIS releases and changelog",
            "notable_fixes": "Notable bug fixes from merged PRs",
            "merged_prs": "Key merged pull requests (features, improvements)",
            "grant_proposals": "Grant program updates",
            "conferences": "Conference and event announcements",
            "news_feed": "Items from feed.qgis.org",
            "blog_posts": "Posts from blog.qgis.org",
            "website_updates": "QGIS website repository changes",
            "qeps": "QGIS Enhancement Proposals",
            "mailing_lists": "Mailing list highlights",
            "user_groups": "User group updates, new groups, and activities",
            "sustaining_members": "New and current sustaining members",
            "analytics": "QGIS usage analytics from feed.qgis.org",
            "plugin_stats": "Plugin download statistics from plugins.qgis.org",
            "planet": "Community blog posts from Planet QGIS",
            "youtube": "QGIS-related YouTube videos",
            "mastodon": "Top QGIS mentions on Mastodon",
            "psc_minutes": "Project Steering Committee minutes",
            "translations": "Translation statistics",
            "discussions": "GitHub Discussions highlights",
        }

    def month_start(self) -> date:
        """Return the first day of the target month."""
        return self.target_month.replace(day=1)

    def month_end(self) -> date:
        """Return the last day of the target month."""
        if self.target_month.month == 12:
            next_month = self.target_month.replace(year=self.target_month.year + 1, month=1, day=1)
        else:
            next_month = self.target_month.replace(month=self.target_month.month + 1, day=1)
        from datetime import timedelta

        return next_month - timedelta(days=1)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "target_month": self.target_month.isoformat(),
            "sections": self.sections,
            "verbose": self.verbose,
        }


# Global settings instance
settings = Settings()
