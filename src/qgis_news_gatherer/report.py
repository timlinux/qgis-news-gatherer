"""Report and show notes generation for QGIS news."""

import json
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any

import markdown
from jinja2 import Template
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from qgis_news_gatherer.charts import generate_analytics_charts
from qgis_news_gatherer.collectors.base import CollectorResult, NewsItem


# YouTube description template
YOUTUBE_DESCRIPTION_TEMPLATE = """{{ month_str }} QGIS News Update!

In this video, we cover the latest news and updates from the QGIS project for {{ month_str }}.

⏱️ CHAPTERS
{{ chapters }}

🔗 LINKS MENTIONED
{{ links }}

📚 RESOURCES
• QGIS Website: https://qgis.org
• QGIS Documentation: https://docs.qgis.org
• QGIS GitHub: https://github.com/qgis/QGIS
• QGIS Blog: https://blog.qgis.org
• Download QGIS: https://qgis.org/download

💬 JOIN THE COMMUNITY
• Mailing Lists: https://lists.osgeo.org/mailman/listinfo/qgis-user
• GitHub Discussions: https://github.com/qgis/QGIS/discussions
• Matrix/IRC: #qgis on matrix.org

❤️ SUPPORT QGIS
• Become a Sketcher: https://qgis.org/sketchers
• Donate: https://qgis.org/funding

---
Made with 💗 by Kartoza | https://kartoza.com
Subscribe for more QGIS content!

#QGIS #GIS #OpenSource #Sketching #Sketchers #GeoSpatial
"""

# HTML template for PDF generation (landscape slide-deck)
PDF_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>QGIS Monthly News - {{ month_str }}</title>
    <style>
        @page {
            size: A4 landscape;
            margin: 1.2cm 2cm 1.5cm 2cm;
            @bottom-left {
                content: "QGIS Monthly News - {{ month_str }}";
                font-size: 7pt;
                color: #aaa;
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', sans-serif;
            }
            @bottom-right {
                content: "Made with love by Kartoza";
                font-size: 7pt;
                color: #aaa;
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', sans-serif;
            }
        }

        @page :first {
            margin: 0;
            @bottom-left { content: none; }
            @bottom-right { content: none; }
        }

        @page fullbleed {
            margin: 0;
            @bottom-left { content: none; }
            @bottom-right { content: none; }
        }

        * { box-sizing: border-box; }

        body {
            font-family: BlinkMacSystemFont, -apple-system, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif;
            line-height: 1.5;
            color: #2d2d2d;
            margin: 0;
            padding: 0;
            font-size: 11pt;
        }

        /* --- SLIDE BASE --- */
        .slide {
            page-break-after: always;
            overflow: hidden;
            max-width: 100%;
        }

        .slide:last-child {
            page-break-after: auto;
        }

        /* --- TITLE SLIDE (hero with background image) --- */
        .slide-title {
            background: #0d1117;
            background-image: url("data:image/webp;base64,{{ hero_bg_data }}");
            background-size: cover;
            background-position: center;
            color: white;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 3cm 3.5cm;
            min-height: 21cm;
        }

        .slide-title .header-badge {
            display: inline-block;
            background: rgba(88, 150, 50, 0.25);
            border: 1px solid rgba(88, 150, 50, 0.5);
            color: #93b023;
            font-size: 8pt;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 2pt;
            padding: 5px 14px;
            border-radius: 14px;
            margin-bottom: 16px;
            width: fit-content;
        }

        .slide-title .header-content {
            display: flex;
            align-items: center;
            gap: 30px;
        }

        .slide-title .header-logo {
            width: 120px;
            height: 120px;
            flex-shrink: 0;
        }

        .slide-title h1 {
            margin: 0;
            font-size: 44pt;
            font-weight: 800;
            letter-spacing: -1pt;
            line-height: 1.05;
        }

        .slide-title .subtitle {
            font-size: 24pt;
            font-weight: 300;
            color: #93b023;
            margin-top: 8px;
            letter-spacing: 1pt;
        }

        .slide-title .tagline {
            font-size: 11pt;
            opacity: 0.6;
            margin-top: 16px;
            font-weight: 300;
        }


        /* --- SECTION TITLE SLIDE (dark bg) --- */
        .slide-section-title {
            background: #0d1117;
            background-image: url("data:image/webp;base64,{{ hero_bg_data }}");
            background-size: cover;
            background-position: center;
            color: white;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: flex-start;
            padding: 3cm 3.5cm;
        }

        .slide-section-title h2 {
            font-size: 36pt;
            font-weight: 700;
            color: white;
            border: none;
            margin: 0;
            padding: 0;
        }

        .slide-section-title .section-count {
            font-size: 14pt;
            color: #93b023;
            font-weight: 300;
            margin-top: 8px;
        }


        /* --- CONTENT SLIDES --- */
        .slide-content {
            background: white;
        }

        .slide-content h2 {
            color: #3d7a1c;
            font-size: 20pt;
            font-weight: 700;
            margin: 0 0 6px 0;
            padding-bottom: 6px;
            border-bottom: 3px solid #93b023;
        }

        .slide-content h2 .item-count {
            font-size: 10pt;
            color: #999;
            font-weight: 400;
            margin-left: 8px;
        }

        /* --- STATS DASHBOARD --- */
        .summary-stats {
            display: flex;
            justify-content: center;
            gap: 0;
            margin: 20px 0;
        }

        .stat-item {
            text-align: center;
            padding: 20px 40px;
            flex: 1;
            border-right: 1px solid #dde8cc;
        }

        .stat-item:last-child { border-right: none; }

        .stat-number {
            font-size: 36pt;
            font-weight: 700;
            color: #589632;
            line-height: 1.1;
        }

        .stat-label {
            font-size: 9pt;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1.5pt;
            margin-top: 4px;
        }

        /* --- HIGHLIGHTS BOX --- */
        .highlights {
            background: linear-gradient(135deg, #f0f7e6 0%, #e8f2d8 100%);
            border: 1px solid #c5dea0;
            border-radius: 10px;
            padding: 20px 28px;
            margin: 16px 0;
        }

        .highlights h3 {
            color: #3d7a1c;
            font-size: 12pt;
            margin: 0 0 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1pt;
        }

        .highlights ul {
            margin: 0;
            padding: 0 0 0 20px;
            column-count: 2;
            column-gap: 30px;
        }

        .highlights li {
            margin: 6px 0;
            color: #3a5a20;
            font-size: 10pt;
            break-inside: avoid;
        }

        .highlights li strong {
            color: #2d4a14;
        }

        /* --- VIDEO CHAPTERS --- */
        .chapter-list {
            display: flex;
            flex-wrap: wrap;
            gap: 6px 20px;
            margin: 12px 0;
        }

        .chapter-item {
            display: flex;
            align-items: center;
            font-size: 10pt;
            width: calc(50% - 10px);
        }

        .timestamp {
            font-family: 'Courier New', monospace;
            background: #589632;
            color: white;
            padding: 3px 10px;
            border-radius: 4px;
            margin-right: 12px;
            min-width: 54px;
            text-align: center;
            font-size: 9pt;
            font-weight: 600;
        }

        /* --- NEWS ITEMS --- */
        .news-item {
            background: #fafbf8;
            border-left: 3px solid #93b023;
            padding: 8px 14px;
            margin: 6px 0;
            border-radius: 0 6px 6px 0;
        }

        .news-item:nth-child(odd) {
            background: #f7f9f4;
        }

        .news-item-title {
            font-weight: 600;
            font-size: 10pt;
            color: #2d2d2d;
            line-height: 1.3;
            overflow-wrap: break-word;
            word-break: break-word;
        }

        .news-item-title a {
            color: #3d7a1c;
            text-decoration: underline;
            text-decoration-color: #b5d88c;
            text-underline-offset: 2px;
        }

        .news-item-meta {
            font-size: 8pt;
            color: #999;
            margin-top: 2px;
        }

        .news-item-description {
            margin-top: 4px;
            color: #555;
            font-size: 9pt;
            line-height: 1.4;
            overflow-wrap: break-word;
            word-break: break-word;
        }

        /* --- COMPACT LIST --- */
        .compact-list {
            column-count: 3;
            column-gap: 24px;
            margin: 8px 0;
        }

        .compact-item {
            break-inside: avoid;
            margin: 3px 0;
            padding: 4px 0;
            font-size: 9pt;
            border-bottom: 1px dotted #e0e0e0;
        }

        .compact-item a {
            color: #3d7a1c;
            text-decoration: underline;
            text-decoration-color: #b5d88c;
            text-underline-offset: 2px;
        }

        /* --- QEP ITEMS --- */
        .qep-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 10px 0;
        }

        .qep-card {
            background: #fafbf8;
            border: 1px solid #dde8cc;
            border-radius: 6px;
            padding: 8px 12px;
            width: calc(50% - 4px);
        }

        .qep-card-title {
            font-weight: 600;
            font-size: 9pt;
            color: #3d7a1c;
            line-height: 1.3;
        }

        .qep-card-title a {
            color: #3d7a1c;
            text-decoration: underline;
            text-decoration-color: #b5d88c;
        }

        .qep-card-desc {
            font-size: 8pt;
            color: #777;
            margin-top: 3px;
            line-height: 1.3;
        }

        .qep-status {
            display: inline-block;
            font-size: 7pt;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5pt;
            padding: 1px 6px;
            border-radius: 3px;
            margin-bottom: 3px;
        }

        .qep-status-open { background: #e3f2fd; color: #1565c0; }
        .qep-status-merged { background: #e8f5e9; color: #2e7d32; }

        /* --- MEMBER CARDS --- */
        .member-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 10px 0;
        }

        .member-card {
            display: flex;
            align-items: center;
            gap: 10px;
            background: #fafbf8;
            border: 1px solid #dde8cc;
            border-radius: 6px;
            padding: 10px 14px;
            width: calc(50% - 5px);
        }

        .member-logo {
            width: 48px;
            height: 48px;
            object-fit: contain;
            border-radius: 4px;
            flex-shrink: 0;
        }

        .member-info { flex: 1; min-width: 0; }

        .member-name {
            font-weight: 600;
            font-size: 9pt;
            color: #3d7a1c;
        }

        .member-name a { color: #3d7a1c; text-decoration: underline; text-decoration-color: #b5d88c; }
        .member-meta { font-size: 7.5pt; color: #888; margin-top: 2px; }

        .member-level {
            display: inline-block;
            font-size: 7pt;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5pt;
            padding: 1px 5px;
            border-radius: 3px;
            background: #e8f5e9;
            color: #2e7d32;
        }

        .member-level-flagship { background: #fff3e0; color: #e65100; }
        .member-level-large { background: #e3f2fd; color: #1565c0; }

        /* --- CHARTS --- */
        .charts-container {
            margin: 8px 0;
        }

        .charts-row {
            display: flex;
            gap: 12px;
            margin: 8px 0;
        }

        .chart-wrapper {
            flex: 1;
            text-align: center;
        }

        .chart-wrapper svg {
            width: 100%;
            height: auto;
        }

        .chart-single .chart-wrapper svg {
            width: 100%;
            height: auto;
        }

        /* --- LINKS SECTION --- */
        .links-section {
            column-count: 3;
            column-gap: 20px;
        }

        .links-group-title {
            font-weight: 600;
            font-size: 9pt;
            color: #589632;
            margin: 8px 0 3px;
            break-after: avoid;
        }

        .link-item {
            break-inside: avoid;
            margin: 1px 0;
            font-size: 7.5pt;
            line-height: 1.3;
        }

        .link-item a {
            color: #3d7a1c;
            text-decoration: underline;
            text-decoration-color: #b5d88c;
            overflow-wrap: break-word;
            word-break: break-all;
        }

        .news-item, .compact-item, .qep-card, .member-card, .link-item {
            max-width: 100%;
            overflow: hidden;
        }

        /* --- FOOTER SLIDE --- */
        .slide-end {
            page: fullbleed;
            background: #0d1117;
            background-image: url("data:image/webp;base64,{{ hero_bg_data }}");
            background-size: cover;
            background-position: center;
            color: white;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            min-height: 21cm;
            padding: 3cm;
        }

        .slide-end h2 {
            font-size: 28pt;
            font-weight: 700;
            color: white;
            border: none;
            margin: 0 0 12px;
        }

        .slide-end .footer-links {
            font-size: 12pt;
            margin-top: 20px;
        }

        .slide-end .footer-links a {
            color: #93b023;
            text-decoration: none;
            margin: 0 16px;
        }

        .slide-end .footer-meta {
            font-size: 9pt;
            color: rgba(255,255,255,0.4);
            margin-top: 24px;
        }

        /* --- UTILITIES --- */
        .warning {
            background: #fffbf0;
            border-left: 3px solid #e8c840;
            padding: 6px 12px;
            font-size: 9pt;
            color: #8a6d00;
            margin: 6px 0;
        }

        .section-intro {
            font-size: 10pt;
            color: #777;
            margin: 2px 0 8px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <!-- SLIDE 1: Title -->
    <div class="slide slide-title">
        <div class="header-badge">Free and Open Source GIS</div>
        <div class="header-content">
            {% if logo_data %}
            <img class="header-logo" src="data:image/png;base64,{{ logo_data }}" alt="QGIS Logo">
            {% endif %}
            <div>
                <h1>Spatial without Compromise</h1>
                <div class="subtitle">{{ month_str }}</div>
                <div class="tagline">Spatial visualization and decision-making tools for everyone</div>
            </div>
        </div>
    </div>

    <!-- SLIDE 2: Chapters -->
    <div class="slide slide-content">
        <h2>Chapters</h2>
        <div class="chapter-list">
            <a class="chapter-item" href="#section-highlights" style="text-decoration:none;color:inherit;">
                <span class="timestamp">1</span>
                <span>Highlights</span>
            </a>
            {% for chapter in chapters %}
            <a class="chapter-item" href="#section-{{ chapter.title|lower|replace(' ', '-')|replace('&', '')|replace("'", '') }}" style="text-decoration:none;color:inherit;">
                <span class="timestamp">{{ loop.index + 1 }}</span>
                <span>{{ chapter.title }}</span>
            </a>
            {% endfor %}
        </div>
    </div>

    <!-- SLIDE 3: Highlights -->
    <div class="slide slide-content">
        <h2 id="section-highlights">Highlights</h2>
        <div class="summary-stats">
            <div class="stat-item">
                <div class="stat-number">{{ total_items }}</div>
                <div class="stat-label">News Items</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{{ successful_sections }}</div>
                <div class="stat-label">Sources</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{{ qep_count }}</div>
                <div class="stat-label">Active QEPs</div>
            </div>
        </div>

        {% if highlights %}
        <div class="highlights">
            <h3>This Month's Highlights</h3>
            <ul>
                {% for hl in highlights %}
                <li><strong>{{ hl.title }}</strong> &mdash; {{ hl.summary }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}
    </div>

    <!-- CONTENT SLIDES: one per section -->
    {% for section in sections %}
    {% if section.news_items %}
    <div class="slide slide-content">
        <h2 id="section-{{ section.title|lower|replace(' ', '-')|replace('&', '')|replace("'", '') }}">{{ section.title }} <span class="item-count">({{ section.news_items|length }} items)</span></h2>

        {% for warning in section.warnings %}
        <div class="warning">{{ warning }}</div>
        {% endfor %}

        {% if section.has_charts %}
        <div class="charts-container {% if section.chart_svgs|length == 1 %}chart-single{% endif %}">
            {% for svg in section.chart_svgs %}
            {% if section.chart_svgs|length == 1 %}
            <div class="chart-wrapper">{{ svg }}</div>
            {% else %}
            {% if loop.index is odd %}
            <div class="charts-row">
            {% endif %}
                <div class="chart-wrapper">{{ svg }}</div>
            {% if loop.index is even or loop.last %}
            </div>
            {% endif %}
            {% endif %}
            {% endfor %}
        </div>
        {% elif section.is_member %}
        <div class="member-grid">
            {% for item in section.news_items %}
            <div class="member-card">
                {% if item.logo_url %}
                <img class="member-logo" src="{{ item.logo_url }}" alt="{{ item.title }}">
                {% endif %}
                <div class="member-info">
                    {% if item.level %}
                    <span class="member-level member-level-{{ item.level|lower }}">{{ item.level }}</span>
                    {% endif %}
                    <div class="member-name">
                        {% if item.url %}<a href="{{ item.url }}">{{ item.title }}</a>{% else %}{{ item.title }}{% endif %}
                    </div>
                    {% if item.description %}
                    <div class="member-meta">{{ item.description }}</div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        {% elif section.is_qep %}
        <div class="qep-grid">
            {% for item in section.news_items %}
            <div class="qep-card">
                {% if 'Merged' in item.title %}
                <span class="qep-status qep-status-merged">Merged</span>
                {% elif 'Open' in item.title %}
                <span class="qep-status qep-status-open">Open</span>
                {% endif %}
                <div class="qep-card-title">
                    {% if item.url %}<a href="{{ item.url }}">{{ item.title }}</a>{% else %}{{ item.title }}{% endif %}
                </div>
                {% if item.description %}
                <div class="qep-card-desc">{{ item.description[:120] }}{% if item.description|length > 120 %}&hellip;{% endif %}</div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% elif section.is_compact %}
        <div class="compact-list">
            {% for item in section.news_items %}
            <div class="compact-item">
                {% if item.url %}<a href="{{ item.url }}">{{ item.title }}</a>{% else %}{{ item.title }}{% endif %}
            </div>
            {% endfor %}
        </div>
        {% else %}
            {% for item in section.news_items %}
            <div class="news-item">
                <div class="news-item-title">
                    {% if item.url %}<a href="{{ item.url }}">{{ item.title }}</a>{% else %}{{ item.title }}{% endif %}
                </div>
                {% if item.date or item.author %}
                <div class="news-item-meta">
                    {% if item.date %}{{ item.date }}{% endif %}
                    {% if item.author %} by {{ item.author }}{% endif %}
                </div>
                {% endif %}
                {% if item.description %}
                <div class="news-item-description">{{ item.description }}</div>
                {% endif %}
            </div>
            {% endfor %}
        {% endif %}

    </div>
    {% endif %}
    {% endfor %}

    <!-- LINKS SLIDE -->
    <div class="slide slide-content">
        <h2>All Links</h2>
        <p class="section-intro">All resources mentioned in this month's news update.</p>
        <div class="links-section">
            {% for group in link_groups %}
            <div class="links-group-title">{{ group.title }}</div>
            {% for link in group.links %}
            <div class="link-item">
                &bull; <a href="{{ link.url }}">{{ link.title }}</a>
            </div>
            {% endfor %}
            {% endfor %}
        </div>
    </div>

    <!-- END SLIDE -->
    <div class="slide slide-end">
        {% if logo_data %}
        <img style="width:100px;height:100px;margin-bottom:20px;" src="data:image/png;base64,{{ logo_data }}" alt="QGIS Logo">
        {% endif %}
        <h2>Thank You!</h2>
        <p style="font-size:13pt;opacity:0.7;margin:0;">See you next month for more QGIS news</p>
        <div class="footer-links">
            <a href="https://qgis.org">qgis.org</a>
            <a href="https://blog.qgis.org">blog.qgis.org</a>
            <a href="https://github.com/qgis/QGIS">GitHub</a>
            <a href="https://qgis.org/download">Download</a>
        </div>
        <div class="footer-meta">
            Made with &#10084;&#65039; by <a href="https://kartoza.com" style="color:#93b023;">Kartoza</a>
            &nbsp;|&nbsp; <a href="https://github.com/sponsors/kartoza" style="color:#93b023;">Donate!</a>
            &nbsp;|&nbsp; Generated {{ generated_date }} &bull; v{{ version }}
        </div>
    </div>
</body>
</html>
"""


class ShowNotesGenerator:
    """Generate YouTube show notes and PDF reports."""

    def __init__(
        self,
        target_month: date,
        console: Console | None = None,
    ):
        self.target_month = target_month
        self.console = console or Console()
        self.results: list[CollectorResult] = []

    def add_result(self, result: CollectorResult) -> None:
        """Add a collector result to the report."""
        self.results.append(result)

    def _calculate_chapters(self) -> list[dict[str, Any]]:
        """Build the list of chapters from sections with content."""
        chapters = []

        for result in self.results:
            if result.success and result.has_items:
                chapters.append(
                    {
                        "title": result.section_title,
                        "item_count": len(result.items),
                    }
                )

        return chapters

    def _collect_all_links(self) -> list[dict[str, str]]:
        """Collect all links from all items."""
        links = []
        seen_urls = set()

        for result in self.results:
            for item in result.items:
                if item.url and item.url not in seen_urls:
                    links.append({"title": item.title[:80], "url": item.url})
                    seen_urls.add(item.url)

        return links

    def generate_youtube_description(self) -> str:
        """Generate YouTube video description with chapters and links."""
        month_str = self.target_month.strftime("%B %Y")
        chapters = self._calculate_chapters()
        links = self._collect_all_links()

        # Format chapters
        chapter_lines = []
        for ch in chapters:
            chapter_lines.append(f"{ch['timestamp']} {ch['title']}")
        chapters_text = "\n".join(chapter_lines)

        # Format links (limit to top items per section)
        link_lines = []
        for result in self.results:
            if result.success and result.has_items:
                link_lines.append(f"\n{result.section_title}:")
                for item in result.items[:5]:
                    if item.url:
                        link_lines.append(f"• {item.title[:60]}: {item.url}")

        links_text = "\n".join(link_lines)

        template = Template(YOUTUBE_DESCRIPTION_TEMPLATE)
        return template.render(
            month_str=month_str,
            chapters=chapters_text,
            links=links_text,
        )

    def generate_markdown_shownotes(self) -> str:
        """Generate detailed markdown show notes."""
        output = StringIO()
        month_str = self.target_month.strftime("%B %Y")
        chapters = self._calculate_chapters()
        total_items = sum(len(r.items) for r in self.results)

        output.write(f"# QGIS Monthly News Show Notes - {month_str}\n\n")
        output.write(f"*Generated: {date.today().isoformat()}*\n\n")

        # Summary
        successful = sum(1 for r in self.results if r.success)

        output.write("## Summary\n\n")
        output.write(f"- **Total Items:** {total_items}\n")
        output.write(f"- **Sources:** {successful}/{len(self.results)}\n\n")

        output.write("---\n\n")

        # Chapters
        output.write("## Video Chapters\n\n")
        output.write("Copy these timestamps to your YouTube description:\n\n")
        output.write("```\n")
        for ch in chapters:
            output.write(f"{ch['timestamp']} {ch['title']}\n")
        output.write("```\n\n")

        output.write("---\n\n")

        # Detailed sections
        for result in self.results:
            output.write(f"## {result.section_title}\n\n")

            if result.error:
                output.write(f"> **Error:** {result.error}\n\n")
                continue

            for warning in result.warnings:
                output.write(f"> **Note:** {warning}\n\n")

            if not result.has_items:
                output.write("*No items found for this month.*\n\n")
                continue

            # Talking points
            output.write("### Talking Points\n\n")
            for i, item in enumerate(result.items[:10], 1):
                output.write(f"{i}. **{item.title}**\n")
                if item.description:
                    desc = item.description.replace("\n", " ")[:200]
                    output.write(f"   - {desc}\n")
                if item.url:
                    output.write(f"   - Link: {item.url}\n")
                output.write("\n")

            if len(result.items) > 10:
                output.write(f"*...and {len(result.items) - 10} more items*\n\n")

        output.write("---\n\n")

        # All links section
        output.write("## All Links\n\n")
        for result in self.results:
            if result.success and result.has_items:
                output.write(f"### {result.section_title}\n\n")
                for item in result.items:
                    if item.url:
                        output.write(f"- [{item.title[:60]}]({item.url})\n")
                output.write("\n")

        output.write("---\n\n")

        # YouTube description ready to copy
        output.write("## YouTube Description (Ready to Copy)\n\n")
        output.write("```\n")
        output.write(self.generate_youtube_description())
        output.write("```\n\n")

        # Footer
        output.write("---\n\n")
        output.write(
            "Made with :heart: by [Kartoza](https://kartoza.com) | "
            "[Donate!](https://github.com/sponsors/kartoza) | "
            "[GitHub](https://github.com/kartoza/qgis-news-gatherer)\n"
        )

        return output.getvalue()

    @staticmethod
    def _load_asset(filenames: list[str]) -> str | None:
        """Load a file as a base64-encoded string, searching common locations."""
        import base64

        project_root = Path(__file__).parent.parent.parent.parent

        for filename in filenames:
            search_paths = [
                Path(filename),
                project_root / filename,
            ]
            for path in search_paths:
                if path.exists():
                    with open(path, "rb") as f:
                        return base64.b64encode(f.read()).decode()
        return None

    @classmethod
    def _load_logo(cls) -> str | None:
        """Load the QGIS logo as a base64-encoded string."""
        return cls._load_asset([
            "qgis-icon-650x650-bordered.png",
            "qgis-logo.png",
        ])

    @classmethod
    def _load_hero_bg(cls) -> str | None:
        """Load the hero background image as a base64-encoded string."""
        return cls._load_asset(["hegobg1.webp"])

    @staticmethod
    def _strip_html(text: str) -> str:
        """Strip HTML tags, entities, and markdown artifacts from text."""
        import re

        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"&#?\w+;", "", text)
        # Also strip partial entities at end of truncated text
        text = re.sub(r"&#?\w*$", "", text)
        # Strip markdown headers and bold markers
        text = re.sub(r"^#{1,4}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"\*\*", "", text)
        # Strip markdown links but keep text: [text](url) -> text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _build_highlights(self) -> list[dict[str, str]]:
        """Extract top highlights from results for the summary box."""
        highlights = []

        # Releases are always a highlight
        for result in self.results:
            if result.section_name == "releases" and result.has_items:
                versions = [item.title for item in result.items[:3]]
                highlights.append(
                    {
                        "title": "New Releases",
                        "summary": f"QGIS {', '.join(versions)} released this month",
                    }
                )
                break

        # Blog posts (first 2 most important)
        for result in self.results:
            if result.section_name == "blog_posts" and result.has_items:
                for item in result.items[:2]:
                    clean = self._strip_html(item.title)
                    highlights.append(
                        {
                            "title": clean,
                            "summary": self._strip_html(
                                item.description[:100] + "..."
                            )
                            if item.description
                            else "Read more on the QGIS blog",
                        }
                    )
                break

        # QEP count
        qep_count = 0
        for result in self.results:
            if result.section_name == "qeps" and result.has_items:
                qep_count = sum(
                    1 for i in result.items if "Open" in i.title
                )
                if qep_count > 0:
                    highlights.append(
                        {
                            "title": f"{qep_count} Active QEPs",
                            "summary": "Enhancement proposals shaping the future of QGIS",
                        }
                    )
                break

        # Notable fixes count
        for result in self.results:
            if result.section_name == "notable_fixes" and result.has_items:
                highlights.append(
                    {
                        "title": f"{len(result.items)} Bug Fixes",
                        "summary": "Important fixes merged this month via the bug fix programme",
                    }
                )
                break

        # Key merged PRs count
        for result in self.results:
            if result.section_name == "merged_prs" and result.has_items:
                highlights.append(
                    {
                        "title": f"{len(result.items)} Key PRs Merged",
                        "summary": "Feature and improvement pull requests merged this month",
                    }
                )
                break

        # User groups
        for result in self.results:
            if result.section_name == "user_groups" and result.has_items:
                # Find the summary item
                for item in result.items:
                    if item.category == "summary":
                        total = item.metadata.get("total_active", 0)
                        countries = item.metadata.get("total_countries", 0)
                        highlights.append(
                            {
                                "title": f"{total} User Groups",
                                "summary": f"Active across {countries} countries worldwide",
                            }
                        )
                        break
                # Check for new groups
                new_groups = [i for i in result.items if i.category == "new_group"]
                if new_groups:
                    names = ", ".join(i.title.replace("New user group: ", "") for i in new_groups)
                    highlights.append(
                        {
                            "title": f"{len(new_groups)} New User Group(s)",
                            "summary": names,
                        }
                    )
                break

        # Analytics headline
        for result in self.results:
            if result.section_name == "analytics" and result.has_items:
                for item in result.items:
                    if item.metadata.get("metric") == "total_opens_30d":
                        val = item.metadata.get("value", 0)
                        highlights.append(
                            {
                                "title": f"{val:,} Opens (30 days)",
                                "summary": "QGIS application opens tracked via the news feed",
                            }
                        )
                        break
                break

        # Plugin ecosystem
        for result in self.results:
            if result.section_name == "plugin_stats" and result.has_items:
                for item in result.items:
                    if item.metadata.get("metric") == "total_plugins":
                        val = item.metadata.get("value", 0)
                        highlights.append(
                            {
                                "title": f"{val:,} Plugins",
                                "summary": "Total plugins in the QGIS ecosystem",
                            }
                        )
                        break
                break

        # New sustaining members
        for result in self.results:
            if result.section_name == "sustaining_members" and result.has_items:
                new_members = [i for i in result.items if i.category == "new_member"]
                if new_members:
                    names = ", ".join(
                        i.title.replace("New Flagship member: ", "")
                        .replace("New Large member: ", "")
                        .replace("New Medium member: ", "")
                        .replace("New Small member: ", "")
                        for i in new_members[:3]
                    )
                    highlights.append(
                        {
                            "title": f"{len(new_members)} New Sustaining Member(s)",
                            "summary": names,
                        }
                    )
                break

        # Website updates count
        for result in self.results:
            if result.section_name == "website_updates" and result.has_items:
                highlights.append(
                    {
                        "title": f"{len(result.items)} Website Updates",
                        "summary": "Improvements to qgis.org",
                    }
                )
                break

        return highlights[:5]

    def generate_html(self) -> str:
        """Generate HTML for PDF conversion."""
        from qgis_news_gatherer import __version__

        month_str = self.target_month.strftime("%B %Y")
        chapters = self._calculate_chapters()

        total_items = sum(len(r.items) for r in self.results)
        successful = sum(1 for r in self.results if r.success)

        # Compact sections that should use the compact list layout
        compact_sections = {"mailing_lists", "website_updates"}
        qep_sections = {"qeps"}
        member_sections = {"sustaining_members"}
        chart_sections = {"analytics", "plugin_stats", "sustaining_members"}

        # Max items per section (top 5 for condensed report)
        section_limits = {
            "releases": 5,
            "notable_fixes": 5,
            "merged_prs": 5,
            "blog_posts": 5,
            "qeps": 10,
            "website_updates": 10,
            "mailing_lists": 5,
            "conferences": 5,
            "user_groups": 5,
            "analytics": 10,
            "plugin_stats": 10,
        }
        default_limit = 5

        # Count active QEPs
        qep_count = 0
        for result in self.results:
            if result.section_name == "qeps" and result.has_items:
                qep_count = sum(1 for i in result.items if "Open" in i.title)

        target_year = self.target_month.year

        sections = []
        for result in self.results:
            # Skip sections with no items (hides errors/empty sections)
            if not result.has_items:
                continue

            limit = section_limits.get(result.section_name, default_limit)

            # Filter out past conferences/events
            filtered_items = result.items
            if result.section_name == "conferences":
                filtered_items = [
                    item for item in result.items
                    if not item.date or item.date.year >= target_year
                ]
                # Also filter by title - remove references to past years
                filtered_items = [
                    item for item in filtered_items
                    if not any(
                        str(y) in (item.title or "")
                        for y in range(2020, target_year)
                    )
                ]

            if not filtered_items:
                continue

            is_member = result.section_name in member_sections

            items = []
            for item in filtered_items[:limit]:
                desc = self._strip_html(item.description[:300]) if item.description else None
                item_dict: dict = {
                    "title": self._strip_html(item.title),
                    "url": item.url,
                    "date": item.date.isoformat() if item.date else None,
                    "author": item.author,
                    "description": desc,
                }
                # Add member-specific fields
                if is_member:
                    logo = item.metadata.get("logo_url", "")
                    item_dict["logo_url"] = logo
                    item_dict["level"] = item.metadata.get("level", "")

                items.append(item_dict)

            # Generate per-section charts for analytics/plugin_stats/members
            section_chart_svgs = []
            if result.section_name in chart_sections:
                section_chart_svgs = [
                    c["svg"] for c in generate_analytics_charts([result])
                ]

            sections.append(
                {
                    "title": result.section_title,
                    "error": None,
                    "warnings": list(result.warnings) if result.warnings else [],
                    "news_items": items,
                    "is_qep": result.section_name in qep_sections,
                    "is_compact": result.section_name in compact_sections,
                    "is_member": is_member,
                    "has_charts": len(section_chart_svgs) > 0,
                    "chart_svgs": section_chart_svgs,
                }
            )

        # Build grouped links
        link_groups = []
        for result in self.results:
            if result.success and result.has_items:
                links = []
                for item in result.items:
                    if item.url:
                        links.append(
                            {"title": self._strip_html(item.title[:60]), "url": item.url}
                        )
                if links:
                    link_groups.append(
                        {"title": result.section_title, "links": links}
                    )

        highlights = self._build_highlights()

        # Generate charts from analytics and plugin stats data
        charts = generate_analytics_charts(self.results)

        # Pair charts for 2-per-slide layout
        chart_pairs = []
        for i in range(0, len(charts), 2):
            chart_pairs.append(charts[i:i + 2])

        # Load assets
        logo_data = self._load_logo()
        hero_bg_data = self._load_hero_bg() or ""

        template = Template(PDF_HTML_TEMPLATE)
        return template.render(
            month_str=month_str,
            chapters=chapters,
            sections=sections,
            link_groups=link_groups,
            highlights=highlights,
            charts=charts,
            chart_pairs=chart_pairs,
            total_items=total_items,
            successful_sections=successful,
            qep_count=qep_count,
            generated_date=date.today().isoformat(),
            version=__version__,
            logo_data=logo_data,
            hero_bg_data=hero_bg_data,
        )

    def generate_pdf(self, output_path: Path) -> None:
        """Generate PDF show notes."""
        try:
            from weasyprint import HTML
        except ImportError:
            self.console.print(
                "[red]WeasyPrint not installed. Install with: pip install weasyprint[/red]"
            )
            return

        html_content = self.generate_html()
        HTML(string=html_content).write_pdf(output_path)
        self.console.print(f"[green]PDF saved to {output_path}[/green]")

    def generate_json(self) -> str:
        """Generate JSON report with all data."""
        chapters = self._calculate_chapters()
        all_links = self._collect_all_links()

        data: dict[str, Any] = {
            "generated_at": date.today().isoformat(),
            "target_month": self.target_month.isoformat(),
            "chapters": chapters,
            "sections": [result.to_dict() for result in self.results],
            "all_links": all_links,
            "summary": {
                "total_sections": len(self.results),
                "successful_sections": sum(1 for r in self.results if r.success),
                "total_items": sum(len(r.items) for r in self.results),
            },
            "youtube_description": self.generate_youtube_description(),
        }
        return json.dumps(data, indent=2, default=str)

    def print_terminal(self) -> None:
        """Print the show notes to the terminal using Rich."""
        month_str = self.target_month.strftime("%B %Y")
        chapters = self._calculate_chapters()

        self.console.print()
        self.console.print(
            Panel(
                f"[bold blue]QGIS Monthly News Show Notes - {month_str}[/bold blue]",
                border_style="blue",
            )
        )
        self.console.print()

        # Summary table
        summary_table = Table(title="Collection Summary", show_header=True)
        summary_table.add_column("Section", style="cyan")
        summary_table.add_column("Status", justify="center")
        summary_table.add_column("Items", justify="right")

        for result in self.results:
            if result.success:
                status = "[green]✓[/green]"
            else:
                status = "[red]✗[/red]"
            summary_table.add_row(
                result.section_title,
                status,
                str(len(result.items)),
            )

        self.console.print(summary_table)
        self.console.print()

        # Chapters
        self.console.print("[bold cyan]Chapters[/bold cyan]")
        self.console.print("-" * 40)
        for i, ch in enumerate(chapters, 1):
            self.console.print(f"[yellow]{i}[/yellow] {ch['title']}")
        self.console.print()

        # Detailed sections
        for result in self.results:
            self._print_section_terminal(result)

        # Footer
        self.console.print()
        self.console.print(
            "[dim]Made with ❤️ by Kartoza | "
            "https://kartoza.com | "
            "https://github.com/kartoza/qgis-news-gatherer[/dim]"
        )

    def _print_section_terminal(self, result: CollectorResult) -> None:
        """Print a single section to the terminal."""
        self.console.print(f"\n[bold cyan]{result.section_title}[/bold cyan]")
        self.console.print("-" * 40)

        if result.error:
            self.console.print(f"[red]Error: {result.error}[/red]")
            return

        for warning in result.warnings:
            self.console.print(f"[yellow]Note: {warning}[/yellow]")

        if not result.has_items:
            self.console.print("[dim]No items found for this month.[/dim]")
            return

        for i, item in enumerate(result.items[:10], 1):
            if item.url:
                self.console.print(f"{i}. [link={item.url}]{item.title}[/link]")
            else:
                self.console.print(f"{i}. {item.title}")

            meta_parts = []
            if item.date:
                meta_parts.append(f"[dim]{item.date}[/dim]")
            if item.author:
                meta_parts.append(f"[dim]by {item.author}[/dim]")

            if meta_parts:
                self.console.print(f"   {' | '.join(meta_parts)}")

        if len(result.items) > 10:
            self.console.print(f"   [dim]... and {len(result.items) - 10} more[/dim]")

    def save(self, path: Path, format: str = "markdown") -> None:
        """Save the report to a file."""
        if format == "json":
            content = self.generate_json()
            path.write_text(content)
        elif format == "pdf":
            self.generate_pdf(path)
            return
        elif format == "youtube":
            content = self.generate_youtube_description()
            path.write_text(content)
        elif format == "html":
            content = self.generate_html()
            path.write_text(content)
        else:
            content = self.generate_markdown_shownotes()
            path.write_text(content)

        self.console.print(f"[green]Report saved to {path}[/green]")

    def preview_markdown(self) -> None:
        """Preview the markdown report in the terminal."""
        md_content = self.generate_markdown_shownotes()
        self.console.print(Markdown(md_content))


# Backwards compatibility alias
ReportGenerator = ShowNotesGenerator
