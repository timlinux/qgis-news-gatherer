---
hide:
  - navigation
  - toc
---
<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

<div class="kz-hero" markdown>

<span class="kz-eyebrow">KARTOZA · QGIS NEWS GATHERER</span>

# A month of QGIS, gathered while you sleep

Every release, pull request, blog post, forum thread, user group and video
&mdash; collected from the whole project and handed to you as show notes.

<div class="kz-cta" markdown>
[:material-rocket-launch: Get Started](getting-started/index.md){ .kz-cta__primary }
[:material-file-document-multiple: Monthly Reports](reports/index.md){ .kz-cta__secondary }
[:simple-github: GitHub](https://github.com/timlinux/qgis-news-gatherer){ .kz-cta__secondary }
</div>

</div>

## What it is

QGIS News Gatherer is a Python command line tool that assembles the content for
the QGIS monthly news segment. It queries every corner of the project &mdash;
GitHub, the blog, Planet QGIS, the mailing lists, Discourse, the plugin
repository, analytics, Transifex, the user group registry, Mastodon and YouTube
&mdash; filters everything to one calendar month, and renders the result as
presenter-ready show notes.

Run it for the current month with no arguments. Point it at any past month with
`--month`. Take the PDF into the studio, paste the description straight into
YouTube.

## Get the latest report

The last Thursday of every month, a GitHub Action runs the gatherer and
publishes the PDF here &mdash; no local install required.

<div class="grid cards" markdown>

-   :material-file-pdf-box:{ .lg .middle } __This month's PDF__

    ---

    The full slide-formatted report: releases, fixes, community activity,
    analytics charts and the YouTube round-up.

    [:octicons-arrow-right-24: Browse the archive](reports/index.md)

-   :material-console:{ .lg .middle } __Run it yourself__

    ---

    One `nix develop` away. Generate any month, any format, any subset of
    sections.

    [:octicons-arrow-right-24: Installation](getting-started/installation.md)

-   :material-tune:{ .lg .middle } __Make it yours__

    ---

    Twenty-two sections, five output formats, and an API token or two for the
    rate-limited sources.

    [:octicons-arrow-right-24: Configuration](admin-guide/configuration.md)

</div>

## What's in the box

<div class="grid cards" markdown>

-   :material-source-branch:{ .lg .middle } __Every QGIS source, one report__

    ---

    Releases and merged PRs from GitHub, QEPs, website changes, blog and
    Planet posts, mailing lists, Discourse threads, PSC minutes, translation
    progress and sustaining members.

    [:octicons-arrow-right-24: The section catalogue](user-guide/sections.md)

-   :material-youtube:{ .lg .middle } __Videos and Shorts__

    ---

    QGIS videos and Shorts published in the month, ranked by views, tutorials
    tagged, with a month-on-month infographic of how the community's output is
    trending.

    [:octicons-arrow-right-24: YouTube sections](user-guide/youtube.md)

-   :material-chart-box:{ .lg .middle } __Charts, not just lists__

    ---

    Usage analytics, plugin downloads, user groups per year and sustaining
    member levels are rendered as inline SVG charts straight into the PDF.

    [:octicons-arrow-right-24: Output formats](user-guide/output-formats.md)

-   :material-clock-outline:{ .lg .middle } __Show notes and chapters__

    ---

    A YouTube description with estimated chapter timestamps and every link,
    grouped by section, ready to paste.

    [:octicons-arrow-right-24: Your first report](getting-started/first-report.md)

-   :material-robot:{ .lg .middle } __Runs itself monthly__

    ---

    A scheduled Action fires on the last Thursday of each month, renders the
    PDF and publishes it to this site's archive.

    [:octicons-arrow-right-24: Monthly automation](admin-guide/automation.md)

-   :material-snowflake:{ .lg .middle } __Reproducible Nix dev shell__

    ---

    One flake provisions Python, WeasyPrint and the Noto font set CI uses, so
    the PDF you build locally is the PDF the robot builds.

    [:octicons-arrow-right-24: Project structure](developer-guide/project-structure.md)

</div>

## QA status

[![CI](https://github.com/timlinux/qgis-news-gatherer/actions/workflows/ci.yml/badge.svg)](https://github.com/timlinux/qgis-news-gatherer/actions/workflows/ci.yml)
[![Docs](https://github.com/timlinux/qgis-news-gatherer/actions/workflows/docs.yml/badge.svg)](https://github.com/timlinux/qgis-news-gatherer/actions/workflows/docs.yml)
[![Monthly report](https://github.com/timlinux/qgis-news-gatherer/actions/workflows/monthly-report.yml/badge.svg)](https://github.com/timlinux/qgis-news-gatherer/actions/workflows/monthly-report.yml)

<div class="kz-footer-credits" markdown>
Made with 💗 by [Kartoza](https://kartoza.com) &middot;
[Sponsor on GitHub](https://github.com/sponsors/kartoza) &middot;
[Repository](https://github.com/timlinux/qgis-news-gatherer)
</div>
