"""Mailing list archive collector."""

import re
from datetime import datetime

from bs4 import BeautifulSoup

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem
from qgis_news_gatherer.config import settings


class MailingListsCollector(BaseCollector):
    """Collect highlights from QGIS mailing list archives."""

    section_name = "mailing_lists"
    section_title = "Mailing List Highlights"

    # Month name mapping
    MONTH_NAMES = {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    }

    async def collect(self) -> CollectorResult:
        """Scrape OSGeo mailing list archives."""
        self.log_verbose("Fetching mailing list archives...")

        items: list[NewsItem] = []
        warnings: list[str] = []

        # Construct archive URL for target month
        month_name = self.MONTH_NAMES[self.config.target_month.month]
        year = self.config.target_month.year
        archive_url = f"{settings.mailing_list_url}{year}-{month_name}/thread.html"

        self.log_verbose(f"Checking archive: {archive_url}")

        try:
            response = await self.client.get(archive_url)
            if response.status_code == 404:
                warnings.append(f"Archive not found for {month_name} {year}")
                return CollectorResult(
                    section_name=self.section_name,
                    section_title=self.section_title,
                    items=items,
                    warnings=warnings,
                )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Find thread list - structure varies by mail archive software
            thread_list = soup.find("ul", class_="thread") or soup.find("ul")

            if thread_list:
                for li in thread_list.find_all("li", recursive=False)[:50]:
                    link = li.find("a")
                    if not link:
                        continue

                    subject = link.get_text(strip=True)
                    href = link.get("href", "")

                    # Skip administrative messages
                    skip_patterns = [
                        r"^\[qgis-user\]\s*$",
                        r"^Re:\s*$",
                        r"digest",
                        r"unsubscribe",
                    ]
                    if any(re.search(p, subject, re.I) for p in skip_patterns):
                        continue

                    # Clean up subject
                    subject = re.sub(r"^\[qgis-user\]\s*", "", subject)
                    subject = re.sub(r"^Re:\s*", "", subject)

                    if len(subject) < 5:
                        continue

                    # Build full URL
                    if href and not href.startswith("http"):
                        full_url = f"{settings.mailing_list_url}{year}-{month_name}/{href}"
                    else:
                        full_url = href

                    # Try to get author
                    author = None
                    author_elem = li.find("em") or li.find("i")
                    if author_elem:
                        author = author_elem.get_text(strip=True)

                    # Try to get date
                    post_date = None
                    date_elem = li.find("span", class_="date")
                    if date_elem:
                        try:
                            date_text = date_elem.get_text(strip=True)
                            post_date = datetime.strptime(date_text, "%Y-%m-%d").date()
                        except ValueError:
                            pass

                    items.append(
                        NewsItem(
                            title=subject[:200],
                            url=full_url,
                            date=post_date,
                            author=author,
                            category="Mailing List",
                        )
                    )

            # Also try date index if thread index didn't work well
            if len(items) < 5:
                date_url = f"{settings.mailing_list_url}{year}-{month_name}/date.html"
                try:
                    date_response = await self.client.get(date_url)
                    if date_response.status_code == 200:
                        date_soup = BeautifulSoup(date_response.text, "lxml")
                        for link in date_soup.find_all("a")[:30]:
                            href = link.get("href", "")
                            if href.endswith(".html") and href != "thread.html":
                                subject = link.get_text(strip=True)
                                if len(subject) > 10 and not any(
                                    x in subject.lower()
                                    for x in ["digest", "unsubscribe"]
                                ):
                                    full_url = (
                                        f"{settings.mailing_list_url}"
                                        f"{year}-{month_name}/{href}"
                                    )
                                    # Avoid duplicates
                                    if not any(i.url == full_url for i in items):
                                        items.append(
                                            NewsItem(
                                                title=subject[:200],
                                                url=full_url,
                                                category="Mailing List",
                                            )
                                        )
                except Exception:
                    pass

        except Exception as e:
            warnings.append(f"Error fetching mailing list: {e}")

        # Limit to most interesting threads (longer subjects often more substantive)
        items.sort(key=lambda x: len(x.title), reverse=True)
        items = items[:20]

        self.log_verbose(f"Found {len(items)} mailing list threads")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )
