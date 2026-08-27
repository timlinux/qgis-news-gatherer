# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""GitHub-based collectors for releases, PRs, discussions, and QEPs."""

from datetime import datetime

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult, NewsItem
from qgis_news_gatherer.config import settings


class ReleasesCollector(BaseCollector):
    """Collect QGIS releases from GitHub."""

    section_name = "releases"
    section_title = "Releases"

    async def collect(self) -> CollectorResult:
        """Fetch releases from GitHub API."""
        self.log_verbose("Fetching releases from GitHub...")

        url = f"{settings.github_api_url}/repos/{settings.qgis_repo}/releases"
        response = await self.client.get(url, headers=settings.get_github_headers())
        response.raise_for_status()

        releases = response.json()
        items: list[NewsItem] = []

        for release in releases:
            published_at = release.get("published_at")
            if published_at:
                release_date = datetime.fromisoformat(published_at.replace("Z", "+00:00")).date()

                if self.is_in_month(release_date):
                    tag = release.get("tag_name", "")
                    name = release.get("name", tag)
                    is_prerelease = release.get("prerelease", False)
                    is_ltr = "ltr" in tag.lower() or "ltr" in name.lower()

                    version_type = ""
                    if is_prerelease:
                        version_type = " (Pre-release)"
                    elif is_ltr:
                        version_type = " (LTR)"

                    items.append(
                        NewsItem(
                            title=f"{name}{version_type}",
                            url=release.get("html_url"),
                            description=release.get("body", "")[:500] if release.get("body") else None,
                            date=release_date,
                            author=release.get("author", {}).get("login"),
                            tags=["release", "ltr" if is_ltr else "regular"],
                            metadata={
                                "tag_name": tag,
                                "prerelease": is_prerelease,
                                "draft": release.get("draft", False),
                            },
                        )
                    )

        self.log_verbose(f"Found {len(items)} releases in target month")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
        )


class NotableFixesCollector(BaseCollector):
    """Collect every PR merged into qgis/QGIS during the target month."""

    section_name = "notable_fixes"
    section_title = "Merged PRs"

    async def collect(self) -> CollectorResult:
        """Fetch every merged PR from GitHub, paginating to 1000 results."""
        self.log_verbose("Fetching all merged PRs from GitHub...")

        month_start = self.config.month_start().isoformat()
        month_end = self.config.month_end().isoformat()

        query = (
            f"repo:{settings.qgis_repo} is:pr is:merged "
            f"merged:{month_start}..{month_end}"
        )

        url = f"{settings.github_api_url}/search/issues"
        items: list[NewsItem] = []
        warnings: list[str] = []
        incomplete = False

        # GitHub Search API caps at 1000 results: 10 pages * 100 per_page.
        for page in range(1, 11):
            params = {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": 100,
                "page": page,
            }
            response = await self.client.get(
                url, params=params, headers=settings.get_github_headers()
            )
            response.raise_for_status()
            data = response.json()
            page_items = data.get("items", [])
            if data.get("incomplete_results"):
                incomplete = True

            for pr in page_items:
                merged_at = pr.get("pull_request", {}).get("merged_at")
                if merged_at:
                    merged_date = datetime.fromisoformat(
                        merged_at.replace("Z", "+00:00")
                    ).date()
                else:
                    merged_date = None

                labels = [label.get("name", "") for label in pr.get("labels", [])]

                items.append(
                    NewsItem(
                        title=pr.get("title", "Untitled"),
                        url=pr.get("html_url"),
                        description=pr.get("body", "")[:300] if pr.get("body") else None,
                        date=merged_date,
                        author=pr.get("user", {}).get("login"),
                        tags=labels,
                        metadata={
                            "pr_number": pr.get("number"),
                            "state": pr.get("state"),
                        },
                    )
                )

            if len(page_items) < 100:
                break

        if incomplete:
            warnings.append("Search results may be incomplete due to GitHub API limits")

        self.log_verbose(f"Found {len(items)} merged PRs")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )


