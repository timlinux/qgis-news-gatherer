<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Mirrored from the repository root by scripts/sync_root_docs.py. -->

# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-08-28

### Added

- MkDocs documentation site, modelled on the Kartoza InfrastructureMapper
  template: Material theme, Kartoza brand tokens with the QGIS palette,
  hero landing page, and guides for users, administrators and developers.
- Published archive of monthly reports at `reports/`, generated from the PDFs
  on the `gh-pages` branch by `scripts/generate_reports_index.py`.
- `monthly-report.yml` workflow: renders the report on the last Thursday of
  each month and publishes the PDF to the archive. The schedule fires daily
  from the 22nd and a gate job decides whether today is the last Thursday,
  because cron ORs day-of-month against day-of-week.
- `docs.yml` workflow building and deploying the site, sharing the build with
  the monthly workflow through the `publish-site` composite action.
- `scripts/sync_root_docs.py`, mirroring SPECIFICATION.md and CHANGELOG.md
  into the site rather than duplicating them.
- `nix run .#docs` and `nix run .#docs-serve`, replacing the placeholder docs
  app; mkdocs and mkdocs-material added to the dev shell.

### Changed

- Report PDFs, generated HTML and scratch screenshots are gitignored; the
  branding assets the report embeds stay tracked.


## [0.2.0] - 2026-08-27

### Added

- `QGIS on YouTube` and `QGIS Shorts` report sections, enumerating the QGIS
  videos and Shorts published in the target month
  (`collectors/youtube.py`, sections `youtube` and `youtube_shorts`).
- Infographic for both YouTube sections: stat tiles (item count, tutorials,
  combined views, change vs last month) and a month-on-month grouped bar
  chart of items and tutorials published.
- Highlighting of the most watched items in each YouTube section, plus a
  `Tutorial` tag for instructional content.
- `grouped_bar_chart()` chart primitive for month-on-month comparisons.
- Cross-month counts recorded in `{cache_dir}/youtube_history.json`, which is
  what makes the month-on-month comparison possible.
- YouTube settings: search URL, `sp` filter, per-section search queries, item
  caps and highlight count.
- Test suite for the YouTube parsing helpers and both collectors, driven by
  canned search payloads (no network access).

### Changed

- YouTube collection moved out of `collectors/social.py` into its own
  `collectors/youtube.py` module.
- YouTube search no longer filters results to long form videos, so Shorts are
  returned as well; results are parsed from `videoRenderer`,
  `reelItemRenderer` and `shortsLockupViewModel` nodes wherever they appear
  in the response rather than at a fixed path.
- `strip_emoji()` moved to `collectors/base.py` and shared by the Mastodon
  and YouTube collectors.

### Fixed

- `KeyError: 'timestamp'` crash in `--format markdown`, `--format json`,
  `--format youtube` and `--show-youtube-desc`: chapters no longer carried
  the timestamp the templates read.
- YouTube search results were parsed at a fixed path that YouTube no longer
  populates, so the section had been silently empty.

[Unreleased]: https://github.com/timlinux/qgis-news-gatherer/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/timlinux/qgis-news-gatherer/releases/tag/v0.3.0
[0.2.0]: https://github.com/timlinux/qgis-news-gatherer/releases/tag/v0.2.0
