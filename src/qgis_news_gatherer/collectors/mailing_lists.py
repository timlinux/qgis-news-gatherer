# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Mailing list archive collector."""

import re
from datetime import datetime

from bs4 import BeautifulSoup

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem


class MailingListsCollector(BaseCollector):
    """Collect every thread for the month from a pipermail archive.

    Subclassed for each list (qgis-user, qgis-developer, …) so the archive
    URL and list-tag prefix can be overridden per-list.
    """

    section_name = "mailing_lists_user"
    section_title = "QGIS Users Mailing List"
    archive_base = "https://lists.osgeo.org/pipermail/qgis-user/"
    list_tag = "qgis-user"

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

        # Threads keyed by normalized subject so multiple replies in the
        # same thread collapse to one entry. We keep the first occurrence
        # (the thread starter, which appears first in the thread index).
        threads: dict[str, NewsItem] = {}
        warnings: list[str] = []

        # Construct archive URL for target month
        month_name = self.MONTH_NAMES[self.config.target_month.month]
        year = self.config.target_month.year
        archive_url = f"{self.archive_base}{year}-{month_name}/thread.html"

        self.log_verbose(f"Checking archive: {archive_url}")

        try:
            response = await self.client.get(archive_url)
            if response.status_code == 404:
                warnings.append(f"Archive not found for {month_name} {year}")
                return CollectorResult(
                    section_name=self.section_name,
                    section_title=self.section_title,
                    items=[],
                    warnings=warnings,
                )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # The pipermail thread index uses a single nested <ul>. Walk all
            # links inside it — top-level threads and nested replies share
            # the same subject after normalization, so dedup handles both.
            thread_list = soup.find("ul", class_="thread") or soup.find("ul")
            if thread_list:
                self._absorb_links(
                    thread_list.find_all("a"), threads, year, month_name
                )

            # Fall back to the date index if the thread page is empty/missing.
            if not threads:
                date_url = f"{self.archive_base}{year}-{month_name}/date.html"
                try:
                    date_response = await self.client.get(date_url)
                    if date_response.status_code == 200:
                        date_soup = BeautifulSoup(date_response.text, "lxml")
                        self._absorb_links(
                            date_soup.find_all("a"), threads, year, month_name
                        )
                except Exception:
                    pass

        except Exception as e:
            warnings.append(f"Error fetching mailing list: {e}")

        items = list(threads.values())
        # Newest threads first when we have dates; otherwise preserve order
        # (which is roughly chronological from the thread index).
        items.sort(
            key=lambda x: (x.date is not None, x.date),
            reverse=True,
        )

        self.log_verbose(f"Found {len(items)} unique mailing list threads")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )

    def _absorb_links(
        self,
        links: list,
        threads: dict[str, NewsItem],
        year: int,
        month_name: str,
    ) -> None:
        """Extract subject links from a pipermail listing and dedupe by subject."""
        skip_patterns = [
            rf"^\[{re.escape(self.list_tag)}\]\s*$",
            r"^Re:\s*$",
            r"digest",
            r"unsubscribe",
        ]
        for link in links:
            href = link.get("href", "")
            if not href or not href.endswith(".html"):
                continue
            if href in ("thread.html", "date.html", "author.html", "subject.html"):
                continue

            subject_raw = link.get_text(strip=True)
            if any(re.search(p, subject_raw, re.I) for p in skip_patterns):
                continue

            # Strip any list-tag and reply markers before deduping so that
            # cross-posts (e.g. "[Qgis-psc] Foo" vs "Foo") collapse together.
            subject = subject_raw
            for _ in range(3):
                stripped = re.sub(
                    r"^(?:\[[^\]]+\]|(?:Re|Fwd|Fw)\s*:)\s*",
                    "",
                    subject,
                    flags=re.I,
                )
                if stripped == subject:
                    break
                subject = stripped
            subject = subject.strip()
            if len(subject) < 5:
                continue

            key = re.sub(r"\s+", " ", subject.lower()).strip()
            if key in threads:
                continue

            if href.startswith("http"):
                full_url = href
            else:
                full_url = f"{self.archive_base}{year}-{month_name}/{href}"

            parent = link.find_parent("li")
            author = None
            post_date = None
            if parent is not None:
                author_elem = parent.find("em") or parent.find("i")
                if author_elem:
                    author = author_elem.get_text(strip=True)
                date_elem = parent.find("span", class_="date")
                if date_elem:
                    try:
                        post_date = datetime.strptime(
                            date_elem.get_text(strip=True), "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        pass

            threads[key] = NewsItem(
                title=subject[:200],
                url=full_url,
                date=post_date,
                author=author,
                category="Mailing List",
            )


class DeveloperMailingListsCollector(MailingListsCollector):
    """Collect every thread for the month from the qgis-developer list."""

    section_name = "mailing_lists_developer"
    section_title = "QGIS Developer Mailing List"
    archive_base = "https://lists.osgeo.org/pipermail/qgis-developer/"
    list_tag = "qgis-developer"
