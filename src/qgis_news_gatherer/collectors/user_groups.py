# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Collector for QGIS user group updates."""

import re
from datetime import datetime

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem
from qgis_news_gatherer.config import settings


class UserGroupsCollector(BaseCollector):
    """Collect QGIS user group updates from qgis.org and the website repo."""

    section_name = "user_groups"
    section_title = "User Groups"

    GROUPS_PAGE_URL = "https://raw.githubusercontent.com/qgis/QGIS-Website/main/content/community/groups.md"
    GROUPS_WEB_URL = "https://qgis.org/community/groups/"

    async def collect(self) -> CollectorResult:
        """Fetch user group data and detect changes."""
        self.log_verbose("Fetching user group data...")

        items: list[NewsItem] = []
        warnings: list[str] = []

        # 1. Parse the groups markdown from GitHub for structured data
        groups, year_sections = await self._parse_groups_markdown()

        if not groups:
            return CollectorResult(
                section_name=self.section_name,
                section_title=self.section_title,
                error="Could not parse user groups data",
            )

        # Count stats
        active_groups = [g for g in groups if not g.get("removed")]
        removed_groups = [g for g in groups if g.get("removed")]
        countries = {g["country"] for g in active_groups if g.get("country")}

        # Build the per-year distribution for charting
        year_distribution: dict[str, int] = {}
        for g in active_groups:
            year = g.get("registered_year") or "Unknown"
            year_distribution[year] = year_distribution.get(year, 0) + 1

        # Add summary item
        items.append(
            NewsItem(
                title=f"{len(active_groups)} Active QGIS User Groups worldwide",
                url=self.GROUPS_WEB_URL,
                description=(
                    f"QGIS has {len(active_groups)} active user groups "
                    f"across {len(countries)} countries. "
                    f"{len(removed_groups)} group(s) have been removed."
                ),
                category="summary",
                metadata={
                    "metric": "user_groups_summary",
                    "total_active": len(active_groups),
                    "total_countries": len(countries),
                    "total_removed": len(removed_groups),
                    "year_distribution": year_distribution,
                },
            )
        )

        # 2. Find groups registered in the target year
        target_year = str(self.config.target_month.year)
        new_this_year = [
            g for g in active_groups if g.get("registered_year") == target_year
        ]
        for group in new_this_year:
            items.append(
                NewsItem(
                    title=group["name"] or "Unknown",
                    url=group.get("url"),
                    description=(
                        f"Registered {target_year}"
                        + (f" · Contact: {group['contact']}" if group.get("contact") else "")
                    ),
                    category="new_group",
                    tags=["new", target_year],
                    metadata={
                        "icon": group.get("icon", ""),
                        "country": group.get("country", ""),
                        "contact": group.get("contact", ""),
                        "registered_year": target_year,
                    },
                )
            )

        # 3. Check for recent changes to the groups page via GitHub commits
        await self._check_groups_page_changes(items, warnings)

        # 4. Check user group websites for recent blog posts / activity
        await self._check_group_websites(active_groups, items, warnings)

        self.log_verbose(f"Found {len(items)} user group items")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )

    async def _parse_groups_markdown(
        self,
    ) -> tuple[list[dict], dict[str, list[dict]]]:
        """Parse the groups.md file from GitHub to extract structured data."""
        response = await self.client.get(self.GROUPS_PAGE_URL)
        response.raise_for_status()
        content = response.text

        groups: list[dict] = []
        year_sections: dict[str, list[dict]] = {}

        # Split the file into sections by the "### Registered YYYY..." and
        # "### Removed" headings so we can attribute multi-line shortcodes
        # to the right year. Splitting on the heading is more robust than
        # walking line-by-line because each shortcode spans several lines.
        section_re = re.compile(
            r"^###\s+(Registered\s+\d{4}(?:\s+or\s+earlier)?|Removed.*)$",
            re.MULTILINE | re.IGNORECASE,
        )
        positions = [(m.start(), m.group(1)) for m in section_re.finditer(content)]
        positions.append((len(content), ""))

        shortcode_re = re.compile(
            r"\{\{<\s*rich-list\s+(.*?)\s*>\}\}", re.DOTALL
        )

        for (start, heading), (end, _) in zip(positions[:-1], positions[1:]):
            year_match = re.search(r"(\d{4})", heading)
            is_removed = heading.lower().startswith("removed")
            current_year = year_match.group(1) if year_match else ""
            block = content[start:end]

            for sc in shortcode_re.finditer(block):
                group = self._parse_shortcode_attrs(sc.group(1))
                group["registered_year"] = current_year
                group["removed"] = is_removed
                group["country"] = self._extract_country(group.get("name", ""))
                groups.append(group)
                year_sections.setdefault(current_year, []).append(group)

        return groups, year_sections

    @staticmethod
    def _parse_shortcode_attrs(attrs_str: str) -> dict:
        """Parse Hugo shortcode attributes into a dict."""
        result = {}
        # Match key = "value" pairs, tolerating whitespace around =.
        for match in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', attrs_str):
            key = match.group(1)
            value = match.group(2).strip()
            if key == "listLink":
                result["url"] = value if value.startswith("http") else f"https://{value}"
            elif key == "listTitle":
                result["name"] = value
            elif key == "listSubtitle":
                contact = value.replace("Contact:", "").strip()
                result["contact"] = contact
            elif key == "icon":
                result["icon"] = value
        return result

    @staticmethod
    def _extract_country(name: str) -> str:
        """Extract country from group name."""
        # Common patterns: "QGIS user group Switzerland", "QGIS Brasil"
        name_lower = name.lower()
        # Remove common prefixes
        for prefix in [
            "qgis user group", "qgis users group", "qgis usergroup",
            "qgis anwendergruppe", "gruppo degli utenti italiani di qgis",
            "groupe des utilisateurs de qgis", "asociación",
            "asociación qgis", "grupo de usuarios qgis",
            "komunitas pengguna qgis", "polska grupa użytkowników qgis",
            "asociația utilizatorilor qgis", "association of qgis users in",
            "qgis brugergruppe", "qgis gebruikersgroep",
        ]:
            if name_lower.startswith(prefix):
                return name[len(prefix):].strip().strip("()")

        # Try extracting from "QGIS Country" pattern
        if name_lower.startswith("qgis "):
            rest = name[5:].strip()
            # Remove parenthetical
            rest = re.sub(r"\s*\(.*?\)", "", rest)
            return rest

        return name

    async def _check_groups_page_changes(
        self, items: list[NewsItem], warnings: list[str]
    ) -> None:
        """Check for recent commits to the groups page in the website repo."""
        month_start = self.config.month_start().isoformat()
        month_end = self.config.month_end().isoformat()

        url = (
            f"{settings.github_api_url}/repos/{settings.qgis_website_repo}"
            f"/commits"
        )
        params = {
            "path": "content/community/groups.md",
            "since": f"{month_start}T00:00:00Z",
            "until": f"{month_end}T23:59:59Z",
        }

        try:
            response = await self.client.get(
                url, params=params, headers=settings.get_github_headers()
            )
            response.raise_for_status()
            commits = response.json()

            for commit in commits:
                message = commit.get("commit", {}).get("message", "")
                first_line = message.split("\n")[0]
                commit_date_str = (
                    commit.get("commit", {}).get("committer", {}).get("date")
                )
                commit_date = None
                if commit_date_str:
                    commit_date = datetime.fromisoformat(
                        commit_date_str.replace("Z", "+00:00")
                    ).date()

                items.append(
                    NewsItem(
                        title=f"Groups page updated: {first_line}",
                        url=commit.get("html_url"),
                        description=f"Change to the QGIS user groups page",
                        date=commit_date,
                        author=commit.get("commit", {})
                        .get("author", {})
                        .get("name"),
                        category="update",
                    )
                )
        except Exception as e:
            self.log_verbose(f"Could not fetch groups page commits: {e}")

    async def _check_group_websites(
        self,
        groups: list[dict],
        items: list[NewsItem],
        warnings: list[str],
    ) -> None:
        """Check a selection of user group websites for recent activity."""
        # Known user group RSS/blog feeds to check
        known_feeds = {
            "qgis.ch": "https://qgis.ch/feed/",
            "qgis.de": "https://qgis.de/feed/",
            "qgis.nl": "https://qgis.nl/feed/",
            "qgis.se": "https://qgis.se/feed/",
            "qgis.at": "https://qgis.at/feed/",
            "qgis.it": "https://qgis.it/feed/",
            "qgis.no": "https://qgis.no/feed/",
            "osgeo.fr": "https://www.osgeo.fr/feed/",
        }

        import feedparser

        for domain, feed_url in known_feeds.items():
            try:
                response = await self.client.get(
                    feed_url, timeout=httpx.Timeout(10)
                )
                if response.status_code != 200:
                    continue

                feed = feedparser.parse(response.text)
                for entry in feed.entries[:5]:
                    # Check if published in the target month
                    published = entry.get("published_parsed") or entry.get(
                        "updated_parsed"
                    )
                    if not published:
                        continue

                    entry_date = datetime(
                        *published[:6]
                    ).date()

                    if self.is_in_month(entry_date):
                        group_name = None
                        for g in groups:
                            if g.get("url") and domain in g["url"]:
                                group_name = g.get("name", domain)
                                break

                        items.append(
                            NewsItem(
                                title=entry.get("title", "Untitled"),
                                url=entry.get("link"),
                                description=entry.get("summary", "")[:200]
                                if entry.get("summary")
                                else None,
                                date=entry_date,
                                author=group_name or domain,
                                category="group_activity",
                                tags=[domain],
                            )
                        )
            except Exception:
                # Silently skip unreachable feeds
                continue
