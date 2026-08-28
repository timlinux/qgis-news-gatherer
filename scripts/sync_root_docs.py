# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Mirror root markdown documents into the MkDocs site.

SPECIFICATION.md and CHANGELOG.md are maintained at the repository root, where
contributors expect them. The site needs its own copy under docs/, so this
script copies them with an SPDX header rather than duplicating the prose by
hand. Run by the docs workflow before building.

Usage:
    python scripts/sync_root_docs.py
"""

from __future__ import annotations

from pathlib import Path

HEADER = (
    "<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->\n"
    "<!-- SPDX-License-Identifier: GPL-3.0-or-later -->\n"
    "<!-- Mirrored from the repository root by scripts/sync_root_docs.py. -->\n\n"
)

MIRRORS = {
    Path("SPECIFICATION.md"): Path("docs/about/specification.md"),
    Path("CHANGELOG.md"): Path("docs/about/changelog.md"),
}


def main() -> int:
    """Copy each root document into its place in the docs tree."""
    for source, target in MIRRORS.items():
        if not source.exists():
            print(f"Skipping {source}: not found")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(HEADER + source.read_text())
        print(f"Mirrored {source} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
