# QGIS News Gatherer

Automated content collection for QGIS monthly YouTube news segments.

[![CI](https://github.com/kartoza/qgis-news-gatherer/actions/workflows/ci.yml/badge.svg)](https://github.com/kartoza/qgis-news-gatherer/actions/workflows/ci.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

## Overview

QGIS News Gatherer is a Python CLI tool that automates gathering content for the QGIS monthly YouTube news segment. It collects data from various QGIS project sources and generates a markdown report organized by topic area.

## Features

- **YouTube Show Notes**: Generate ready-to-use video descriptions with chapters and timestamps
- **PDF Export**: Beautiful PDF show notes to share with your audience
- **Multi-source collection**: Gathers news from GitHub, RSS feeds, mailing lists, and more
- **Async processing**: Concurrent data collection for fast results
- **Flexible output**: Terminal, Markdown, JSON, PDF, HTML, or YouTube description
- **Video Chapters**: Auto-generated timestamps for YouTube chapters
- **Configurable sections**: Choose which news sources to include
- **Date filtering**: Automatically filters content to the target month

## Data Sources

| Source | Description |
|--------|-------------|
| GitHub Releases | QGIS version releases |
| Notable Fixes | Merged PRs with bug labels |
| QGIS Blog | Posts from blog.qgis.org |
| News Feed | Items from feed.qgis.org |
| QEPs | QGIS Enhancement Proposals |
| Website Updates | QGIS-Website repository changes |
| Conferences | Event announcements |
| Mailing Lists | Highlights from qgis-user list |
| Translations | Transifex statistics |
| Discussions | GitHub Discussions |

## Installation

### Using Nix (Recommended)

```bash
# Enter development shell
nix develop

# Run the tool
nix run .#run
```

### Using pip

```bash
pip install -e ".[dev]"
qgis-news-gatherer --help
```

## Usage

### Basic Usage

```bash
# Generate show notes for current month (terminal output)
qgis-news-gatherer

# Generate show notes for specific month
qgis-news-gatherer --month 2026-03

# Verbose mode
qgis-news-gatherer -v
```

### Output Formats

```bash
# PDF show notes (great for sharing!)
qgis-news-gatherer --output shownotes.pdf --format pdf

# Markdown with talking points
qgis-news-gatherer --output shownotes.md --format markdown

# YouTube description ready to paste
qgis-news-gatherer --format youtube
qgis-news-gatherer --show-youtube-desc

# Video chapters only
qgis-news-gatherer --show-chapters

# JSON for processing
qgis-news-gatherer --output report.json --format json

# HTML (can print to PDF from browser)
qgis-news-gatherer --output shownotes.html --format html
```

### Section Selection

```bash
# Select specific sections only
qgis-news-gatherer --sections releases,news_feed,blog_posts

# List available sections
qgis-news-gatherer --list-sections
```

### Example Workflow

```bash
# 1. Generate terminal preview
qgis-news-gatherer -m 2026-03

# 2. Generate PDF for team review
qgis-news-gatherer -m 2026-03 -o "QGIS News March 2026.pdf" -f pdf

# 3. Get YouTube description
qgis-news-gatherer -m 2026-03 --show-youtube-desc > youtube-desc.txt
```

## Configuration

Set environment variables or create a `.env` file:

```bash
# GitHub token (optional, increases API rate limits)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# Transifex token (required for translation stats)
TRANSIFEX_TOKEN=xxxxxxxxxxxx
```

## Development

```bash
# Enter development environment
nix develop

# Run tests
nix run .#test

# Run linter
nix run .#lint

# Format code
nix run .#format

# Build documentation
nix run .#docs
```

## Project Structure

```
qgis-news-gatherer/
├── src/qgis_news_gatherer/
│   ├── cli.py           # CLI entry point
│   ├── config.py        # Configuration management
│   ├── report.py        # Report generation
│   └── collectors/      # Data collectors
│       ├── base.py      # Base collector class
│       ├── github.py    # GitHub API collectors
│       ├── feeds.py     # RSS/JSON feed collectors
│       └── ...          # Other collectors
├── tests/               # Test suite
├── docs/                # Documentation
└── flake.nix           # Nix development environment
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/qgis-news-gatherer)
