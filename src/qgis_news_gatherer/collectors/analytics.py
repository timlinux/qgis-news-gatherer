# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Collectors for QGIS usage analytics and plugin statistics from Metabase dashboards."""

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem


class _MetabaseCollector(BaseCollector):
    """Base class for Metabase dashboard collectors."""

    base_url: str = ""
    dashboard_uuid: str = ""

    @property
    def dashboard_url(self) -> str:
        return f"{self.base_url}/public/dashboard/{self.dashboard_uuid}"

    async def _fetch_card(self, dashcard_id: int, card_id: int) -> dict | None:
        """Fetch data from a Metabase dashboard card."""
        url = (
            f"{self.base_url}/api/public/dashboard/{self.dashboard_uuid}"
            f"/dashcard/{dashcard_id}/card/{card_id}"
        )
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and "data" in data:
                return data["data"]
        except Exception as e:
            self.log_verbose(f"Could not fetch card {card_id}: {e}")
        return None


class AnalyticsCollector(_MetabaseCollector):
    """Collect QGIS usage analytics from the feed.qgis.org Metabase dashboard."""

    section_name = "analytics"
    section_title = "QGIS Usage Analytics"
    base_url = "https://feed.qgis.org/metabase"
    dashboard_uuid = "df81071d-4c75-45b8-a698-97b8649d7228"

    async def collect(self) -> CollectorResult:
        """Fetch QGIS usage analytics."""
        self.log_verbose("Fetching QGIS analytics from Metabase...")

        items: list[NewsItem] = []
        warnings: list[str] = []

        # Total opens in last 30 days (dashcard=14, card=14)
        data = await self._fetch_card(14, 14)
        if data and data.get("rows"):
            total_30d = data["rows"][0][0]
            items.append(
                NewsItem(
                    title=f"{total_30d:,} QGIS opens in the last 30 days",
                    url=self.dashboard_url,
                    description=(
                        "Approximate daily active users based on QGIS News Feed "
                        "hits when the application starts."
                    ),
                    category="metric",
                    metadata={"metric": "total_opens_30d", "value": total_30d},
                )
            )

        # Total opens yesterday (dashcard=18, card=18)
        data = await self._fetch_card(18, 18)
        if data and data.get("rows"):
            yesterday = data["rows"][0][0]
            items.append(
                NewsItem(
                    title=f"{yesterday:,} QGIS opens yesterday",
                    url=self.dashboard_url,
                    category="metric",
                    metadata={"metric": "opens_yesterday", "value": yesterday},
                )
            )

        # Monthly opens history for trend analysis (dashcard=15, card=15)
        data = await self._fetch_card(15, 15)
        if data and data.get("rows"):
            rows = sorted(data["rows"], key=lambda x: x[0])
            recent = rows[-12:] if len(rows) >= 12 else rows

            # Month-over-month trend
            target_month_str = self.config.target_month.strftime("%Y-%m")
            prev_month = self.config.target_month.month - 1
            prev_year = self.config.target_month.year
            if prev_month == 0:
                prev_month = 12
                prev_year -= 1
            prev_month_str = f"{prev_year}-{prev_month:02d}"

            current_val = None
            prev_val = None
            for r in recent:
                month_key = r[0][:7]
                if month_key == target_month_str:
                    current_val = r[1]
                elif month_key == prev_month_str:
                    prev_val = r[1]

            if current_val and prev_val:
                change_pct = ((current_val - prev_val) / prev_val) * 100
                direction = "up" if change_pct > 0 else "down"
                items.append(
                    NewsItem(
                        title=(
                            f"Monthly opens {direction} {abs(change_pct):.1f}% "
                            f"({current_val:,} vs {prev_val:,} previous month)"
                        ),
                        url=self.dashboard_url,
                        category="trend",
                        metadata={
                            "metric": "monthly_trend",
                            "current": current_val,
                            "previous": prev_val,
                            "change_pct": round(change_pct, 1),
                        },
                    )
                )

            # Monthly history summary
            history_lines = [
                f"{r[0][:7]}: {r[1]:,}" for r in recent[-6:]
            ]
            items.append(
                NewsItem(
                    title="Monthly opens history (last 6 months)",
                    url=self.dashboard_url,
                    description=" | ".join(history_lines),
                    category="history",
                    metadata={
                        "metric": "monthly_history",
                        "data": {r[0][:7]: r[1] for r in recent[-6:]},
                    },
                )
            )

        # Top countries (dashcard=1, card=1)
        data = await self._fetch_card(1, 1)
        if data and data.get("rows"):
            rows = sorted(data["rows"], key=lambda x: x[1], reverse=True)
            top_5 = rows[:5]
            country_list = ", ".join(f"{r[0]} ({r[1]:,})" for r in top_5)
            items.append(
                NewsItem(
                    title=f"Top 5 countries: {country_list}",
                    url=self.dashboard_url,
                    description=(
                        "Top 15 countries by QGIS opens (30 days): "
                        + ", ".join(f"{r[0]}: {r[1]:,}" for r in rows[:15])
                    ),
                    category="countries",
                    metadata={
                        "metric": "top_countries",
                        "data": {r[0]: r[1] for r in rows[:15]},
                    },
                )
            )

        # Top platforms (dashcard=3, card=3)
        data = await self._fetch_card(3, 3)
        if data and data.get("rows"):
            items.append(
                NewsItem(
                    title=f"Top platform: {data['rows'][0][0]}",
                    url=self.dashboard_url,
                    description=(
                        "Top 10 platforms (30 days): "
                        + ", ".join(
                            f"{r[0]}: {r[1]:,}" for r in data["rows"][:10]
                        )
                    ),
                    category="platforms",
                    metadata={
                        "metric": "top_platforms",
                        "data": {r[0]: r[1] for r in data["rows"][:10]},
                    },
                )
            )

        self.log_verbose(f"Found {len(items)} analytics items")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )


class PluginStatsCollector(_MetabaseCollector):
    """Collect QGIS plugin statistics from plugins.qgis.org Metabase dashboard."""

    section_name = "plugin_stats"
    section_title = "Plugin Statistics"
    base_url = "https://plugins.qgis.org/metabase"
    dashboard_uuid = "7ecd345f-7321-423d-9844-71e526a454a9"

    async def collect(self) -> CollectorResult:
        """Fetch QGIS plugin statistics."""
        self.log_verbose("Fetching plugin statistics from Metabase...")

        items: list[NewsItem] = []
        warnings: list[str] = []

        # Total downloads (dashcard=62, card=61)
        data = await self._fetch_card(62, 61)
        if data and data.get("rows"):
            total = data["rows"][0][0]
            items.append(
                NewsItem(
                    title=f"{total:,} total plugin downloads",
                    url=self.dashboard_url,
                    category="metric",
                    metadata={"metric": "total_downloads", "value": total},
                )
            )

        # Downloads in last 30 days (dashcard=85, card=83)
        data = await self._fetch_card(85, 83)
        if data and data.get("rows"):
            val = data["rows"][0][0]
            items.append(
                NewsItem(
                    title=f"{val:,} plugin downloads in the last 30 days",
                    url=self.dashboard_url,
                    category="metric",
                    metadata={"metric": "downloads_30d", "value": val},
                )
            )

        # New plugins in last 30 days (dashcard=64, card=62)
        data = await self._fetch_card(64, 62)
        if data and data.get("rows"):
            val = data["rows"][0][0]
            items.append(
                NewsItem(
                    title=f"{val:,} new plugins published in the last 30 days",
                    url=self.dashboard_url,
                    category="metric",
                    metadata={"metric": "new_plugins_30d", "value": val},
                )
            )

        # Updated plugins in last 30 days (dashcard=65, card=63)
        data = await self._fetch_card(65, 63)
        if data and data.get("rows"):
            val = data["rows"][0][0]
            items.append(
                NewsItem(
                    title=f"{val:,} plugins updated in the last 30 days",
                    url=self.dashboard_url,
                    category="metric",
                    metadata={"metric": "updated_plugins_30d", "value": val},
                )
            )

        # Active developers (dashcard=70, card=68)
        data = await self._fetch_card(70, 68)
        if data and data.get("rows"):
            val = data["rows"][0][0]
            items.append(
                NewsItem(
                    title=f"{val:,} active plugin developers (12 months)",
                    url=self.dashboard_url,
                    category="metric",
                    metadata={"metric": "active_devs", "value": val},
                )
            )

        # Most downloaded plugins - last 30 days (dashcard=101, card=86)
        data = await self._fetch_card(101, 86)
        if data and data.get("rows"):
            top_5 = data["rows"][:5]
            items.append(
                NewsItem(
                    title="Top 5 plugins this month",
                    url=self.dashboard_url,
                    description=", ".join(
                        f"{i+1}. {r[0]} ({r[1]:,})"
                        for i, r in enumerate(top_5)
                    ),
                    category="top_monthly",
                    metadata={
                        "metric": "top_downloads_30d",
                        "data": {r[0]: r[1] for r in top_5},
                    },
                )
            )

        # Most downloaded plugins - all time (dashcard=69, card=67)
        data = await self._fetch_card(69, 67)
        if data and data.get("rows"):
            top_5 = data["rows"][:5]
            items.append(
                NewsItem(
                    title="Top 5 plugins all time",
                    url=self.dashboard_url,
                    description=", ".join(
                        f"{i+1}. {r[0]} ({r[1]:,})"
                        for i, r in enumerate(top_5)
                    ),
                    category="top_alltime",
                    metadata={
                        "metric": "top_downloads_alltime",
                        "data": {r[0]: r[1] for r in top_5},
                    },
                )
            )

        # Most voted plugins (dashcard=66, card=64)
        data = await self._fetch_card(66, 64)
        if data and data.get("rows"):
            top_5 = data["rows"][:5]
            items.append(
                NewsItem(
                    title="Most voted plugins",
                    url=self.dashboard_url,
                    description=", ".join(
                        f"{r[0]} ({r[1]} votes)" for r in top_5
                    ),
                    category="most_voted",
                    metadata={
                        "metric": "most_voted",
                        "data": {r[0]: r[1] for r in top_5},
                    },
                )
            )

        # Top countries for downloads (dashcard=80, card=78)
        data = await self._fetch_card(80, 78)
        if data and data.get("rows"):
            top_5 = data["rows"][:5]
            items.append(
                NewsItem(
                    title="Top 5 plugin download countries",
                    url=self.dashboard_url,
                    description=", ".join(
                        f"{r[0]} ({r[1]:,})" for r in top_5
                    ),
                    category="countries",
                    metadata={
                        "metric": "top_countries",
                        "data": {r[0]: r[1] for r in top_5},
                    },
                )
            )

        # Top contributors (dashcard=71, card=69)
        data = await self._fetch_card(71, 69)
        if data and data.get("rows"):
            # Filter out None/empty names
            contributors = [
                r for r in data["rows"][:5]
                if r[0] and str(r[0]).strip() not in ("None", "")
            ]
            if contributors:
                items.append(
                    NewsItem(
                        title="Top contributors (12 months)",
                        url=self.dashboard_url,
                        description=", ".join(
                            str(r[0]).strip() for r in contributors
                        ),
                        category="contributors",
                        metadata={
                            "metric": "top_contributors",
                            "data": [str(r[0]).strip() for r in contributors],
                        },
                    )
                )

        self.log_verbose(f"Found {len(items)} plugin stats items")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )
