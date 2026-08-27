# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Command-line interface for QGIS News Gatherer."""

import asyncio
from datetime import date, datetime
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from qgis_news_gatherer import __version__
from qgis_news_gatherer.collectors.base import BaseCollector
from qgis_news_gatherer.collectors.changelog import ChangelogCollector
from qgis_news_gatherer.collectors.conferences import ConferencesCollector
from qgis_news_gatherer.collectors.discourse import DiscourseCollector
from qgis_news_gatherer.collectors.feeds import BlogFeedCollector, NewsFeedCollector
from qgis_news_gatherer.collectors.github import (
    DiscussionsCollector,
    MergedPRsCollector,
    NotableFixesCollector,
    QEPsCollector,
    ReleasesCollector,
    WebsiteUpdatesCollector,
)
from qgis_news_gatherer.collectors.analytics import AnalyticsCollector, PluginStatsCollector
from qgis_news_gatherer.collectors.mailing_lists import (
    DeveloperMailingListsCollector,
    MailingListsCollector,
)
from qgis_news_gatherer.collectors.members import SustainingMembersCollector
from qgis_news_gatherer.collectors.psc import PSCMinutesCollector
from qgis_news_gatherer.collectors.social import MastodonCollector, PlanetCollector
from qgis_news_gatherer.collectors.transifex import TranslationsCollector
from qgis_news_gatherer.collectors.youtube import (
    YouTubeShortsCollector,
    YouTubeVideosCollector,
)
from qgis_news_gatherer.collectors.user_groups import UserGroupsCollector
from qgis_news_gatherer.config import ReportConfig
from qgis_news_gatherer.report import ShowNotesGenerator

console = Console()

# Map section names to collector classes
COLLECTORS: dict[str, type[BaseCollector]] = {
    "releases": ReleasesCollector,
    "notable_fixes": NotableFixesCollector,
    "merged_prs": MergedPRsCollector,
    "blog_posts": BlogFeedCollector,
    "news_feed": NewsFeedCollector,
    "qeps": QEPsCollector,
    "website_updates": WebsiteUpdatesCollector,
    "discussions": DiscussionsCollector,
    "conferences": ConferencesCollector,
    "mailing_lists_user": MailingListsCollector,
    "mailing_lists_developer": DeveloperMailingListsCollector,
    "translations": TranslationsCollector,
    "user_groups": UserGroupsCollector,
    "sustaining_members": SustainingMembersCollector,
    "analytics": AnalyticsCollector,
    "plugin_stats": PluginStatsCollector,
    "changelog": ChangelogCollector,
    "youtube": YouTubeVideosCollector,
    "youtube_shorts": YouTubeShortsCollector,
    "mastodon": MastodonCollector,
    "planet": PlanetCollector,
    "psc_minutes": PSCMinutesCollector,
    "discourse": DiscourseCollector,
}


def parse_month(value: str) -> date:
    """Parse a month string (YYYY-MM) into a date."""
    try:
        return datetime.strptime(value, "%Y-%m").date()
    except ValueError:
        raise click.BadParameter(f"Invalid month format: {value}. Use YYYY-MM (e.g., 2026-03)")


