"""Collector for QGIS sustaining members."""

import asyncio
from datetime import datetime

from bs4 import BeautifulSoup

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem


class SustainingMembersCollector(BaseCollector):
    """Collect QGIS sustaining member updates from members.qgis.org."""

    section_name = "sustaining_members"
    section_title = "Sustaining Members"

    MEMBERS_URL = "https://members.qgis.org/en/members/list/"
    BASE_URL = "https://members.qgis.org"

    async def collect(self) -> CollectorResult:
        """Fetch sustaining members and identify new additions."""
        self.log_verbose("Fetching sustaining members...")

        items: list[NewsItem] = []
        warnings: list[str] = []

        # Fetch the members list page
        response = await self.client.get(self.MEMBERS_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        # Parse all members from the page
        all_members = self._parse_members_list(soup)

        # Add summary
        counts = {}
        for m in all_members:
            level = m.get("level", "Unknown")
            counts[level] = counts.get(level, 0) + 1

        summary_parts = [f"{v} {k}" for k, v in counts.items()]
        items.append(
            NewsItem(
                title=f"{len(all_members)} sustaining members",
                url=self.MEMBERS_URL,
                description=(
                    f"Current sustaining members: {', '.join(summary_parts)}"
                ),
                category="summary",
                metadata={
                    "total": len(all_members),
                    "by_level": counts,
                },
            )
        )

        # Fetch detail pages to find members added in the target month
        # Check all members concurrently (limited batch)
        new_members = await self._find_new_members(all_members)

        for member in new_members:
            logo_url = member.get("logo", "")
            if logo_url and not logo_url.startswith("http"):
                logo_url = f"{self.BASE_URL}{logo_url}"

            items.append(
                NewsItem(
                    title=f"New {member['level']} member: {member['name']}",
                    url=member.get("website") or member.get("detail_url"),
                    description=(
                        f"{member.get('country', '')}. "
                        f"Joined {member.get('start_date', 'recently')}."
                    ),
                    date=member.get("start_date_parsed"),
                    category="new_member",
                    tags=[member.get("level", "").lower()],
                    metadata={
                        "level": member.get("level"),
                        "country": member.get("country"),
                        "logo_url": logo_url,
                        "website": member.get("website"),
                        "start_date": member.get("start_date"),
                    },
                )
            )

        self.log_verbose(f"Found {len(items)} member items ({len(new_members)} new)")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )

    def _parse_members_list(self, soup: BeautifulSoup) -> list[dict]:
        """Parse the members list page to extract all members."""
        members = []
        current_level = ""

        for h3 in soup.find_all("h3"):
            text = h3.get_text(strip=True)

            # Level headings
            if text in ["Flagship", "Large", "Medium", "Small"]:
                current_level = text
                continue
            if text == "List of Current Sustaining Members":
                continue

            member: dict = {"name": text, "level": current_level}

            # Check if h3 is inside an <a> tag (link to detail page)
            parent_a = h3.find_parent("a")
            if parent_a:
                href = parent_a.get("href", "")
                if href:
                    member["detail_url"] = (
                        f"{self.BASE_URL}{href}"
                        if href.startswith("/")
                        else href
                    )

                # Logo image
                img = parent_a.find("img")
                if img and img.get("src"):
                    member["logo"] = img["src"]

                # Country from subtitle
                subtitle = parent_a.find("article")
                if subtitle:
                    member["country"] = subtitle.get_text(strip=True)

            members.append(member)

        return members

    async def _find_new_members(self, members: list[dict]) -> list[dict]:
        """Check member detail pages to find those added in the target month."""
        new_members = []

        # Process in batches to avoid overwhelming the server
        batch_size = 10
        for i in range(0, len(members), batch_size):
            batch = members[i : i + batch_size]
            tasks = [
                self._check_member_date(m) for m in batch if m.get("detail_url")
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, dict) and result.get("is_new"):
                    new_members.append(result)

        return new_members

    async def _check_member_date(self, member: dict) -> dict:
        """Fetch a member's detail page and check their start date."""
        try:
            response = await self.client.get(member["detail_url"])
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # Extract start date and website from the detail page
            page_text = soup.get_text()

            # Find "Start Date:" field
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if text.startswith("Start Date:"):
                    date_str = text.replace("Start Date:", "").strip()
                    member["start_date"] = date_str
                    try:
                        # Parse "Jan. 1, 2026" format
                        parsed = datetime.strptime(
                            date_str.replace(".", ""), "%b %d, %Y"
                        ).date()
                        member["start_date_parsed"] = parsed
                        if self.is_in_month(parsed):
                            member["is_new"] = True
                    except ValueError:
                        pass

                elif text.startswith("Website:"):
                    url = text.replace("Website:", "").strip()
                    if url:
                        member["website"] = url

        except Exception:
            pass

        return member