class MergedPRsCollector(BaseCollector):
    """Collect key merged PRs (features, improvements) from the QGIS repo."""

    section_name = "merged_prs"
    section_title = "Key Merged Pull Requests"

    # Labels that indicate bug fixes (already covered by NotableFixesCollector)
    BUG_LABELS = {"bug", "bugfix", "bug fix", "crash", "regression"}

    # Labels that indicate significant/notable PRs worth highlighting
    NOTABLE_LABELS = {
        "feature", "enhancement", "new feature", "improvement",
        "performance", "documentation", "API", "processing",
        "3d", "labeling", "rendering", "expressions", "layout",
        "server", "authentication", "data provider", "digitizing",
        "gps", "sketching", "sketchers",
    }

    async def collect(self) -> CollectorResult:
        """Fetch key merged PRs from GitHub API."""
        self.log_verbose("Fetching key merged PRs from GitHub...")

        month_start = self.config.month_start().isoformat()
        month_end = self.config.month_end().isoformat()

        items: list[NewsItem] = []
        warnings: list[str] = []

        # Strategy 1: Search for PRs with notable labels
        for label in ["feature", "enhancement", "new feature", "performance"]:
            query = (
                f"repo:{settings.qgis_repo} is:pr is:merged "
                f"merged:{month_start}..{month_end} "
                f"label:\"{label}\""
            )

            url = f"{settings.github_api_url}/search/issues"
            params = {"q": query, "sort": "reactions", "order": "desc", "per_page": 30}

            response = await self.client.get(
                url, params=params, headers=settings.get_github_headers()
            )
            response.raise_for_status()

            data = response.json()
            for pr in data.get("items", []):
                pr_number = pr.get("number")
                # Skip if already added
                if any(
                    i.metadata.get("pr_number") == pr_number for i in items
                ):
                    continue

                labels = {
                    label.get("name", "").lower()
                    for label in pr.get("labels", [])
                }
                # Skip bug fixes (covered by NotableFixesCollector)
                if labels & self.BUG_LABELS:
                    continue

                merged_at = pr.get("pull_request", {}).get("merged_at")
                merged_date = None
                if merged_at:
                    merged_date = datetime.fromisoformat(
                        merged_at.replace("Z", "+00:00")
                    ).date()

                display_labels = sorted(
                    labels - {"feature", "enhancement", "new feature"}
                )

                items.append(
                    NewsItem(
                        title=pr.get("title", "Untitled"),
                        url=pr.get("html_url"),
                        description=pr.get("body", "")[:300]
                        if pr.get("body")
                        else None,
                        date=merged_date,
                        author=pr.get("user", {}).get("login"),
                        tags=display_labels,
                        metadata={
                            "pr_number": pr_number,
                            "reactions": pr.get("reactions", {}).get(
                                "total_count", 0
                            ),
                            "comments": pr.get("comments", 0),
                        },
                    )
                )

        # Strategy 2: Also get most-reacted merged PRs (popular PRs)
        query = (
            f"repo:{settings.qgis_repo} is:pr is:merged "
            f"merged:{month_start}..{month_end} "
            f"comments:>3"
        )

        url = f"{settings.github_api_url}/search/issues"
        params = {
            "q": query,
            "sort": "reactions",
            "order": "desc",
            "per_page": 20,
        }

        response = await self.client.get(
            url, params=params, headers=settings.get_github_headers()
        )
        response.raise_for_status()

        data = response.json()
        for pr in data.get("items", []):
            pr_number = pr.get("number")
            if any(i.metadata.get("pr_number") == pr_number for i in items):
                continue

            labels = {
                label.get("name", "").lower()
                for label in pr.get("labels", [])
            }
            if labels & self.BUG_LABELS:
                continue

            merged_at = pr.get("pull_request", {}).get("merged_at")
            merged_date = None
            if merged_at:
                merged_date = datetime.fromisoformat(
                    merged_at.replace("Z", "+00:00")
                ).date()

            items.append(
                NewsItem(
                    title=pr.get("title", "Untitled"),
                    url=pr.get("html_url"),
                    description=pr.get("body", "")[:300]
                    if pr.get("body")
                    else None,
                    date=merged_date,
                    author=pr.get("user", {}).get("login"),
                    tags=sorted(labels),
                    metadata={
                        "pr_number": pr_number,
                        "reactions": pr.get("reactions", {}).get(
                            "total_count", 0
                        ),
                        "comments": pr.get("comments", 0),
                    },
                )
            )

        if data.get("incomplete_results"):
            warnings.append(
                "Search results may be incomplete due to GitHub API limits"
            )

        # Sort by reactions + comments (most notable first)
        items.sort(
            key=lambda x: (
                x.metadata.get("reactions", 0) + x.metadata.get("comments", 0)
            ),
            reverse=True,
        )

        # Limit to top items
        items = items[:20]

        self.log_verbose(f"Found {len(items)} key merged PRs")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
            warnings=warnings,
        )