@click.command()
@click.option(
    "--month",
    "-m",
    "month_str",
    default=None,
    help="Target month in YYYY-MM format (default: current month)",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path (default: stdout)",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["terminal", "markdown", "json", "pdf", "youtube", "html"]),
    default="terminal",
    help="Output format (default: terminal)",
)
@click.option(
    "--sections",
    "-s",
    default=None,
    help="Comma-separated list of sections to include (default: all)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--list-sections",
    is_flag=True,
    help="List available sections and exit",
)
@click.option(
    "--show-chapters",
    is_flag=True,
    help="Show video chapters only",
)
@click.option(
    "--show-youtube-desc",
    is_flag=True,
    help="Show YouTube description only",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force fresh data fetch, bypassing cache",
)
@click.version_option(version=__version__)
def main(
    month_str: str | None,
    output_path: Path | None,
    output_format: str,
    sections: str | None,
    verbose: bool,
    list_sections: bool,
    show_chapters: bool,
    show_youtube_desc: bool,
    force: bool,
) -> None:
    """QGIS Monthly News Gatherer - Generate YouTube Show Notes.

    Automatically collects content for QGIS monthly YouTube news segments
    from various QGIS project sources and generates show notes with
    timestamps, chapters, and links.

    \b
    Output Formats:
        terminal  - Interactive display in terminal (default)
        markdown  - Full show notes with talking points
        json      - Structured data for processing
        pdf       - Beautiful PDF for sharing
        youtube   - YouTube description ready to paste
        html      - HTML version (can be printed to PDF)

    \b
    Examples:
        qgis-news-gatherer                           # Current month, terminal
        qgis-news-gatherer -m 2026-03                # Specific month
        qgis-news-gatherer -o shownotes.md -f markdown   # Markdown file
        qgis-news-gatherer -o shownotes.pdf -f pdf   # PDF show notes
        qgis-news-gatherer --show-youtube-desc       # Just YouTube description
        qgis-news-gatherer -s releases,news_feed     # Specific sections only
    """
    if list_sections:
        console.print("[bold]Available sections:[/bold]\n")
        for name, collector_cls in COLLECTORS.items():
            console.print(f"  [cyan]{name}[/cyan]: {collector_cls.section_title}")
        return

    # Parse target month
    if month_str:
        target_month = parse_month(month_str)
    else:
        target_month = date.today().replace(day=1)

    # Parse sections
    section_list: list[str] | None = None
    if sections:
        section_list = [s.strip() for s in sections.split(",")]
        invalid = [s for s in section_list if s not in COLLECTORS]
        if invalid:
            raise click.BadParameter(
                f"Invalid section(s): {', '.join(invalid)}. "
                f"Use --list-sections to see available sections."
            )

    # Create configuration
    config = ReportConfig(
        target_month=target_month,
        sections=section_list,
        verbose=verbose,
    )

    month_display = target_month.strftime("%B %Y")
    console.print(f"\n[bold blue]QGIS News Gatherer[/bold blue] - {month_display}\n")

    if verbose:
        console.print(f"[dim]Target month: {target_month}[/dim]")
        console.print(f"[dim]Sections: {config.sections}[/dim]")
        console.print()

    # Run collection
    asyncio.run(
        run_collection(
            config,
            output_path,
            output_format,
            show_chapters,
            show_youtube_desc,
            force,
        )
    )


async def run_collection(
    config: ReportConfig,
    output_path: Path | None,
    output_format: str,
    show_chapters: bool,
    show_youtube_desc: bool,
    force: bool = False,
) -> None:
    """Run the async collection process."""
    report = ShowNotesGenerator(config.target_month, console)

    # Determine which collectors to use
    collector_names = config.sections or list(COLLECTORS.keys())

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        # Create all collectors
        collectors: list[BaseCollector] = []
        for name in collector_names:
            if name in COLLECTORS:
                collector = COLLECTORS[name](config, console)
                collectors.append(collector)

        # Run all collectors concurrently
        task = progress.add_task("Collecting news...", total=len(collectors))

        async def collect_with_progress(collector: BaseCollector) -> None:
            result = await collector.safe_collect(force=force)
            report.add_result(result)
            await collector.close()
            progress.advance(task)

        await asyncio.gather(*[collect_with_progress(c) for c in collectors])

    # Handle special display modes
    if show_chapters:
        chapters = report._calculate_chapters()
        console.print("\n[bold cyan]Video Chapters[/bold cyan]")
        console.print("-" * 40)
        for ch in chapters:
            console.print(f"[yellow]{ch['timestamp']}[/yellow] {ch['title']}")
        console.print()
        return

    if show_youtube_desc:
        console.print("\n[bold cyan]YouTube Description[/bold cyan]")
        console.print("-" * 40)
        console.print(report.generate_youtube_description())
        return

    # Generate output
    if output_format == "terminal":
        report.print_terminal()
    elif output_format == "markdown":
        if output_path:
            report.save(output_path, format="markdown")
        else:
            console.print(report.generate_markdown_shownotes())
    elif output_format == "json":
        if output_path:
            report.save(output_path, format="json")
        else:
            console.print(report.generate_json())
    elif output_format == "pdf":
        if output_path:
            report.save(output_path, format="pdf")
        else:
            # Default filename for PDF
            default_name = f"qgis-news-{config.target_month.strftime('%Y-%m')}.pdf"
            report.save(Path(default_name), format="pdf")
    elif output_format == "youtube":
        if output_path:
            report.save(output_path, format="youtube")
        else:
            console.print(report.generate_youtube_description())
    elif output_format == "html":
        if output_path:
            report.save(output_path, format="html")
        else:
            console.print(report.generate_html())

    # Summary
    successful = sum(1 for r in report.results if r.success)
    total_items = sum(len(r.items) for r in report.results)

    console.print()
    console.print(
        f"[green]Collected {total_items} items from "
        f"{successful}/{len(report.results)} sources[/green]"
    )

    if output_path:
        console.print(f"[green]Output saved to: {output_path}[/green]")


if __name__ == "__main__":
    main()
