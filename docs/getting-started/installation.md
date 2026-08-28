<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Installation

## Using Nix (recommended)

The flake pins Python 3.12, WeasyPrint and the Noto font set &mdash; including
the CJK and colour emoji faces the PDF renderer needs. This is the same
environment CI uses, so a PDF you build locally matches the published one.

```bash
git clone https://github.com/timlinux/qgis-news-gatherer.git
cd qgis-news-gatherer
nix develop
```

The shell greets you with the available commands:

| Command | What it does |
|---------|--------------|
| `nix run .#run` | Run the gatherer, passing any CLI arguments |
| `nix run .#report-md` | Markdown show notes (optional `YYYY-MM`) |
| `nix run .#report-pdf` | PDF show notes (optional `YYYY-MM`) |
| `nix run .#report-pdf-no-cache` | PDF, bypassing the cache |
| `nix run .#report-html` | HTML show notes |
| `nix run .#report-youtube` | YouTube description only |
| `nix run .#docs` | Build this documentation site |
| `nix run .#docs-serve` | Serve the docs with live reload |
| `nix run .#test` | Run the test suite |
| `nix run .#lint` | Run ruff and mypy |
| `nix run .#format` | Format and autofix |

With [direnv](https://direnv.net/) installed, `direnv allow` enters the shell
automatically whenever you `cd` into the project.

## Using pip

```bash
python -m pip install -e ".[dev]"
qgis-news-gatherer --help
```

!!! warning "PDF output needs system libraries"

    The PDF renderer is [WeasyPrint](https://weasyprint.org/), which links
    against Pango, HarfBuzz and Cairo. On Debian or Ubuntu:

    ```bash
    sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 \
        libharfbuzz0b fonts-noto fonts-noto-cjk fonts-noto-color-emoji
    ```

    Without the Noto fonts the PDF still builds, but emoji and non-Latin
    scripts fall back to missing-glyph boxes. The Nix shell avoids all of
    this.

## Verifying the install

```bash
qgis-news-gatherer --version
qgis-news-gatherer --list-sections
```

The second command prints every section the tool knows about. If that works,
you are ready for [your first report](first-report.md).
