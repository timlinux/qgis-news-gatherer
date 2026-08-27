# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Collectors for Mastodon posts and Planet QGIS blog posts.

YouTube collection lives in :mod:`qgis_news_gatherer.collectors.youtube`.
"""

import re
from datetime import datetime
from time import mktime

import feedparser

from qgis_news_gatherer.collectors.base import (
    BaseCollector,
    CollectorResult,
    NewsItem,
    strip_emoji,
)


class MastodonCollector(BaseCollector):
    """Collect top QGIS mentions on Mastodon by engagement."""

    section_name = "mastodon"
    section_title = "QGIS on Mastodon"

    # Instances popular in the GIS/FOSS community
    INSTANCES = [
        "fosstodon.org",
        "mastodon.social",
        "mapstodon.space",
    ]

    async def collect(self) -> CollectorResult:
        """Fetch QGIS-tagged posts from Mastodon instances."""
        self.log_verbose("Fetching QGIS posts from Mastodon...")

        all_posts: list[NewsItem] = []
        warnings: list[str] = []
        seen_urls: set[str] = set()

        for instance in self.INSTANCES:
            try:
                url = f"https://{instance}/api/v1/timelines/tag/qgis?limit=40"
                response = await self.client.get(
                    url,
                    headers={"User-Agent": "QGIS-News-Gatherer/1.0"},
                    timeout=15,
                )
                if response.status_code != 200:
                    self.log_verbose(f"{instance} returned {response.status_code}")
                    continue

                posts = response.json()
                for post in posts:
                    created = post.get("created_at", "")
                    post_date = None
                    if created:
                        try:
                            post_date = datetime.fromisoformat(
                                created.replace("Z", "+00:00")
                            ).date()
                        except (ValueError, TypeError):
                            pass

                    if not self.is_in_month(post_date):
                        continue

                    post_url = post.get("url", "")
                    if post_url in seen_urls:
                        continue
                    seen_urls.add(post_url)

                    acct = post.get("account", {}).get("acct", "")
                    display_name = post.get("account", {}).get("display_name", acct)
                    boosts = post.get("reblogs_count", 0)
                    favs = post.get("favourites_count", 0)
                    replies = post.get("replies_count", 0)
                    engagement = boosts + favs + replies

                    # Strip HTML and color-emoji glyphs from content. Color
                    # emoji are pulled from Noto Color Emoji at full glyph
                    # size and break the inline card layout.
                    content = re.sub(r"<[^>]+>", "", post.get("content", ""))
                    content = strip_emoji(content)
                    content = re.sub(r"\s+", " ", content).strip()[:200]

                    all_posts.append(
                        NewsItem(
                            title=f"@{acct}",
                            url=post_url,
                            description=content,
                            date=post_date,
                            author=display_name,
                            category="Mastodon",
                            metadata={
                                "boosts": boosts,
                                "favourites": favs,
                                "replies": replies,
                                "engagement": engagement,
                                "instance": instance,
                            },
                        )
                    )
            except Exception as e:
                self.log_verbose(f"Error fetching from {instance}: {e}")

        # Sort by engagement, take top 5
        all_posts.sort(
            key=lambda x: x.metadata.get("engagement", 0), reverse=True
        )
        items = all_posts[:5]

        # Enrich descriptions with engagement stats. Plain text only \u2014
        # rendered inline with body type, color-emoji glyphs blow up to
        # full size and break the card layout.
        for item in items:
            meta = item.metadata
            stats = (
                f"{meta.get('favourites', 0)} favs \u00b7 "
                f"{meta.get('boosts', 0)} boosts \u00b7 "
                f"{meta.get('replies', 0)} replies"
            )
            item.description = f"{stats} | {item.description}"

        self.log_verbose(f"Found {len(items)} top Mastodon posts")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )


class PlanetCollector(BaseCollector):
    """Collect blog posts from Planet QGIS (planet.qgis.org)."""

    section_name = "planet"
    section_title = "Blogosphere"

    FEED_URL = "https://planet.qgis.org/index.xml"

    async def collect(self) -> CollectorResult:
        """Fetch and parse Planet QGIS RSS feed."""
        self.log_verbose(f"Fetching Planet QGIS feed from {self.FEED_URL}...")

        response = await self.client.get(self.FEED_URL)
        response.raise_for_status()

        feed = feedparser.parse(response.text)
        items: list[NewsItem] = []
        warnings: list[str] = []

        if feed.bozo:
            warnings.append(f"Feed parsing warning: {feed.bozo_exception}")

        for entry in feed.entries:
            pub_date = None
            try:
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime.fromtimestamp(
                        mktime(entry.published_parsed)
                    ).date()
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    pub_date = datetime.fromtimestamp(
                        mktime(entry.updated_parsed)
                    ).date()
            except (ValueError, OverflowError, OSError):
                continue

            if not self.is_in_month(pub_date):
                continue

            author = None
            if hasattr(entry, "author"):
                author = entry.author
            elif hasattr(entry, "source") and hasattr(entry.source, "title"):
                author = entry.source.title

            description = None
            if hasattr(entry, "summary"):
                description = re.sub(r"<[^>]+>", "", entry.summary)[:300]

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

        self.log_verbose(f"Found {len(items)} Planet QGIS posts in target month")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )
