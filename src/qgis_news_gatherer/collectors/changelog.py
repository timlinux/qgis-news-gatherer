# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Changelog scraper for changelog.qgis.org."""

import re
from datetime import datetime

from bs4 import BeautifulSoup

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem
from qgis_news_gatherer.config import settings


class ChangelogCollector(BaseCollector):
    """Collect changelog entries from changelog.qgis.org."""

    section_name = "changelog"
    section_title = "Changelog Highlights"

    async def collect(self) -> CollectorResult:
        """Scrape changelog.qgis.org for recent changes."""
        self.log_verbose(f"Fetching changelog from {settings.changelog_url}...")

        response = await self.client.get(settings.changelog_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        items: list[NewsItem] = []
        warnings: list[str] = []

        # Find version sections
        version_sections = soup.find_all("div", class_="release") or soup.find_all(
            "section", class_="release"
        )

        if not version_sections:
            # Try alternative structure
            version_sections = soup.find_all("div", id=re.compile(r"version-\d+"))

        for section in version_sections:
            # Extract version info
            version_header = section.find(["h1", "h2", "h3"])
            if not version_header:
                continue

            version_text = version_header.get_text(strip=True)
            version_match = re.search(r"(\d+\.\d+(?:\.\d+)?)", version_text)
            version = version_match.group(1) if version_match else version_text

            # Try to find release date
            release_date = None
            date_elem = section.find(class_=re.compile(r"date|release-date"))
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                try:
                    release_date = datetime.strptime(date_text, "%Y-%m-%d").date()
                except ValueError:
                    try:
                        release_date = datetime.strptime(date_text, "%B %d, %Y").date()
                    except ValueError:
                        pass

            # Find feature entries
            feature_lists = section.find_all("ul", class_=re.compile(r"feature|changelog"))
            if not feature_lists:
                feature_lists = section.find_all("ul")

            for feature_list in feature_lists[:3]:  # Limit to first 3 lists per version
                for li in feature_list.find_all("li", recursive=False)[:10]:  # Limit items
                    feature_text = li.get_text(strip=True)
                    if len(feature_text) < 10:  # Skip very short entries
                        continue

                    link = li.find("a")
                    url = link.get("href") if link else None

                    # Check if this entry is in our target month
                    # If we can't determine the date, include it if version seems recent
                    if release_date and not self.is_in_month(release_date):
                        continue

                    items.append(
                        NewsItem(
                            title=feature_text[:200],
                            url=url if url and url.startswith("http") else None,
                            date=release_date,
                            category=f"QGIS {version}",
                            metadata={"version": version},
                        )
                    )

        # Also try to get recent changelog entries from the main page
        if not items:
            # Alternative parsing for different page structure
            entries = soup.find_all("article") or soup.find_all("div", class_="entry")
            for entry in entries[:20]:
                title_elem = entry.find(["h1", "h2", "h3", "h4"])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.find("a")
                    url = link.get("href") if link else None

                    items.append(
                        NewsItem(
                            title=title,
                            url=url,
                            category="Changelog",
                        )
                    )

        if not items:
            warnings.append(
                "Could not parse changelog structure - page format may have changed"
            )

        self.log_verbose(f"Found {len(items)} changelog entries")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )
