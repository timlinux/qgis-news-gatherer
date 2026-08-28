<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Getting Started

Three steps from a clean checkout to a finished report.

<div class="grid cards" markdown>

-   :material-download-box:{ .lg .middle } __1. Install__

    ---

    A Nix flake provisions Python, WeasyPrint and the fonts the PDF needs.
    A pip install works too.

    [:octicons-arrow-right-24: Installation](installation.md)

-   :material-play-circle:{ .lg .middle } __2. Run it__

    ---

    No arguments gathers the current month and prints to the terminal.

    [:octicons-arrow-right-24: Your first report](first-report.md)

-   :material-tune:{ .lg .middle } __3. Tune it__

    ---

    Add a GitHub token to lift the rate limit, pick the sections you care
    about, choose an output format.

    [:octicons-arrow-right-24: Configuration](../admin-guide/configuration.md)

</div>

## In a hurry

```bash
git clone https://github.com/timlinux/qgis-news-gatherer.git
cd qgis-news-gatherer
nix develop
nix run .#report-pdf
```

That writes `qgis-news-YYYY-MM.pdf` for the current month into the working
directory.

!!! tip "You may not need to install anything"

    If you only want to read the report, the last Thursday of every month a
    GitHub Action publishes it to the [report archive](../reports/index.md).
