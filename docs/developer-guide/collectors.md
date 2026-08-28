<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Writing a Collector

A collector is one class with one method. Everything else &mdash; caching,
retries, error handling, date filtering &mdash; comes from `BaseCollector`.

## The minimum

```python
# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Collector for the QGIS widget registry."""

from qgis_news_gatherer.collectors.base import (
    BaseCollector,
    CollectorResult,
    NewsItem,
)


class WidgetsCollector(BaseCollector):
    """Collect widgets published this month."""

    section_name = "widgets"
    section_title = "New Widgets"

    async def collect(self) -> CollectorResult:
        """Fetch and parse the widget registry."""
        self.log_verbose("Fetching widgets...")

        response = await self.client.get("https://example.org/widgets.json")
        response.raise_for_status()

        items: list[NewsItem] = []
        warnings: list[str] = []

        for entry in response.json():
            published = parse_date(entry["published"])
            if not self.is_in_month(published):
                continue
            items.append(
                NewsItem(
                    title=entry["name"],
                    url=entry["url"],
                    description=entry["summary"],
                    date=published,
                    category="Widget",
                )
            )

        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )
```

## Register it

Three places:

1. `cli.py` &mdash; add to the `COLLECTORS` map:

    ```python
    "widgets": WidgetsCollector,
    ```

2. `config.py` &mdash; add to `default_sections()` in the position it should
   appear in the report, and to `available_sections()` with a description.

3. `SPECIFICATION.md` &mdash; add an `FR-001.x` line and, if it scrapes
   something, a note on the source and its limitations.

## What you get for free

| From `BaseCollector` | What it does |
|----------------------|--------------|
| `self.client` | A shared `httpx.AsyncClient` with the configured timeout |
| `self.is_in_month(d)` | True when `d` falls in the target month |
| `self.log_verbose(msg)` | Prints only under `--verbose` |
| `self.log_warning(msg)` | Always prints, in yellow |
| `safe_collect()` | Caching, HTTP and timeout handling, stale-cache fallback |

## Rules of the road

!!! success "Do"

    - **Raise, do not swallow.** Let HTTP errors propagate out of `collect()`;
      `safe_collect()` turns them into a recorded error and falls back to a
      stale cache.
    - **Use `warnings` for partial success.** A source that returned half its
      data should say so rather than look complete.
    - **Put extras in `metadata`.** Counts, identifiers and chart series
      belong there, not encoded into the title.
    - **Strip emoji from anything user-supplied.** Use `strip_emoji()` from
      `base.py`. Colour emoji render at full glyph size in WeasyPrint and
      break card layouts.

!!! failure "Do not"

    - **Do not call `date.today()` directly** in logic that tests need to pin.
      Expose it as an overridable method, as the YouTube collector does.
    - **Do not hit the network in tests.** See [Testing](testing.md).
    - **Do not let one bad entry kill the batch.** Skip it and carry on.

## Adding a chart

Emit a summary item carrying a `metric` key:

```python
NewsItem(
    title="42 widgets this month",
    category="summary",
    metadata={
        "metric": "widget_summary",
        "count": 42,
        "history": {"2026-07": 31, "2026-08": 42},
    },
)
```

Then handle it in `charts.py` inside `generate_analytics_charts()`, and add
the section name to `chart_sections` in `report.py`. If the summary item
should not also appear as a card, filter it out where the section is built
&mdash; the YouTube sections do exactly this.
