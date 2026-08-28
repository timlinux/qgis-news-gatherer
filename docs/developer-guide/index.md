<!-- SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Developer Guide

<div class="grid cards" markdown>

-   :material-file-tree:{ .lg .middle } __Project Structure__

    ---

    How the package fits together, from CLI to collectors to report.

    [:octicons-arrow-right-24: Structure](project-structure.md)

-   :material-plus-box:{ .lg .middle } __Writing a Collector__

    ---

    Add a new source in one file and one registration.

    [:octicons-arrow-right-24: Guide](collectors.md)

-   :material-test-tube:{ .lg .middle } __Testing__

    ---

    How collectors are tested without touching the network.

    [:octicons-arrow-right-24: Testing](testing.md)

-   :material-source-pull:{ .lg .middle } __Contributing__

    ---

    Conventions, commits and the pull request path.

    [:octicons-arrow-right-24: Contributing](contributing.md)

</div>

## The dev shell

```bash
nix develop
nix run .#test
nix run .#lint
nix run .#format
```

Everything CI runs is available locally through the same flake.
