#!/usr/bin/env bash
#
# Queued commands for this session. Claude runs sandboxed and cannot reach the
# network, so the git/gh work is collected here for you to run:
#
#     ./claude.sh
#
# Everything it prints is also written to claude.out for Claude to read back.
# Safe to re-run: each step checks whether it has already been done.

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
printf '$ gh auth status\n'
if ! gh auth status; then
    printf '!! Not logged in to GitHub. Run: gh auth login\n'
    exit 1
fi

step "Remote"
if git remote get-url origin >/dev/null 2>&1; then
    run git remote set-url origin "$REPO_SSH"
else
    run git remote add origin "$REPO_SSH"
fi
run git remote -v

step "Checks (informational, does not block the commit)"
printf '$ pytest\n'
pytest -q 2>&1 | tail -6 || true

step "Commit the documentation site and monthly automation"
run git add -A
if git diff --cached --quiet; then
    printf '   nothing staged, skipping\n'
else
    run git commit -q -m "feat(docs): add documentation site and monthly report automation

Adds a MkDocs site modelled on the Kartoza InfrastructureMapper template:
Material theme, Kartoza brand tokens carrying the QGIS palette, a hero
landing page, and guides for users, administrators and developers.

A scheduled workflow renders the report on the last Thursday of each month
and publishes the PDF to an archive page on the site. Cron cannot express
'last Thursday', and ORs day-of-month against day-of-week, so the schedule
fires daily from the 22nd and a gate job decides whether today qualifies.

Both the docs workflow and the monthly workflow publish through one
composite action, which restores the existing archive from gh-pages before
each build so previously published reports survive a redeploy.

Bumps the version to 0.3.0."
    run git --no-pager log --oneline -3
fi

step "Push"
run git push -u origin main

step "Enable GitHub Pages"
if gh api "repos/$REPO_SLUG/pages" >/dev/null 2>&1; then
    printf '   Pages already enabled\n'
else
    printf '   Pages is not enabled yet.\n'
    printf '   The gh-pages branch is created by the first Docs workflow run,\n'
    printf '   so enable Pages after that run finishes:\n'
    printf '     gh api -X POST repos/%s/pages \\\n' "$REPO_SLUG"
    printf "       -f 'source[branch]=gh-pages' -f 'source[path]=/'\n"
    printf '   or Settings > Pages > Deploy from a branch > gh-pages / (root)\n'
fi

step "Watch the docs build"
printf '   gh run watch --exit-status\n'
printf '   Site: https://timlinux.github.io/qgis-news-gatherer/\n'

step "Trigger a report by hand (optional)"
printf '   The schedule next fires on the last Thursday of the month.\n'
printf '   To publish one now:\n'
printf '     gh workflow run monthly-report.yml\n'

step "Summary"
if [ "$FAILED" -eq 0 ]; then
    printf 'All steps completed.\n'
else
    printf 'One or more steps failed - see the output above (also in claude.out).\n'
fi
exit "$FAILED"
