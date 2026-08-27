# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/timlinux/qgis-news-gatherer/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/timlinux/qgis-news-gatherer/releases/tag/v0.2.0
