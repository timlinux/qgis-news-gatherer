# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Collector for QGIS Project Steering Committee meeting minutes."""

from __future__ import annotations

import io
import re
from datetime import date, datetime

from pypdf import PdfReader

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem


ARCHIVE_URL = "https://github.com/qgis/QGIS/wiki/PSC-Meetings-archive"

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

# Newest first: YYYYMMDD-QGIS-PSC-Meeting.pdf
_DATE_PREFIX_RE = re.compile(r"/(\d{8})-QGIS-PSC-Meeting\.pdf", re.IGNORECASE)
# Middle era: Month.YYYY.pdf or Month YYYY.pdf
_MONTH_YEAR_RE = re.compile(
    r"/(January|February|March|April|May|June|July|August|September|October|November|December)[.\s]?(\d{4})\.pdf",
    re.IGNORECASE,
)
# Older: QGIS-PSC-Meeting-DD-Month-YYYY.pdf or with no day
_LEGACY_DAY_MONTH_RE = re.compile(
    r"QGIS-PSC-Meeting-(\d{1,2})-?-?(January|February|March|April|May|June|July|August|September|October|November|December)-?-?(\d{4})\.pdf",
    re.IGNORECASE,
)
_LEGACY_MONTH_RE = re.compile(
    r"QGIS-PSC-Meeting-(January|February|March|April|May|June|July|August|September|October|November|December)[.\s]?(\d{4})\.pdf",
    re.IGNORECASE,
)


def _meeting_date_from_url(url: str) -> date | None:
    """Best-effort derive the meeting date from a PDF URL."""
    m = _DATE_PREFIX_RE.search(url)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d").date()
        except ValueError:
            return None
    m = _LEGACY_DAY_MONTH_RE.search(url)
    if m:
        try:
            day = int(m.group(1))
            month = MONTH_NAMES[m.group(2).lower()]
            year = int(m.group(3))
            return date(year, month, day)
        except (ValueError, KeyError):
            return None
    m = _MONTH_YEAR_RE.search(url)
    if m:
        try:
            month = MONTH_NAMES[m.group(1).lower()]
            year = int(m.group(2))
            return date(year, month, 1)
        except (ValueError, KeyError):
            return None
    m = _LEGACY_MONTH_RE.search(url)
    if m:
        try:
            month = MONTH_NAMES[m.group(1).lower()]
            year = int(m.group(2))
            return date(year, month, 1)
        except (ValueError, KeyError):
            return None
    return None


class PSCMinutesCollector(BaseCollector):
    """Collect the topic list from the most recent QGIS PSC meeting."""

    section_name = "psc_minutes"
    section_title = "PSC Meeting"

    async def collect(self) -> CollectorResult:
        warnings: list[str] = []
        self.log_verbose(f"Fetching PSC archive from {ARCHIVE_URL}...")

        response = await self.client.get(
            ARCHIVE_URL,
            headers={"User-Agent": "QGIS-News-Gatherer/1.0"},
        )
        response.raise_for_status()

        pdf_links: list[tuple[date | None, str]] = []
        seen: set[str] = set()
        for match in re.finditer(
            r'href="(https://github\.com/[^"]+\.pdf)"', response.text
        ):
            url = match.group(1)
            if url in seen:
                continue
            seen.add(url)
            pdf_links.append((_meeting_date_from_url(url), url))

        dated = [(d, u) for d, u in pdf_links if d is not None]
        dated.sort(key=lambda x: x[0], reverse=True)

        if not dated:
            warnings.append("Could not find any PSC meeting PDFs in the archive")
            return CollectorResult(
                section_name=self.section_name,
                section_title=self.section_title,
                items=[],
                warnings=warnings,
            )

        # Prefer a meeting that occurred during the target month;
        # fall back to the most recent meeting on or before month-end.
        month_end = self.config.month_end()
        chosen: tuple[date, str] | None = None
        for d, u in dated:
            if self.config.month_start() <= d <= month_end:
                chosen = (d, u)
                break
        if chosen is None:
            for d, u in dated:
                if d <= month_end:
                    chosen = (d, u)
                    break
        if chosen is None:
            chosen = dated[0]

        meeting_date, pdf_url = chosen
        self.log_verbose(
            f"Latest meeting: {meeting_date.isoformat()} -> {pdf_url}"
        )

        pdf_response = await self.client.get(pdf_url)
        pdf_response.raise_for_status()

        try:
            reader = PdfReader(io.BytesIO(pdf_response.content))
            full_text = "\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception as exc:
            warnings.append(f"Failed to parse PDF: {exc}")
            return CollectorResult(
                section_name=self.section_name,
                section_title=self.section_title,
                items=[],
                warnings=warnings,
            )

        topics = _extract_topics(full_text)

        items: list[NewsItem] = []
        for owner, topic in topics:
            display_title = f"{owner}: {topic}" if owner else topic
            items.append(
                NewsItem(
                    title=display_title,
                    url=pdf_url,
                    description=None,
                    date=meeting_date,
                    author=owner or None,
                    category="PSC Minutes",
                    metadata={
                        "meeting_date": meeting_date.isoformat(),
                        "topic": topic,
                        "owner": owner,
                    },
                )
            )

        if not items:
            warnings.append(
                "Could not extract any topics from the meeting PDF "
                "(the format may have changed)"
            )

        self.log_verbose(
            f"Extracted {len(items)} topics from meeting on {meeting_date}"
        )
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )


