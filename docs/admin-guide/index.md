<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Administrator Guide

For whoever keeps the gatherer running and the archive published.

<div class="grid cards" markdown>

-   :material-key-variant:{ .lg .middle } __Configuration__

    ---

    Environment variables, API tokens, cache behaviour and timeouts.

    [:octicons-arrow-right-24: Settings](configuration.md)

-   :material-robot:{ .lg .middle } __Monthly Automation__

    ---

    The scheduled Action, how "last Thursday" is computed, and how the
    archive is published.

    [:octicons-arrow-right-24: Automation](automation.md)

</div>

## Operational notes

- **Nothing is stored server-side.** The tool holds no database. The only
  persistent state is the cache directory and the YouTube history file.
- **Failures are soft.** A source that is down produces a warning and an empty
  section, not a failed run.
- **Rate limits are the usual culprit.** Unauthenticated GitHub requests are
  capped at 60 an hour, which a full run can exhaust. Set `GITHUB_TOKEN`.
