<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Sections

Each section is one collector talking to one source. Select a subset with
`--sections`, or run `--list-sections` to see the live list.

## Project activity

| Section | Collects |
|---------|----------|
| `releases` | QGIS releases and changelog entries from GitHub |
| `notable_fixes` | All merged pull requests for the month |
| `merged_prs` | Key merged pull requests: features and improvements |
| `qeps` | QGIS Enhancement Proposals, open and merged |
| `website_updates` | Changes to the QGIS-Website repository |
| `discussions` | GitHub Discussions highlights |
| `grant_proposals` | Grant programme updates |

## Publishing and community

| Section | Collects |
|---------|----------|
| `blog_posts` | Posts from blog.qgis.org |
| `planet` | Community posts from Planet QGIS |
| `news_feed` | Items from feed.qgis.org |
| `mailing_lists_user` | Threads from the QGIS Users list |
| `mailing_lists_developer` | Threads from the QGIS Developer list |
| `discourse` | Threads in the OSGeo Discourse QGIS category |
| `psc_minutes` | Project Steering Committee minutes |
| `conferences` | Conference and event announcements |
| `user_groups` | User group registrations and activity |
| `sustaining_members` | New and current sustaining members |

## Media

| Section | Collects |
|---------|----------|
| `youtube` | QGIS videos published this month |
| `youtube_shorts` | QGIS Shorts published this month |
| `mastodon` | Top QGIS mentions on Mastodon by engagement |

See [YouTube sections](youtube.md) for how those two work.

## Numbers

| Section | Collects |
|---------|----------|
| `analytics` | Usage analytics from feed.qgis.org |
| `plugin_stats` | Plugin download statistics from plugins.qgis.org |
| `translations` | Translation progress from Transifex |

## Sections that need a token

Most sources are public. Two benefit from credentials:

- `GITHUB_TOKEN` lifts the GitHub rate limit from 60 to 5000 requests an hour.
  Without it the GitHub-backed sections may come back partial on a busy month.
- `TRANSIFEX_TOKEN` is required for `translations`.

See [Configuration](../admin-guide/configuration.md).

## Rendering

Sections render differently depending on what they hold:

- **Compact list** &mdash; mailing lists, Discourse, website updates,
  notable fixes: dense three-column link lists.
- **Cards** &mdash; QEPs, sustaining members, user groups.
- **Charts** &mdash; analytics, plugin stats, sustaining members, user groups
  and both YouTube sections get inline SVG charts.
- **Video cards** &mdash; the YouTube sections, with type badges and stat tiles.

An empty section is dropped from the PDF entirely rather than rendered as a
blank slide.
