<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Configuration

Settings load from environment variables or a `.env` file in the working
directory. Names are case-insensitive.

```bash title=".env"
GITHUB_TOKEN=ghp_your_token_here
TRANSIFEX_TOKEN=1/your_token_here
CACHE_TTL_HOURS=6
```

!!! danger "Never commit `.env`"

    It is in `.gitignore` and pre-commit runs secret scanning, but treat the
    tokens as credentials: least privilege, rotated, and out of the repo.

## Tokens

| Variable | Needed for | Scope |
|----------|------------|-------|
| `GITHUB_TOKEN` | Releases, PRs, QEPs, website updates, discussions | Public read is enough &mdash; a fine-grained token with no permissions works |
| `TRANSIFEX_TOKEN` | The `translations` section | Read access to the QGIS Transifex organisation |

Without `GITHUB_TOKEN` the tool still runs, but 60 requests an hour does not
go far on a busy month and the GitHub sections come back partial.

## Cache

| Variable | Default | Purpose |
|----------|---------|---------|
| `CACHE_DIR` | `~/.cache/qgis-news-gatherer` | Where responses are stored |
| `CACHE_TTL_HOURS` | `1` | How long an entry stays fresh |

Entries are keyed by month and section: `{CACHE_DIR}/2026-03/releases.json`.
A stale entry is still used as a fallback when a live fetch fails, and the
section carries a warning to say so. `--force` bypasses the cache.

`{CACHE_DIR}/youtube_history.json` is different: it is not a cache but the
accumulated month-on-month counts behind the YouTube charts. Deleting it loses
the history &mdash; see [YouTube sections](../user-guide/youtube.md).

## Requests

| Variable | Default | Purpose |
|----------|---------|---------|
| `REQUEST_TIMEOUT` | `30` | Per-request timeout in seconds |
| `MAX_CONCURRENT_REQUESTS` | `5` | Concurrency ceiling |

## Sources

Every upstream URL is overridable, which is mostly useful for testing against
a mirror.

| Variable | Default |
|----------|---------|
| `GITHUB_API_URL` | `https://api.github.com` |
| `QGIS_REPO` | `qgis/QGIS` |
| `QGIS_WEBSITE_REPO` | `qgis/QGIS-Website` |
| `QGIS_QEPS_REPO` | `qgis/QGIS-Enhancement-Proposals` |
| `QGIS_BLOG_FEED` | `https://blog.qgis.org/feed/` |
| `FEED_QGIS_URL` | `https://feed.qgis.org/?json=1` |
| `CHANGELOG_URL` | `https://changelog.qgis.org/en/qgis/` |
| `ANALYTICS_URL` | `https://analytics.qgis.org` |
| `CONFERENCE_URL` | `https://uc2025.qgis.org` |
| `MAILING_LIST_URL` | `https://lists.osgeo.org/pipermail/qgis-user/` |

## YouTube

| Variable | Default |
|----------|---------|
| `YOUTUBE_SEARCH_URL` | `https://www.youtube.com/results` |
| `YOUTUBE_SEARCH_FILTER` | `EgIIBA%3D%3D` |
| `YOUTUBE_SEARCH_QUERIES` | `["QGIS", "QGIS tutorial"]` |
| `YOUTUBE_SHORTS_SEARCH_QUERIES` | `["QGIS shorts", "QGIS"]` |
| `YOUTUBE_MAX_VIDEOS` | `8` |
| `YOUTUBE_MAX_SHORTS` | `8` |
| `YOUTUBE_HIGHLIGHT_COUNT` | `3` |

List values are JSON when set through the environment:

```bash
YOUTUBE_SEARCH_QUERIES='["QGIS", "QGIS 4.0", "QGIS plugin"]'
```

## Output defaults

| Variable | Default |
|----------|---------|
| `OUTPUT_FORMAT` | `markdown` |
| `OUTPUT_FILE` | unset &mdash; standard output |

Command line flags always win over the environment.
