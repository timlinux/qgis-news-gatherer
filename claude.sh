#!/usr/bin/env bash
#
# Queued commands for this session. Claude runs sandboxed and cannot reach
# the network or push, so the git/gh work is collected here for you to run:
#
#     ./claude.sh
#
# Everything it prints is also written to claude.out for Claude to read back.
#
# It is safe to re-run: each step checks whether it has already been done.
# Nothing here deletes files - "git rm --cached" only unstages.

set -uo pipefail

cd "$(dirname "$0")" || exit 1
exec > >(tee claude.out) 2>&1

REPO_SLUG="timlinux/qgis-news-gatherer"
REPO_SSH="git@github.com:timlinux/qgis-news-gatherer.git"
FAILED=0

step() {
    printf '\n=== %s ===\n' "$1"
}

run() {
    printf '$ %s\n' "$*"
    "$@" || { FAILED=1; printf '!! failed (exit %s): %s\n' "$?" "$*"; }
}

step "Preflight"
run git --version
run gh --version
printf '$ gh auth status\n'
if ! gh auth status; then
    printf '!! Not logged in to GitHub. Run: gh auth login\n'
    printf '   Then re-run this script.\n'
    exit 1
fi

step "Drop generated artefacts from the index"
# These are report outputs, now covered by .gitignore. The files stay on disk.
for artefact in qgis-news-2026-03.pdf qgis-shownotes-2026-03.md; do
    if git ls-files --cached --error-unmatch "$artefact" >/dev/null 2>&1; then
        run git rm --cached --quiet "$artefact"
    else
        printf '   already unstaged: %s\n' "$artefact"
    fi
done

step "Commit 1 of 2: initial import"
if [ -z "$(git rev-list -n 1 --all 2>/dev/null)" ]; then
    # The index still holds the code as it was before this session's work,
    # so this commit captures the project as it stood, licence included.
    run git add LICENSE qgis-icon-650x650-bordered.png qgis-logo.svg
    run git commit -q -m "feat: initial import of the QGIS monthly news gatherer

Collects QGIS project activity for the monthly news segment and renders it
as markdown, JSON, HTML and PDF show notes.

Licensed GPL-3.0-or-later."
    run git --no-pager log --oneline -1
else
    printf '   repository already has commits, skipping initial import\n'
fi

step "Lint report (informational, does not block the commit)"
# The repository carries pre-existing ruff/mypy debt that predates this
# session. Recorded here so it is visible, not silently skipped.
printf '$ ruff check src tests\n'
ruff check src tests 2>&1 | tail -5 || true
printf '$ pytest\n'
pytest -q 2>&1 | tail -6 || true

step "Commit 2 of 2: YouTube videos and Shorts sections"
run git add -A
if git diff --cached --quiet; then
    printf '   nothing staged, skipping\n'
else
    run git commit -q -m "feat(youtube): add QGIS videos and Shorts report sections

Adds two report sections enumerating the QGIS videos and Shorts published
on YouTube in the target month, each rendered as badged cards with the most
watched items highlighted and tutorials tagged.

Each section carries an infographic: stat tiles for item count, tutorials,
combined views and the change against last month, plus a grouped bar chart
of items and tutorials published per month. Cross-month counts are recorded
in the cache so the comparison builds up run over run.

YouTube collection moves out of collectors/social.py into its own module.
The search no longer filters to long form videos, and results are parsed
from the videoRenderer, reelItemRenderer and shortsLockupViewModel nodes
wherever they appear, replacing a fixed path YouTube no longer populates
which had left the section silently empty.

Also fixes a KeyError crash in the markdown, JSON and YouTube description
output paths, where chapters no longer carried the timestamp the templates
read.

Bumps the version to 0.2.0 and adds a CHANGELOG."
    run git --no-pager log --oneline -2
fi

step "Create the GitHub repository"
if gh repo view "$REPO_SLUG" >/dev/null 2>&1; then
    printf '   %s already exists\n' "$REPO_SLUG"
else
    run gh repo create "$REPO_SLUG" \
        --public \
        --description "Automated content collection for the QGIS monthly YouTube news segment"
fi

step "Wire up the remote (ssh)"
# gh's own git_protocol setting is https, so set the remote explicitly.
if git remote get-url origin >/dev/null 2>&1; then
    run git remote set-url origin "$REPO_SSH"
else
    run git remote add origin "$REPO_SSH"
fi
run git remote -v

step "Push"
run git push -u origin main

step "Summary"
if [ "$FAILED" -eq 0 ]; then
    printf 'All steps completed.\n'
    printf 'Repository: https://github.com/%s\n' "$REPO_SLUG"
else
    printf 'One or more steps failed - see the output above (also in claude.out).\n'
fi
exit "$FAILED"
