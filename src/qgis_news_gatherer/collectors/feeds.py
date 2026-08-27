# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""RSS and JSON feed collectors."""

from datetime import datetime
from time import mktime

import feedparser

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem
from qgis_news_gatherer.config import settings


class BlogFeedCollector(BaseCollector):
    """Collect posts from the QGIS blog RSS feed."""

    section_name = "blog_posts"
    section_title = "Blog Posts"

    async def collect(self) -> CollectorResult:
        """Fetch and parse QGIS blog RSS feed."""
        self.log_verbose(f"Fetching blog feed from {settings.qgis_blog_feed}...")

        response = await self.client.get(settings.qgis_blog_feed)
        response.raise_for_status()

        feed = feedparser.parse(response.text)
        items: list[NewsItem] = []
        warnings: list[str] = []

        if feed.bozo:
            warnings.append(f"Feed parsing warning: {feed.bozo_exception}")

        for entry in feed.entries:
            # Parse publication date
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime.fromtimestamp(mktime(entry.published_parsed)).date()
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub_date = datetime.fromtimestamp(mktime(entry.updated_parsed)).date()

            if self.is_in_month(pub_date):
                # Extract author
                author = None
                if hasattr(entry, "author"):
                    author = entry.author
                elif hasattr(entry, "authors") and entry.authors:
                    author = entry.authors[0].get("name")

                # Extract tags/categories
                tags = []
                if hasattr(entry, "tags"):
                    tags = [tag.term for tag in entry.tags if hasattr(tag, "term")]

                # Get summary/description
                description = None
                if hasattr(entry, "summary"):
                    description = entry.summary[:500]
                elif hasattr(entry, "description"):
                    description = entry.description[:500]

                items.append(
                    NewsItem(
                        title=entry.get("title", "Untitled"),
                        url=entry.get("link"),
                        description=description,
                        date=pub_date,
                        author=author,
                        tags=tags,
                        category="Blog",
                    )
                )

        self.log_verbose(f"Found {len(items)} blog posts in target month")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )


class NewsFeedCollector(BaseCollector):
    """Collect items from feed.qgis.org (sketches JSON)."""

    section_name = "news_feed"
    section_title = "News Feed"

    async def collect(self) -> CollectorResult:
        """Fetch feed.qgis.org JSON data."""
        self.log_verbose(f"Fetching news feed from {settings.feed_qgis_url}...")

        response = await self.client.get(settings.feed_qgis_url)
        response.raise_for_status()

        data = response.json()
        items: list[NewsItem] = []

        # The feed.qgis.org sketches endpoint returns different structure
        # Try to parse whatever format we get
        sketches = data if isinstance(data, list) else data.get("sketches", data.get("items", []))

        for sketch in sketches:
            # Handle various possible date formats
            pub_date = None
            date_str = sketch.get("date") or sketch.get("published") or sketch.get("created")
            if date_str:
                try:
                    if "T" in str(date_str):
                        pub_date = datetime.fromisoformat(
                            str(date_str).replace("Z", "+00:00")
                        ).date()
                    else:
                        pub_date = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    self.log_verbose(f"Could not parse date: {date_str}")

            if self.is_in_month(pub_date):
                items.append(
                    NewsItem(
                        title=sketch.get("title") or sketch.get("name", "Untitled"),
                        url=sketch.get("url") or sketch.get("link"),
                        description=sketch.get("description") or sketch.get("summary"),
                        date=pub_date,
                        author=sketch.get("author"),
                        category="News Feed",
                        metadata=sketch.get("metadata", {}),
                    )
                )

        self.log_verbose(f"Found {len(items)} news items in target month")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
        )


class PlanetFeedCollector(BaseCollector):
    """Collect posts from QGIS Planet (community blogs)."""

    section_name = "planet"
    section_title = "Planet QGIS"

    async def collect(self) -> CollectorResult:
        """Fetch and parse QGIS Planet feed."""
        self.log_verbose(f"Fetching planet feed from {settings.qgis_planet_feed}...")

        response = await self.client.get(settings.qgis_planet_feed)
        response.raise_for_status()

        feed = feedparser.parse(response.text)
        items: list[NewsItem] = []
        warnings: list[str] = []

        if feed.bozo:
            warnings.append(f"Feed parsing warning: {feed.bozo_exception}")

        for entry in feed.entries:
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime.fromtimestamp(mktime(entry.published_parsed)).date()
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub_date = datetime.fromtimestamp(mktime(entry.updated_parsed)).date()

            if self.is_in_month(pub_date):
                author = None
                if hasattr(entry, "author"):
                    author = entry.author
                elif hasattr(entry, "source") and hasattr(entry.source, "title"):
                    author = entry.source.title

                description = None
                if hasattr(entry, "summary"):
                    description = entry.summary[:500]

                items.append(
                    NewsItem(
                        title=entry.get("title", "Untitled"),
                        url=entry.get("link"),
                        description=description,
                        date=pub_date,
                        author=author,
                        category="Planet",
                    )
                )

        self.log_verbose(f"Found {len(items)} planet posts in target month")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )
