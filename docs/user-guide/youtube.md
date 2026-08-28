<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# YouTube Sections

Two sections cover what the community published on YouTube in the month:

- **`youtube`** &mdash; QGIS on YouTube: long form videos
- **`youtube_shorts`** &mdash; QGIS Shorts

They are separate on purpose. A ten minute walkthrough and a thirty second tip
are different kinds of content, and mixing them into one ranked list buries
one behind the other.

## What each section shows

**Stat tiles** across the top: items this month, how many were tutorials,
combined view count, and the change against last month.

**A month-on-month chart**: items published and tutorials published, per
month, as grouped bars.

**Cards**: one per video, ranked by view count, each showing

- a `VIDEO` or `SHORT` badge
- the runtime, where YouTube reports one
- a `Tutorial` tag when the title reads as instructional
- a `Most watched` tag on the top three, suppressed when the section holds
  three or fewer items &mdash; badging everything says nothing

## How videos are found

YouTube has no free, key-less search API, so the collectors read the
`ytInitialData` JSON embedded in the search results page:

```
https://www.youtube.com/results?search_query=QGIS&sp=EgIIBA%3D%3D
```

The `sp` filter restricts results to uploads from the current month and
applies no type filter, so long form videos and Shorts both come back. Results
are read from the `videoRenderer`, `reelItemRenderer` and
`shortsLockupViewModel` nodes wherever they appear in the document, rather
than at a fixed path &mdash; YouTube reshuffles the envelope around results
far more often than it changes the leaf renderers.

Anything YouTube serves from a `/shorts/` URL, or that runs to three minutes
or less, counts as a Short.

## Tutorial detection

A video is tagged as a tutorial when its title or description contains one of
a list of instructional keywords &mdash; *tutorial*, *how to*, *guide*,
*walkthrough*, *getting started*, *beginner*, *step by step* and similar. It
is a heuristic on titles, not a judgement about the content.

## Dates, and their limits

!!! warning "Shorts have no publish date"

    Long form results carry a relative upload date &mdash; "3 days ago" &mdash;
    which is resolved to an approximate date and filtered to the target month.
    Shorts results carry no date at all. Because the search is already
    filtered to this month's uploads, undated Shorts are kept when the report
    targets the current month, and dropped otherwise.

    In practice: generating a report for a **past** month returns few or no
    Shorts. Run the gatherer within the month you want, which is what the
    [monthly automation](../admin-guide/automation.md) does.

## The month-on-month chart

YouTube only reports "this month", so there is nothing to query for last
month's number. Instead every run appends its counts to

```
~/.cache/qgis-news-gatherer/youtube_history.json
```

and the chart is drawn from that file. Two consequences:

- The first ever run has no comparison, so the "vs last month" tile is absent
  and the chart shows a single month.
- History accumulates on whichever machine runs the gatherer. The scheduled
  Action keeps its own history in the CI cache, which is why the automation
  restores that cache between runs.

## Configuration

| Setting | Default | Purpose |
|---------|---------|---------|
| `YOUTUBE_SEARCH_QUERIES` | `["QGIS", "QGIS tutorial"]` | Searches for the videos section |
| `YOUTUBE_SHORTS_SEARCH_QUERIES` | `["QGIS shorts", "QGIS"]` | Searches for the Shorts section |
| `YOUTUBE_MAX_VIDEOS` | `8` | Cards in the videos section |
| `YOUTUBE_MAX_SHORTS` | `8` | Cards in the Shorts section |
| `YOUTUBE_HIGHLIGHT_COUNT` | `3` | How many get `Most watched` |
| `YOUTUBE_SEARCH_FILTER` | `EgIIBA%3D%3D` | YouTube's `sp` filter: uploads this month |

!!! danger "This is scraping, and scraping breaks"

    There is no API contract here. If YouTube changes its response shape the
    sections go empty and the run records a warning rather than failing. If
    both sections are consistently empty, that is the first thing to check
    &mdash; see [the collector source][src].

[src]: https://github.com/timlinux/qgis-news-gatherer/blob/main/src/qgis_news_gatherer/collectors/youtube.py
