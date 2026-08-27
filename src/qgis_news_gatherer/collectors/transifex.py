"""Transifex translation statistics collector."""

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem
from qgis_news_gatherer.config import settings


class TranslationsCollector(BaseCollector):
    """Collect translation statistics from Transifex."""

    section_name = "translations"
    section_title = "Translation Updates"

    # Transifex API endpoints
    TRANSIFEX_API_URL = "https://rest.api.transifex.com"
    QGIS_ORGANIZATION = "qgis"
    QGIS_PROJECT = "qgis-documentation"

    async def collect(self) -> CollectorResult:
        """Fetch translation statistics from Transifex API."""
        self.log_verbose("Fetching translation statistics...")

        if not settings.transifex_token:
            return CollectorResult(
                section_name=self.section_name,
                section_title=self.section_title,
                items=[],
                warnings=["Transifex token not configured - skipping translation stats"],
            )

        items: list[NewsItem] = []
        warnings: list[str] = []

        headers = {
            "Authorization": f"Bearer {settings.transifex_token}",
            "Content-Type": "application/vnd.api+json",
        }

        try:
            # Get project statistics
            project_url = (
                f"{self.TRANSIFEX_API_URL}/projects/"
                f"o:{self.QGIS_ORGANIZATION}:p:{self.QGIS_PROJECT}"
            )

            response = await self.client.get(project_url, headers=headers)

            if response.status_code == 401:
                return CollectorResult(
                    section_name=self.section_name,
                    section_title=self.section_title,
                    error="Transifex authentication failed - check your API token",
                )

            if response.status_code == 404:
                warnings.append("QGIS project not found on Transifex")
            else:
                response.raise_for_status()
                project_data = response.json()

                # Extract project stats
                attrs = project_data.get("data", {}).get("attributes", {})
                items.append(
                    NewsItem(
                        title=f"QGIS Documentation Translation Project",
                        url="https://www.transifex.com/qgis/qgis-documentation/",
                        description=attrs.get("description"),
                        category="Translation Project",
                        metadata={
                            "name": attrs.get("name"),
                            "slug": attrs.get("slug"),
                        },
                    )
                )

            # Get language statistics
            stats_url = (
                f"{self.TRANSIFEX_API_URL}/project_language_stats"
                f"?filter[project]=o:{self.QGIS_ORGANIZATION}:p:{self.QGIS_PROJECT}"
            )

            stats_response = await self.client.get(stats_url, headers=headers)

            if stats_response.status_code == 200:
                stats_data = stats_response.json()

                # Process language statistics
                languages = []
                for lang_stat in stats_data.get("data", []):
                    attrs = lang_stat.get("attributes", {})
                    lang_code = lang_stat.get("id", "").split(":")[-1]

                    translated = attrs.get("translated_strings", 0)
                    total = attrs.get("total_strings", 1)
                    percentage = (translated / total * 100) if total > 0 else 0

                    if percentage > 50:  # Only show languages > 50% complete
                        languages.append(
                            {
                                "code": lang_code,
                                "percentage": round(percentage, 1),
                                "translated": translated,
                                "total": total,
                            }
                        )

                # Sort by completion percentage
                languages.sort(key=lambda x: x["percentage"], reverse=True)

                # Add top languages as items
                for lang in languages[:15]:
                    items.append(
                        NewsItem(
                            title=f"{lang['code'].upper()}: {lang['percentage']}% complete",
                            url="https://www.transifex.com/qgis/qgis-documentation/",
                            description=(
                                f"{lang['translated']:,} of {lang['total']:,} strings translated"
                            ),
                            category="Language Stats",
                            metadata=lang,
                        )
                    )

        except Exception as e:
            warnings.append(f"Error fetching Transifex data: {e}")

        self.log_verbose(f"Found {len(items)} translation items")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )
