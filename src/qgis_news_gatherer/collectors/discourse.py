# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Collector for QGIS-category threads on the OSGeo Discourse forum."""

from __future__ import annotations

from datetime import datetime, timedelta

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem


class DiscourseCollector(BaseCollector):
    """Collect every Discourse topic started in the QGIS category this month."""

    section_name = "discourse"
    section_title = "QGIS Forum (Discourse)"

    CATEGORY_ID = 11
    CATEGORY_URL = "https://discourse.osgeo.org/c/qgis/11"
    SEARCH_URL = "https://discourse.osgeo.org/search.json"
    TOPIC_BASE_URL = "https://discourse.osgeo.org/t"

    async def collect(self) -> CollectorResult:
        self.log_verbose("Fetching Discourse threads for the month...")

        items: list[NewsItem] = []
        warnings: list[str] = []

        month_start = self.config.month_start().isoformat()
        # Discourse `before:` is exclusive — pass the day after month-end.
        before = (self.config.month_end() + timedelta(days=1)).isoformat()
        query = f"after:{month_start} before:{before} category:{self.CATEGORY_ID}"

        seen_ids: set[int] = set()

        for page in range(1, 11):
            response = await self.client.get(
                self.SEARCH_URL,
                params={"q": query, "page": page},
                headers={"User-Agent": "QGIS-News-Gatherer/1.0"},
            )
            response.raise_for_status()
            data = response.json()

            topics = data.get("topics", []) or []
            if not topics:
                break

            for topic in topics:
                tid = topic.get("id")
                if not tid or tid in seen_ids:
                    continue
                seen_ids.add(tid)

                created = topic.get("created_at", "") or ""
                topic_date = None
                if created:
                    try:
                        topic_date = datetime.fromisoformat(
                            created.replace("Z", "+00:00")
                        ).date()
                    except ValueError:
                        pass

                # Filter to topics whose start really is in the target month;
                # the search API rounds dates in some edge cases.
                if not self.is_in_month(topic_date):
                    continue

                slug = topic.get("slug") or ""
                topic_url = (
                    f"{self.TOPIC_BASE_URL}/{slug}/{tid}" if slug
                    else f"{self.TOPIC_BASE_URL}/{tid}"
                )

                posts_count = topic.get("posts_count", 0)
                reply_count = max(0, posts_count - 1)
                stats_parts = []
                if reply_count:
                    stats_parts.append(
                        f"{reply_count} repl{'y' if reply_count == 1 else 'ies'}"
                    )
                like_count = topic.get("like_count") or 0
                if like_count:
                    stats_parts.append(f"{like_count} likes")

                items.append(
                    NewsItem(
                        title=topic.get("title") or topic.get("fancy_title") or "Untitled",
                        url=topic_url,
                        description=" · ".join(stats_parts) if stats_parts else None,
                        date=topic_date,
                        category="discourse",
                        metadata={
                            "topic_id": tid,
                            "posts_count": posts_count,
                            "like_count": like_count,
                            "category_id": topic.get("category_id"),
                        },
                    )
                )

            more = (
                data.get("grouped_search_result", {}) or {}
            ).get("more_full_page_results")
            if not more:
                break

        # Newest first
        items.sort(key=lambda x: x.date or self.config.month_start(), reverse=True)

        self.log_verbose(f"Found {len(items)} Discourse threads")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )
