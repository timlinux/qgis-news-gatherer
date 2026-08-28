<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Testing

```bash
nix run .#test          # or: pytest
pytest tests/test_youtube.py -v
pytest --cov=src/qgis_news_gatherer
```

## No network in tests

Collectors are tested against canned payloads, never the live source. A test
that depends on what YouTube returned this morning is not a test.

The pattern, from `tests/test_youtube.py`:

```python
def _collector(cls, page, month=date(2026, 8, 1), today=date(2026, 8, 20)):
    """Build a collector whose HTTP client serves a canned search page."""
    collector = cls(ReportConfig(target_month=month))
    collector.today = lambda: today
    collector._client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=page)
        )
    )
    return collector
```

Two things make this work:

- **`httpx.MockTransport`** intercepts every request, so no socket is opened.
- **`today` is a method, not a call to `date.today()`**, so relative dates
  ("3 days ago") resolve to a fixed, assertable date.

## Isolate the cache

Collectors write to `settings.cache_dir`. Point it at a temporary directory so
tests neither read a developer's cache nor pollute it:

```python
@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Point the collector cache and history file at a temp directory."""
    monkeypatch.setattr(settings, "cache_dir", tmp_path)
    return tmp_path
```

## Build fixtures with helpers

Rather than pasting a 400-line JSON blob, write a small builder per node
shape. It documents the shape and keeps each test readable:

```python
def _video_renderer(video_id, title, length="12:34", published="3 days ago"):
    """Build a videoRenderer node shaped like YouTube's search response."""
    ...
```

## What to cover

- **Each upstream shape.** YouTube alone has three node shapes; all three have
  a test.
- **The filtering rules.** Items outside the month are dropped; undated items
  follow the documented rule.
- **The degraded paths.** An unparseable page produces an error result, not an
  exception.
- **The pure helpers.** Parsing view counts, durations and relative dates is
  where the fiddly bugs live; these are cheap parametrised tests.

## Async tests

`pytest-asyncio` runs in auto mode, configured in `pyproject.toml`, so an
`async def` test needs no decorator beyond `@pytest.mark.asyncio`.

## Before you push

```bash
nix run .#lint
nix run .#test
```

!!! note "Known failures"

    Four tests in `tests/test_report.py` currently fail. They exercise an
    `add_custom_chapter` API and Introduction/Wrap-up chapters that were
    removed from `ShowNotesGenerator`. They are stale tests for a removed
    feature, not a regression &mdash; decide whether to restore the feature or
    delete the tests before treating a green run as the bar.
