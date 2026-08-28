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

step "Wait for the workflows to register"
# A freshly pushed workflow is not immediately dispatchable.
for attempt in 1 2 3 4 5 6 7 8 9 10; do
    if gh workflow view monthly-report.yml >/dev/null 2>&1; then
        printf '   monthly-report.yml is registered\n'
        break
    fi
    printf '   not registered yet (attempt %s/10), waiting 10s...\n' "$attempt"
    sleep 10
done

step "Trigger the monthly report"
# A manual dispatch skips the last-Thursday gate and defaults to this month.
if gh workflow run monthly-report.yml; then
    printf '   dispatched\n'
    sleep 8
    run_id="$(gh run list --workflow=monthly-report.yml --limit 1 \
        --json databaseId --jq '.[0].databaseId' 2>/dev/null)"
    if [ -n "${run_id:-}" ]; then
        printf '   run: https://github.com/%s/actions/runs/%s\n' "$REPO_SLUG" "$run_id"
        printf '\n   Watching (this takes a few minutes - Nix install, then the\n'
        printf '   gatherer talks to every QGIS source, then the site build):\n\n'
        gh run watch "$run_id" --exit-status || FAILED=1
        printf '\n'
        gh run view "$run_id" --log-failed 2>/dev/null | tail -40 || true
    else
        printf '!! Could not find the run id. Check: gh run list\n'
        FAILED=1
    fi
else
    FAILED=1
    printf '!! Dispatch failed. The workflow may not be registered yet.\n'
    printf '   Try again in a minute: gh workflow run monthly-report.yml\n'
fi

step "Enable GitHub Pages"
if gh api "repos/$REPO_SLUG/pages" >/dev/null 2>&1; then
    printf '   Pages already enabled\n'
elif git ls-remote --exit-code --heads origin gh-pages >/dev/null 2>&1; then
    run gh api -X POST "repos/$REPO_SLUG/pages" \
        -f 'source[branch]=gh-pages' -f 'source[path]=/'
else
    printf '!! gh-pages does not exist yet, so Pages cannot be enabled.\n'
    printf '   That means the publish step did not run. Check the run log above.\n'
fi

step "Where to look"
printf '   Site:    https://timlinux.github.io/qgis-news-gatherer/\n'
printf '   Reports: https://timlinux.github.io/qgis-news-gatherer/reports/\n'
printf '   Actions: https://github.com/%s/actions\n' "$REPO_SLUG"
printf '\n   Pages can take a minute to serve after it is first enabled.\n'

step "Summary"
if [ "$FAILED" -eq 0 ]; then
    printf 'All steps completed.\n'
else
    printf 'One or more steps failed - see the output above (also in claude.out).\n'
fi
exit "$FAILED"