class QEPsCollector(BaseCollector):
    """Collect QGIS Enhancement Proposals updates."""

    section_name = "qeps"
    section_title = "QGIS Enhancement Proposals"

    async def collect(self) -> CollectorResult:
        """Fetch QEP updates from GitHub."""
        self.log_verbose("Fetching QEPs from GitHub...")

        # Get recent commits to the QEPs repo
        month_start = self.config.month_start().isoformat()
        month_end = self.config.month_end().isoformat()

        url = f"{settings.github_api_url}/repos/{settings.qgis_qeps_repo}/commits"
        params = {"since": f"{month_start}T00:00:00Z", "until": f"{month_end}T23:59:59Z"}

        response = await self.client.get(
            url, params=params, headers=settings.get_github_headers()
        )
        response.raise_for_status()

        commits = response.json()
        items: list[NewsItem] = []

        for commit in commits:
            commit_date_str = commit.get("commit", {}).get("committer", {}).get("date")
            if commit_date_str:
                commit_date = datetime.fromisoformat(
                    commit_date_str.replace("Z", "+00:00")
                ).date()
            else:
                commit_date = None

            message = commit.get("commit", {}).get("message", "")
            first_line = message.split("\n")[0]

            items.append(
                NewsItem(
                    title=first_line,
                    url=commit.get("html_url"),
                    description=message if len(message) > len(first_line) else None,
                    date=commit_date,
                    author=commit.get("commit", {}).get("author", {}).get("name"),
                    category="QEP",
                    metadata={
                        "sha": commit.get("sha"),
                    },
                )
            )

        # Also fetch open PRs for QEPs
        pr_url = f"{settings.github_api_url}/repos/{settings.qgis_qeps_repo}/pulls"
        pr_response = await self.client.get(
            pr_url, params={"state": "all"}, headers=settings.get_github_headers()
        )
        pr_response.raise_for_status()

        for pr in pr_response.json():
            created_at = pr.get("created_at")
            updated_at = pr.get("updated_at")

            pr_date = None
            if created_at:
                pr_date = datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()

            if self.is_in_month(pr_date) or (
                updated_at
                and self.is_in_month(
                    datetime.fromisoformat(updated_at.replace("Z", "+00:00")).date()
                )
            ):
                state = pr.get("state", "unknown")
                merged = pr.get("merged_at") is not None

                status = "Merged" if merged else state.capitalize()

                items.append(
                    NewsItem(
                        title=f"[{status}] {pr.get('title', 'Untitled')}",
                        url=pr.get("html_url"),
                        description=pr.get("body", "")[:300] if pr.get("body") else None,
                        date=pr_date,
                        author=pr.get("user", {}).get("login"),
                        category="QEP PR",
                        metadata={
                            "pr_number": pr.get("number"),
                            "state": state,
                            "merged": merged,
                        },
                    )
                )

        self.log_verbose(f"Found {len(items)} QEP updates")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
        )


