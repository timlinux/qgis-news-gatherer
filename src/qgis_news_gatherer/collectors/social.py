"""Collectors for YouTube, Mastodon, and Planet QGIS blog posts."""

import re
from datetime import datetime
from time import mktime

import feedparser

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem
from qgis_news_gatherer.config import settings


class YouTubeCollector(BaseCollector):
    """Collect QGIS-related YouTube videos published this month."""

    section_name = "youtube"
    section_title = "QGIS on YouTube"

    async def collect(self) -> CollectorResult:
        """Search YouTube for recent QGIS videos."""
        self.log_verbose("Searching YouTube for QGIS videos...")

        # YouTube search sorted by upload date, filtered to videos only
        # sp=CAISBAgCEAE= means sort by upload date, filter to videos
        url = (
            "https://www.youtube.com/results"
            "?search_query=QGIS"
            "&sp=CAISBAgCEAE%3D"
        )
        response = await self.client.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        response.raise_for_status()

        items: list[NewsItem] = []
        warnings: list[str] = []

        match = re.search(r"ytInitialData\s*=\s*(\{.*?\});", response.text)
        if not match:
            warnings.append("Could not parse YouTube search results")
            return CollectorResult(
                section_name=self.section_name,
                section_title=self.section_title,
                items=items,
                warnings=warnings,
            )

        import json
        data = json.loads(match.group(1))
        contents = (
            data.get("contents", {})
            .get("twoColumnSearchResultsRenderer", {})
            .get("primaryContents", {})
            .get("sectionListRenderer", {})
            .get("contents", [])
        )

        for section in contents:
            for item in section.get("itemSectionRenderer", {}).get("contents", []):
                vid = item.get("videoRenderer", {})
                if not vid:
                    continue

                title = vid.get("title", {}).get("runs", [{}])[0].get("text", "")
                vid_id = vid.get("videoId", "")
                pub_text = vid.get("publishedTimeText", {}).get("simpleText", "")
                views_text = vid.get("viewCountText", {}).get("simpleText", "")
                channel = vid.get("ownerText", {}).get("runs", [{}])[0].get("text", "")

                if not vid_id or not title:
                    continue

                # Filter: only include videos from roughly this month
                # pub_text is like "2 days ago", "1 week ago", "3 weeks ago", "1 month ago"
                # We include anything up to ~5 weeks old
                if any(x in pub_text.lower() for x in ["month", "year"]):
                    num = re.search(r"(\d+)", pub_text)
                    if num and int(num.group(1)) > 1:
                        continue

                video_url = f"https://www.youtube.com/watch?v={vid_id}"

                # Parse view count for engagement sorting
                view_count = 0
                if views_text:
                    num_match = re.search(r"([\d,]+)", views_text.replace(",", ""))
                    if num_match:
                        try:
                            view_count = int(num_match.group(1).replace(",", ""))
                        except ValueError:
                            pass

                items.append(
                    NewsItem(
                        title=title,
                        url=video_url,
                        description=f"by {channel} | {views_text} | {pub_text}",
                        author=channel,
                        category="YouTube",
                        metadata={
                            "video_id": vid_id,
                            "views": view_count,
                            "published_text": pub_text,
                            "channel": channel,
                        },
                    )
                )

                if len(items) >= 10:
                    break
            if len(items) >= 10:
                break

        # Sort by view count (highest engagement first)
        items.sort(key=lambda x: x.metadata.get("views", 0), reverse=True)

        self.log_verbose(f"Found {len(items)} YouTube videos")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
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

                    # Strip HTML from content for description
                    content = re.sub(r"<[^>]+>", "", post.get("content", ""))
                    content = content[:200]

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

        # Enrich descriptions with engagement stats
        for item in items:
            meta = item.metadata
            stats = (
                f"\u2764 {meta.get('favourites', 0)} "
                f"\U0001f501 {meta.get('boosts', 0)} "
                f"\U0001f4ac {meta.get('replies', 0)}"
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
