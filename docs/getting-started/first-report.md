<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Your First Report

## Look at the current month

```bash
qgis-news-gatherer
```

With no arguments the tool gathers the current calendar month and renders it
to the terminal: a table showing which sources succeeded, then each section
with its items.

The first run takes a minute or two &mdash; it is talking to a dozen or so
services. Responses are cached, so the next run is close to instant.

## Pick a month

```bash
qgis-news-gatherer --month 2026-03
```

Anything with a date outside March 2026 is filtered out.

## Write a PDF

```bash
qgis-news-gatherer --month 2026-03 --format pdf --output qgis-news-2026-03.pdf
```

Or, in the Nix shell, the same thing with the paths handled for you:

```bash
nix run .#report-pdf 2026-03
```

## Get the YouTube description

Once the video is recorded, the description and chapter markers are one
command away:

```bash
qgis-news-gatherer --month 2026-03 --show-youtube-desc
```

Chapter timestamps are estimated from how many items each section holds, so
treat them as a starting point and nudge them to match the recording.

## Narrow it down

While drafting, gathering everything is slow. Ask for the sections you are
working on:

```bash
qgis-news-gatherer --sections releases,merged_prs,youtube,youtube_shorts
```

## When something looks stale

Results are cached for an hour. To force fresh data:

```bash
qgis-news-gatherer --force
```

Add `--verbose` to watch each collector as it works &mdash; useful when a
source is slow or a section comes back empty.

## Next

- [Command line reference](../user-guide/cli.md) &mdash; every option
- [Sections](../user-guide/sections.md) &mdash; what each one collects
- [Output formats](../user-guide/output-formats.md) &mdash; when to use which