class WebsiteUpdatesCollector(BaseCollector):
    """Collect QGIS website repository updates."""

    section_name = "website_updates"
    section_title = "Website Updates"

    async def collect(self) -> CollectorResult:
        """Fetch website repository commits and PRs."""
        self.log_verbose("Fetching website updates from GitHub...")

        month_start = self.config.month_start().isoformat()
        month_end = self.config.month_end().isoformat()

        # Get merged PRs
        query = (
            f"repo:{settings.qgis_website_repo} is:pr is:merged "
            f"merged:{month_start}..{month_end}"
        )

        url = f"{settings.github_api_url}/search/issues"
        params = {"q": query, "sort": "updated", "order": "desc", "per_page": 30}

        response = await self.client.get(
            url, params=params, headers=settings.get_github_headers()
        )
        response.raise_for_status()

        data = response.json()
        items: list[NewsItem] = []

        for pr in data.get("items", []):
            merged_at = pr.get("pull_request", {}).get("merged_at")
            if merged_at:
                merged_date = datetime.fromisoformat(merged_at.replace("Z", "+00:00")).date()
            else:
                merged_date = None

            items.append(
                NewsItem(
                    title=pr.get("title", "Untitled"),
                    url=pr.get("html_url"),
                    description=pr.get("body", "")[:200] if pr.get("body") else None,
                    date=merged_date,
                    author=pr.get("user", {}).get("login"),
                    category="Website",
                    metadata={
                        "pr_number": pr.get("number"),
                    },
                )
            )

        self.log_verbose(f"Found {len(items)} website updates")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
        )


class DiscussionsCollector(BaseCollector):
    """Collect GitHub Discussions highlights."""

    section_name = "discussions"
    section_title = "Community Discussions"

    async def collect(self) -> CollectorResult:
        """Fetch discussions using GitHub GraphQL API."""
        self.log_verbose("Fetching discussions from GitHub...")

        if not settings.github_token:
            return CollectorResult(
                section_name=self.section_name,
                section_title=self.section_title,
                error="GitHub token required for discussions (GraphQL API)",
            )

        # GraphQL query for discussions
        query = """
        query($owner: String!, $name: String!, $first: Int!) {
          repository(owner: $owner, name: $name) {
            discussions(first: $first, orderBy: {field: UPDATED_AT, direction: DESC}) {
              nodes {
                title
                url
                createdAt
                updatedAt
                author {
                  login
                }
                category {
                  name
                }
                comments {
                  totalCount
                }
                upvoteCount
              }
            }
          }
        }
        """

        owner, name = settings.qgis_repo.split("/")
        variables = {"owner": owner, "name": name, "first": 50}

        response = await self.client.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers=settings.get_github_headers(),
        )
        response.raise_for_status()

        data = response.json()
        items: list[NewsItem] = []

        if "errors" in data:
            return CollectorResult(
                section_name=self.section_name,
                section_title=self.section_title,
                error=f"GraphQL errors: {data['errors']}",
            )

        discussions = (
            data.get("data", {}).get("repository", {}).get("discussions", {}).get("nodes", [])
        )

        for disc in discussions:
            created_at = disc.get("createdAt")
            if created_at:
                disc_date = datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()

                if self.is_in_month(disc_date):
                    items.append(
                        NewsItem(
                            title=disc.get("title", "Untitled"),
                            url=disc.get("url"),
                            date=disc_date,
                            author=disc.get("author", {}).get("login") if disc.get("author") else None,
                            category=disc.get("category", {}).get("name") if disc.get("category") else None,
                            metadata={
                                "comments": disc.get("comments", {}).get("totalCount", 0),
                                "upvotes": disc.get("upvoteCount", 0),
                            },
                        )
                    )

        self.log_verbose(f"Found {len(items)} discussions")
        return CollectorResult(
            section_name=self.section_name,
            section_title=self.section_title,
            items=items,
        )