# Names of agenda owners we expect to see. Drives the topic-extraction
# regex so we don't accidentally match arbitrary "Word: Word" snippets
# inside bullet content (e.g. "TODO Marco: draft...").
_KNOWN_OWNERS = (
    "Marco|Anita|Andreas|Tim|R[eé]gis|J[uü]rgen|Giovanni|Paolo|"
    "Alessandro|Richard|Jacob|Otto|Vincent|Anne|Jorge|Margherita|Maria"
)

# Stop the topic capture at the next bullet, the next known-owner heading,
# the "Old Agenda" divider, or end-of-text. This prevents one false-positive
# match (e.g. a "Andreas: ..." mention inside a bullet) from swallowing the
# next real heading.
_TOPIC_HEADING_RE = re.compile(
    rf"({_KNOWN_OWNERS})\s*:\s+"
    rf"([^●○\n]+?)"
    rf"(?=\s+[●○]|\s+(?:{_KNOWN_OWNERS})\s*:|\s+(?:Old|Previous)\s+Agenda|$)",
    re.IGNORECASE,
)


def _extract_topics(text: str) -> list[tuple[str, str]]:
    """Pull (owner, topic) pairs from the Agenda section of a PSC PDF.

    Stops at the "Old Agenda" / "Previous Agenda" carry-over divider so
    we only return topics from the current meeting.
    """
    # Collapse all whitespace (including newlines pypdf inserts mid-phrase)
    # to single spaces so the heading regex sees contiguous text.
    cleaned = re.sub(r"\s+", " ", text)

    # Find the start of the live agenda (not "Old Agenda" / "Previous Agenda").
    agenda_start = -1
    for m in re.finditer(r"\bAgenda\b", cleaned):
        before = cleaned[max(0, m.start() - 10) : m.start()].lower()
        if "old" in before or "previous" in before:
            continue
        agenda_start = m.end()
        break
    if agenda_start < 0:
        return []

    tail = cleaned[agenda_start:]
    cutoff = re.search(r"\b(?:Old|Previous)\s+Agenda\b", tail, re.IGNORECASE)
    if cutoff:
        tail = tail[: cutoff.start()]

    topics: list[tuple[str, str]] = []
    seen: set[str] = set()
    for match in _TOPIC_HEADING_RE.finditer(tail):
        # Reject matches sitting inside a bullet body. Top-level headings
        # come after the end of the previous bullet group; they are NOT
        # preceded by a `●` or `○` within the last ~6 chars.
        preceding = tail[max(0, match.start() - 6) : match.start()]
        if "●" in preceding or "○" in preceding:
            continue
        # Reject the "TODO Name:" action-item pattern that appears in bullets.
        if re.search(r"\bTODO\s*$", preceding, re.IGNORECASE):
            continue

        owner = match.group(1).strip()
        topic = match.group(2).strip().rstrip(":").strip()
        if not topic or len(topic) > 80:
            continue
        # Topic titles start with a capital letter (or an opening paren).
        if not topic[0].isupper() and topic[0] != "(":
            continue

        key = f"{owner.lower()}|{topic.lower()}"
        if key in seen:
            continue
        seen.add(key)
        topics.append((owner, topic))
    return topics
