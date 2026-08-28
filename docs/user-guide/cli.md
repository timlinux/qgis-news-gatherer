<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Command Line Reference

```
qgis-news-gatherer [OPTIONS]
```

## Options

| Option | Description |
|--------|-------------|
| `-m`, `--month TEXT` | Target month as `YYYY-MM`. Defaults to the current month. |
| `-o`, `--output PATH` | Write to a file instead of standard output. |
| `-f`, `--format FORMAT` | One of `terminal`, `markdown`, `json`, `pdf`, `youtube`, `html`. Default `terminal`. |
| `-s`, `--sections TEXT` | Comma-separated section names. Default: all. |
| `-v`, `--verbose` | Log each collector as it runs. |
| `--list-sections` | Print the available sections and exit. |
| `--show-chapters` | Print the chapter timestamps only. |
| `--show-youtube-desc` | Print the YouTube description only. |
| `--force` | Ignore the cache and refetch everything. |
| `--version` | Print the version and exit. |
| `--help` | Print usage and exit. |

## Recipes

=== "Read this month"

    ```bash
    qgis-news-gatherer
    ```

=== "PDF for a past month"

    ```bash
    qgis-news-gatherer -m 2026-03 -f pdf -o qgis-news-2026-03.pdf
    ```

=== "Just the video content"

    ```bash
    qgis-news-gatherer -s youtube,youtube_shorts -v
    ```

=== "Machine readable"

    ```bash
    qgis-news-gatherer -f json -o report.json
    ```

=== "Description and chapters"

    ```bash
    qgis-news-gatherer --show-youtube-desc > description.txt
    qgis-news-gatherer --show-chapters
    ```

## Exit behaviour

A collector that fails does not fail the run. The section is recorded with its
error, the terminal summary shows it, and empty sections are dropped from the
PDF rather than rendered blank. Use `--verbose` to see why a source came back
empty.

## Caching

Responses are cached per month and per section under
`~/.cache/qgis-news-gatherer/YYYY-MM/`, for one hour by default. If a fetch
fails and a stale cache entry exists, the stale data is used and the section
carries a warning saying so. `--force` bypasses the cache entirely.
