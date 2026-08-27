# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Conference and event information collector."""

import re
from datetime import datetime

from bs4 import BeautifulSoup

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem
from qgis_news_gatherer.config import settings


class ConferencesCollector(BaseCollector):
    """Collect QGIS conference and event information."""

    section_name = "conferences"
    section_title = "Conferences & Events"

    async def collect(self) -> CollectorResult:
        """Scrape conference websites for event information."""
        self.log_verbose("Fetching conference information...")

        items: list[NewsItem] = []
        warnings: list[str] = []

        # Try to fetch from conference URL
        try:
            await self._collect_from_conference_site(items)
        except Exception as e:
            warnings.append(f"Could not fetch conference site: {e}")

        # Also check the blog for conference announcements
        try:
            await self._collect_from_blog(items)
        except Exception as e:
            warnings.append(f"Could not fetch conference posts from blog: {e}")

        self.log_verbose(f"Found {len(items)} conference/event items")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )

    async def _collect_from_conference_site(self, items: list[NewsItem]) -> None:
        """Scrape the QGIS conference website."""
        response = await self.client.get(settings.conference_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Look for event details
        title = soup.find("title")
        main_title = title.get_text(strip=True) if title else "QGIS User Conference"

        # Try to find dates
        date_patterns = [
            r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
            r"(\w+ \d{1,2}(?:-\d{1,2})?,? \d{4})",
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        ]

        page_text = soup.get_text()
        event_dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, page_text)
            event_dates.extend(matches[:5])  # Limit matches

        # Look for location
        location = None
        location_elem = soup.find(class_=re.compile(r"location|venue|place"))
        if location_elem:
            location = location_elem.get_text(strip=True)

        # Look for registration info
        registration = soup.find(
            ["a", "button"], string=re.compile(r"register|sign up|tickets", re.I)
        )
        registration_url = registration.get("href") if registration else None

        description_parts = []
        if event_dates:
            description_parts.append(f"Dates: {', '.join(event_dates[:3])}")
        if location:
            description_parts.append(f"Location: {location}")

        items.append(
            NewsItem(
                title=main_title,
                url=settings.conference_url,
                description=" | ".join(description_parts) if description_parts else None,
                category="Conference",
                metadata={
                    "dates": event_dates[:5] if event_dates else [],
                    "location": location,
                    "registration_url": registration_url,
                },
            )
        )

        # Look for program/schedule items
        schedule_section = soup.find(id=re.compile(r"program|schedule|agenda"))
        if schedule_section:
            for item in schedule_section.find_all(["li", "div", "article"])[:10]:
                item_text = item.get_text(strip=True)
                if len(item_text) > 20:
                    items.append(
                        NewsItem(
                            title=item_text[:200],
                            url=settings.conference_url,
                            category="Conference Program",
                        )
                    )

    async def _collect_from_blog(self, items: list[NewsItem]) -> None:
        """Check QGIS blog for conference-related posts."""
        import feedparser

        response = await self.client.get(settings.qgis_blog_feed)
        response.raise_for_status()

        feed = feedparser.parse(response.text)

        conference_keywords = [
            "conference",
            "user conference",
            "contributor meeting",
            "hackfest",
            "foss4g",
            "event",
            "meetup",
            "workshop",
        ]

        for entry in feed.entries:
            title = entry.get("title", "").lower()
            summary = entry.get("summary", "").lower()

            if any(kw in title or kw in summary for kw in conference_keywords):
                from time import mktime

                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime.fromtimestamp(mktime(entry.published_parsed)).date()

                if self.is_in_month(pub_date):
                    items.append(
                        NewsItem(
                            title=entry.get("title", "Conference Update"),
                            url=entry.get("link"),
                            description=entry.get("summary", "")[:300],
                            date=pub_date,
                            category="Conference Announcement",
                        )
                    )
