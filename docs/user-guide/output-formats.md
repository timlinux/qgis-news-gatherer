<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Output Formats

Pick with `--format`, write to a file with `--output`.

| Format | Extension | Use it for |
|--------|-----------|------------|
| `terminal` | &mdash; | Reading the month at a glance. The default. |
| `markdown` | `.md` | Drafting the script. Talking points per section. |
| `json` | `.json` | Feeding another tool. Every item, structured. |
| `pdf` | `.pdf` | The slide deck for the recording. |
| `html` | `.html` | The same deck in a browser. |
| `youtube` | `.txt` | The video description, ready to paste. |

## Terminal

A summary table of every source with its status and item count, then the
sections themselves. Sources that failed are visible rather than silently
missing.

## Markdown

Full show notes: a summary, the chapter list, then each section with numbered
talking points, descriptions and links. This is the drafting format.

## JSON

Everything the collectors returned, including per-item `metadata` &mdash; view
counts, engagement figures, chart series. Also carries the chapter list, the
deduplicated link list and the generated YouTube description.

```bash
qgis-news-gatherer -f json -o report.json
jq '.sections[] | select(.section_name == "youtube") | .items[].title' report.json
```

## PDF and HTML

The presentation deck: a title slide, a contents slide, a highlights slide,
one slide per section, an all-links slide and a closing slide. Charts are
inline SVG, so the PDF has no external dependencies and prints cleanly at A4.

```bash
qgis-news-gatherer -m 2026-03 -f pdf -o qgis-news-2026-03.pdf
```

!!! note "Fonts matter here"

    Text is set in Noto, with the CJK and colour emoji faces bundled by the
    Nix shell. Building outside Nix without those fonts installed gives
    missing-glyph boxes wherever the community wrote in a non-Latin script.

## YouTube description

```bash
qgis-news-gatherer --show-youtube-desc
```

Produces the description with chapter timestamps and every link grouped under
its section heading. Timestamps are estimated from section sizes &mdash; a
starting point to adjust against the recording.
