# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-11-27

### Added

- "QGIS Year at a Glance" timeline: a gray vertical gridline at each month
  boundary, drawn behind the stepper line and event labels.

### Changed

- "QGIS Year at a Glance" timeline content (events, categories, quarter
  cards, bugfix-release recurrence) moved out of `charts.py` and into
  `src/qgis_news_gatherer/data/timeline.json`, so the annual event calendar
  can be edited without touching chart code. The legend now renders
  dynamically from whatever categories are defined in that file.
- YouTube/Shorts sections now label their card list as "top N by views"
  rather than implying a monthly total. The scrape only ever sees a page or
  two of YouTube's search results, so a "total found this month" figure
  would read as an exhaustive count it isn't - the report now just surfaces
  the best-performing videos/Shorts by views, with no claim about how many
  exist in total.
- The PDF's "QGIS on YouTube" / "QGIS Shorts" sections no longer open on a
  stat-tiles-and-monthly-trend-chart page ahead of the actual top-10 card
  grid - with the header already saying "top 10 by views", that page said
  nothing the cards didn't, and just pushed them to the next page. The top
  10 now starts right under the heading. Removed the now-dead
  `_video_stats()` (report.py), the YouTube branch of
  `generate_analytics_charts()` and the `grouped_bar_chart()` helper it was
  the only caller of (charts.py), and the associated `.video-stats` /
  `.video-chart` CSS.
- `youtube_max_videos` / `youtube_max_shorts` default from 8 to 10, to match
  the "top 10 by views" framing.
- `qgis_blog_feed` default from `https://blog.qgis.org/feed/` to
  `https://blog.qgis.org/index.xml` - the blog moved off WordPress onto a
  Hugo-based site, and the old WordPress feed path now 404s.

### Fixed

- The blog feed collector (and the conference-announcement scan, and the
  Planet QGIS collector) crashed with `year 0 is out of range` whenever a
  feed contained an entry with no publish date. Hugo's RSS template renders
  a missing date as its zero `time.Time` value
  (`Mon, 01 Jan 0001 00:00:00 +0000`), which `time.mktime` cannot convert to
  a POSIX timestamp - the new `blog.qgis.org/index.xml` feed includes exactly
  one such entry (a static `/funders/` page with no front-matter date), which
  took down the whole `blog_posts` section. Extracted a shared
  `parse_feed_entry_date()` helper in `collectors/base.py` that treats an
  unconvertible date as "no date" instead of raising, and reused it across
  all four feedparser-based collectors that had duplicated this exact
  date-parsing pattern.
- "QGIS Year at a Glance" timeline: the TODAY ribbon was pinned to a fixed
  offset from its quarter-card's right edge regardless of where in the card
  the current date actually fell, so it visually pointed at the wrong date
  except when "today" happened to land near the end of its card. It's now
  anchored to the actual today tick on the stepper line (clamped to stay
  inside the card), stands vertically instead of on a 40° diagonal, and is
  drawn before (so it paints behind) the card's own month/event labels, so
  it no longer covers a label that happens to sit near today's date.
- "QGIS Year at a Glance" timeline: long event labels (e.g. "FOSS4G
  International Conference" next to "Feature release + LTR designation")
  could render on top of each other when their dates landed close together.
  Labels longer than 18 characters now word-wrap onto two lines, which
  halves their horizontal footprint and resolves the collision in practice.

## [0.4.0] - 2026-09-21

### Added

- "QGIS Year at a Glance" PDF slide, placed right after the chapters slide:
  three quarter-cards covering all 12 months, styled after the stepper/
  ribbon look of qgis.org/resources/roadmap/ (light card panels, a
  green-vs-pending-grey progress line, filled dots for events already past
  and hollow dots for events still ahead, and a folded ribbon flagging
  "today"). Plots the project's recurring annual cycle (feature/LTR/bugfix
  releases, budget year, financial report, grant call/awards, monthly Open
  Day, FOSS4G, the User Conference, and the AGM cycle). Implemented as
  `generate_year_timeline_svg()` in `charts.py`, grounded in publicly
  documented QGIS scheduling patterns.

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

[Unreleased]: https://github.com/timlinux/qgis-news-gatherer/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/timlinux/qgis-news-gatherer/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/timlinux/qgis-news-gatherer/releases/tag/v0.3.0
[0.2.0]: https://github.com/timlinux/qgis-news-gatherer/releases/tag/v0.2.0
