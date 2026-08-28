<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# User Guide

For the person who prepares the monthly news segment.

<div class="grid cards" markdown>

-   :material-console:{ .lg .middle } __Command Line__

    ---

    Every option, with the flags you will actually reach for.

    [:octicons-arrow-right-24: Reference](cli.md)

-   :material-format-list-bulleted:{ .lg .middle } __Sections__

    ---

    All twenty-two sources, what each collects and where it comes from.

    [:octicons-arrow-right-24: Catalogue](sections.md)

-   :material-file-export:{ .lg .middle } __Output Formats__

    ---

    Terminal, markdown, JSON, HTML, PDF and the YouTube description.

    [:octicons-arrow-right-24: Formats](output-formats.md)

-   :material-youtube:{ .lg .middle } __YouTube Sections__

    ---

    How videos and Shorts are found, ranked and charted.

    [:octicons-arrow-right-24: Details](youtube.md)

</div>

## The monthly rhythm

1. **Gather** &mdash; `qgis-news-gatherer --month 2026-03` and read the terminal
   output to see what kind of month it was.
2. **Draft** &mdash; `--format markdown` gives talking points per section to
   write the script from.
3. **Present** &mdash; `--format pdf` is the slide deck for the recording.
4. **Publish** &mdash; `--show-youtube-desc` is the description and chapters,
   ready to paste.
