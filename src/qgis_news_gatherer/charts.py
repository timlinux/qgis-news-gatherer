# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""SVG chart generation for PDF reports.

Generates inline SVG charts compatible with WeasyPrint (no JavaScript).
Uses QGIS branding colors.
"""

import calendar
import json
from datetime import date
from importlib import resources
from typing import Any

# QGIS brand palette
COLORS = {
    "primary": "#589632",
    "primary_dark": "#3d7a1c",
    "primary_light": "#7db842",
    "accent": "#93b023",
    "gold": "#e8c840",
    "text": "#2d2d2d",
    "text_light": "#666666",
    "text_muted": "#999999",
    "bg": "#fafbf8",
    "bg_alt": "#f0f7e6",
    "border": "#dde8cc",
    "grid": "#e8e8e8",
    # Extra hues used only by the year-at-a-glance timeline. Sampled from
    # https://qgis.org/resources/roadmap/ so the slide matches the site's
    # own roadmap styling: light card background, a muted pending-grey for
    # the stepper line, a saturated "current" green for the today ribbon,
    # plus two categories (funding, governance) the roadmap has no analog
    # for, chosen to stay legible against that palette.
    "timeline_card_bg": "#f4f7f9",
    "timeline_pending": "#dbe5eb",
    "timeline_ribbon": "#3a9800",
    "timeline_funding": "#3f7cac",
    "timeline_governance": "#b5651d",
}

BAR_PALETTE = [
    "#589632", "#7db842", "#93b023", "#3d7a1c", "#a8c94e",
    "#4a8528", "#6aaa38", "#b5d060", "#2d6a10", "#c2dc78",
]


def _fmt_number(n: int | float) -> str:
    """Format a number with K/M suffixes for compact display."""
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if abs(n) >= 10_000:
        return f"{n / 1_000:.0f}K"
    if abs(n) >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:,.0f}"


#: Public alias - the report reuses this for its stat tiles.
fmt_number = _fmt_number


def _escape(text: str) -> str:
    """Escape text for SVG/XML."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _shorten_label(label: str, max_chars: int = 24) -> str:
    """Shorten a label intelligently for chart display."""
    if len(label) <= max_chars:
        return label
    # For Windows platform strings, extract the distinguishing part
    if label.startswith("Windows "):
        # "Windows 11 Version 2009" -> "Win 11 v2009"
        parts = label.replace("Windows ", "Win ").replace("Version ", "v")
        if len(parts) <= max_chars:
            return parts
    # For Debian/macOS etc, keep as-is if short enough
    return label[:max_chars - 1] + "\u2026"


def horizontal_bar_chart(
    data: list[tuple[str, int | float]],
    title: str = "",
    width: int = 520,
    bar_height: int = 28,
    max_label_width: int = 160,
    show_values: bool = True,
    value_suffix: str = "",
    color: str | None = None,
    multi_color: bool = True,
) -> str:
    """Generate a horizontal bar chart as an SVG string.

    Args:
        data: List of (label, value) tuples, ordered by display preference.
        title: Chart title.
        width: Total SVG width.
        bar_height: Height of each bar.
        max_label_width: Max width reserved for labels.
        show_values: Whether to annotate bars with values.
        value_suffix: Suffix for value annotations (e.g. " votes").
        color: Single color for all bars (overrides multi_color).
        multi_color: Use multiple colors from the palette.
    """
    if not data:
        return ""

    # Calculate max value label width to ensure nothing gets clipped
    max_val_str = max(
        (len(_fmt_number(v) + value_suffix) for _, v in data),
        default=0,
    )
    value_label_space = max(80, max_val_str * 8 + 16)

    padding_top = 36 if title else 8
    padding_bottom = 12
    bar_gap = 6
    chart_left = max_label_width + 10
    chart_width = width - chart_left - value_label_space

    total_height = padding_top + len(data) * (bar_height + bar_gap) + padding_bottom
    max_val = max(v for _, v in data) if data else 1
    if max_val == 0:
        max_val = 1

    # Max chars for labels based on label width (approx 6px per char at 9pt)
    max_label_chars = max(8, max_label_width // 6)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {total_height}" '
        f'style="font-family: \'Segoe UI\', Tahoma, sans-serif; background: {COLORS["bg"]}; '
        f'border: 1px solid {COLORS["border"]}; border-radius: 6px; margin: 8px 0;">',
    ]

    if title:
        lines.append(
            f'<text x="{width // 2}" y="22" text-anchor="middle" '
            f'font-size="11" font-weight="600" fill="{COLORS["primary_dark"]}">'
            f'{_escape(title)}</text>'
        )

    for i, (label, value) in enumerate(data):
        y = padding_top + i * (bar_height + bar_gap)
        bar_w = (value / max_val) * chart_width if max_val else 0
        bar_color = color or (BAR_PALETTE[i % len(BAR_PALETTE)] if multi_color else COLORS["primary"])

        display_label = _shorten_label(label, max_label_chars)

        # Label
        lines.append(
            f'<text x="{max_label_width}" y="{y + bar_height * 0.65}" '
            f'text-anchor="end" font-size="9" fill="{COLORS["text_light"]}">'
            f'{_escape(display_label)}</text>'
        )

        # Bar with rounded right end
        if bar_w > 0:
            radius = min(4, bar_w / 2)
            lines.append(
                f'<rect x="{chart_left}" y="{y + 2}" width="{bar_w:.1f}" height="{bar_height - 4}" '
                f'rx="{radius}" fill="{bar_color}" opacity="0.85"/>'
            )

        # Value annotation
        if show_values:
            val_str = _fmt_number(value) + value_suffix
            val_x = chart_left + bar_w + 6
            lines.append(
                f'<text x="{val_x:.1f}" y="{y + bar_height * 0.65}" '
                f'font-size="9" font-weight="600" fill="{COLORS["text"]}">'
                f'{_escape(val_str)}</text>'
            )

    lines.append("</svg>")
    return "\n".join(lines)


def time_series_chart(
    data: list[tuple[str, int | float]],
    title: str = "",
    width: int = 520,
    height: int = 220,
    show_values: bool = True,
    area_fill: bool = True,
    color: str | None = None,
) -> str:
    """Generate a time series line/area chart as an SVG string.

    Args:
        data: List of (label, value) tuples in chronological order.
        title: Chart title.
        width: SVG width.
        height: SVG height.
        show_values: Annotate each data point with its value.
        area_fill: Fill area under the line.
        color: Line/fill color.
    """
    if not data or len(data) < 2:
        return ""

    line_color = color or COLORS["primary"]
    padding = {"top": 44 if title else 20, "right": 30, "bottom": 50, "left": 70}
    chart_w = width - padding["left"] - padding["right"]
    chart_h = height - padding["top"] - padding["bottom"]

    values = [v for _, v in data]
    min_val = min(values) * 0.85
    max_val = max(values) * 1.10
    if max_val == min_val:
        max_val = min_val + 1
    val_range = max_val - min_val

    def x_pos(i: int) -> float:
        return padding["left"] + (i / (len(data) - 1)) * chart_w

    def y_pos(v: float) -> float:
        return padding["top"] + chart_h - ((v - min_val) / val_range) * chart_h

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'style="font-family: \'Segoe UI\', Tahoma, sans-serif; background: {COLORS["bg"]}; '
        f'border: 1px solid {COLORS["border"]}; border-radius: 6px; margin: 8px 0;">',
    ]

    if title:
        lines.append(
            f'<text x="{width // 2}" y="28" text-anchor="middle" '
            f'font-size="11" font-weight="600" fill="{COLORS["primary_dark"]}">'
            f'{_escape(title)}</text>'
        )

    # Y-axis grid lines and labels (5 steps)
    for j in range(5):
        frac = j / 4
        grid_val = min_val + frac * val_range
        gy = padding["top"] + chart_h - frac * chart_h
        lines.append(
            f'<line x1="{padding["left"]}" y1="{gy:.1f}" '
            f'x2="{padding["left"] + chart_w}" y2="{gy:.1f}" '
            f'stroke="{COLORS["grid"]}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{padding["left"] - 8}" y="{gy + 3:.1f}" '
            f'text-anchor="end" font-size="7.5" fill="{COLORS["text_muted"]}">'
            f'{_fmt_number(grid_val)}</text>'
        )

    # Area fill
    if area_fill:
        area_points = []
        for i in range(len(data)):
            area_points.append(f"{x_pos(i):.1f},{y_pos(values[i]):.1f}")
        area_points.append(f"{x_pos(len(data) - 1):.1f},{padding['top'] + chart_h:.1f}")
        area_points.append(f"{x_pos(0):.1f},{padding['top'] + chart_h:.1f}")
        lines.append(
            f'<polygon points="{" ".join(area_points)}" '
            f'fill="{line_color}" opacity="0.12"/>'
        )

    # Line
    points = []
    for i in range(len(data)):
        points.append(f"{x_pos(i):.1f},{y_pos(values[i]):.1f}")
    lines.append(
        f'<polyline points="{" ".join(points)}" '
        f'fill="none" stroke="{line_color}" stroke-width="2.5" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
    )

    # Data points and annotations
    for i, (label, value) in enumerate(data):
        px, py = x_pos(i), y_pos(value)

        # Dot
        lines.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" '
            f'fill="white" stroke="{line_color}" stroke-width="2"/>'
        )

        # Value annotation — alternate above/below to prevent overlap
        if show_values:
            if i % 2 == 0:
                val_y = py - 12
                # If too close to top edge, push below
                if val_y < padding["top"] + 4:
                    val_y = py + 18
            else:
                val_y = py + 18
                # If too close to bottom edge, push above
                if val_y > padding["top"] + chart_h - 4:
                    val_y = py - 12

            lines.append(
                f'<text x="{px:.1f}" y="{val_y:.1f}" text-anchor="middle" '
                f'font-size="8" font-weight="600" fill="{COLORS["text"]}">'
                f'{_fmt_number(value)}</text>'
            )

        # X-axis label
        label_y = padding["top"] + chart_h + 14
        short_label = label[-5:] if len(label) > 5 else label
        lines.append(
            f'<text x="{px:.1f}" y="{label_y}" text-anchor="middle" '
            f'font-size="8" fill="{COLORS["text_muted"]}">'
            f'{_escape(short_label)}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


def pie_chart(
    data: list[tuple[str, int | float]],
    title: str = "",
    width: int = 520,
    height: int = 300,
    colors: list[str] | None = None,
) -> str:
    """Generate a pie/donut chart as an SVG string.

    Args:
        data: List of (label, value) tuples.
        title: Chart title.
        width: SVG width.
        height: SVG height.
        colors: Custom color list. Falls back to BAR_PALETTE.
    """
    import math

    if not data:
        return ""

    palette = colors or BAR_PALETTE
    total = sum(v for _, v in data)
    if total == 0:
        return ""

    cx = width // 2 - 60  # shift left to make room for legend
    cy = (height // 2) + (16 if title else 0)
    outer_r = min(cx - 30, cy - 30, 100)
    inner_r = outer_r * 0.55  # donut hole

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'style="font-family: \'Segoe UI\', Tahoma, sans-serif; background: {COLORS["bg"]}; '
        f'border: 1px solid {COLORS["border"]}; border-radius: 6px; margin: 8px 0;">',
    ]

    if title:
        lines.append(
            f'<text x="{width // 2}" y="24" text-anchor="middle" '
            f'font-size="11" font-weight="600" fill="{COLORS["primary_dark"]}">'
            f'{_escape(title)}</text>'
        )

    # Draw slices
    start_angle = -math.pi / 2  # start at top
    for i, (label, value) in enumerate(data):
        if value == 0:
            continue
        sweep = (value / total) * 2 * math.pi
        end_angle = start_angle + sweep

        # Outer arc
        x1_o = cx + outer_r * math.cos(start_angle)
        y1_o = cy + outer_r * math.sin(start_angle)
        x2_o = cx + outer_r * math.cos(end_angle)
        y2_o = cy + outer_r * math.sin(end_angle)

        # Inner arc (reverse direction for donut)
        x1_i = cx + inner_r * math.cos(end_angle)
        y1_i = cy + inner_r * math.sin(end_angle)
        x2_i = cx + inner_r * math.cos(start_angle)
        y2_i = cy + inner_r * math.sin(start_angle)

        large_arc = 1 if sweep > math.pi else 0
        fill_color = palette[i % len(palette)]

        path = (
            f"M {x1_o:.1f},{y1_o:.1f} "
            f"A {outer_r},{outer_r} 0 {large_arc},1 {x2_o:.1f},{y2_o:.1f} "
            f"L {x1_i:.1f},{y1_i:.1f} "
            f"A {inner_r},{inner_r} 0 {large_arc},0 {x2_i:.1f},{y2_i:.1f} "
            f"Z"
        )
        lines.append(f'<path d="{path}" fill="{fill_color}" opacity="0.85"/>')

        # Percentage label on the slice (midpoint of arc, between inner and outer)
        mid_angle = start_angle + sweep / 2
        label_r = (outer_r + inner_r) / 2
        lx = cx + label_r * math.cos(mid_angle)
        ly = cy + label_r * math.sin(mid_angle)
        pct = (value / total) * 100
        if pct >= 5:  # only show label if slice is big enough
            lines.append(
                f'<text x="{lx:.1f}" y="{ly + 3:.1f}" text-anchor="middle" '
                f'font-size="8" font-weight="600" fill="white">'
                f'{pct:.0f}%</text>'
            )

        start_angle = end_angle

    # Center total
    lines.append(
        f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" '
        f'font-size="20" font-weight="700" fill="{COLORS["primary_dark"]}">'
        f'{total}</text>'
    )
    lines.append(
        f'<text x="{cx}" y="{cy + 12}" text-anchor="middle" '
        f'font-size="8" fill="{COLORS["text_muted"]}">TOTAL</text>'
    )

    # Legend (right side)
    legend_x = cx + outer_r + 40
    legend_y_start = cy - (len(data) * 22) // 2
    for i, (label, value) in enumerate(data):
        ly = legend_y_start + i * 22
        fill_color = palette[i % len(palette)]
        pct = (value / total) * 100

        # Color swatch
        lines.append(
            f'<rect x="{legend_x}" y="{ly}" width="12" height="12" rx="2" '
            f'fill="{fill_color}" opacity="0.85"/>'
        )
        # Label
        lines.append(
            f'<text x="{legend_x + 18}" y="{ly + 10}" '
            f'font-size="9" fill="{COLORS["text_light"]}">'
            f'{_escape(label)}</text>'
        )
        # Value + percentage
        lines.append(
            f'<text x="{legend_x + 18}" y="{ly + 21}" '
            f'font-size="8" font-weight="600" fill="{COLORS["text"]}">'
            f'{value:,} ({pct:.1f}%)</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


def _aggregate_platforms_by_os(data: dict[str, int]) -> dict[str, int]:
    """Roll per-version platform counts up into Windows / Mac / Linux+Other.

    The analytics card returns rows like "Windows 11 Version 2009", "macOS 14",
    "Ubuntu 24.04"; presenting them grouped by OS family is much more
    informative than a long version-by-version list.
    """
    buckets = {"Windows": 0, "Mac": 0, "Linux & Other": 0}
    mac_markers = ("mac", "darwin", "osx", "os x")
    linux_markers = (
        "linux", "ubuntu", "debian", "fedora", "arch", "manjaro",
        "centos", "rhel", "red hat", "suse", "mint", "pop!_os", "popos",
        "gentoo", "alpine",
    )
    for name, count in data.items():
        low = (name or "").lower()
        try:
            value = int(count)
        except (TypeError, ValueError):
            continue
        if "windows" in low or low.startswith("win "):
            buckets["Windows"] += value
        elif any(m in low for m in mac_markers):
            buckets["Mac"] += value
        elif any(m in low for m in linux_markers):
            buckets["Linux & Other"] += value
        else:
            buckets["Linux & Other"] += value
    return {k: v for k, v in buckets.items() if v > 0}


def generate_analytics_charts(results: list[Any]) -> list[dict[str, str]]:
    """Generate chart SVGs from analytics collector results.

    Returns a list of dicts with 'title' and 'svg' keys.
    """
    charts = []

    for result in results:
        if result.section_name == "analytics":
            for item in result.items:
                meta = item.metadata or {}
                metric = meta.get("metric", "")

                if metric == "monthly_history" and meta.get("data"):
                    data_dict = meta["data"]
                    sorted_data = sorted(data_dict.items())
                    charts.append({
                        "title": "QGIS Monthly Opens",
                        "svg": time_series_chart(
                            [(k, v) for k, v in sorted_data],
                            title="QGIS Monthly Opens (Application Starts)",
                            width=520,
                            height=240,
                        ),
                    })

                elif metric == "top_countries" and meta.get("data"):
                    data_dict = meta["data"]
                    sorted_data = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)[:10]
                    charts.append({
                        "title": "Top Countries",
                        "svg": horizontal_bar_chart(
                            sorted_data,
                            title="Top 10 Countries by QGIS Opens (30 days)",
                            width=520,
                            max_label_width=55,
                        ),
                    })

                elif metric == "top_platforms" and meta.get("data"):
                    aggregated = _aggregate_platforms_by_os(meta["data"])
                    sorted_data = sorted(
                        aggregated.items(), key=lambda x: x[1], reverse=True
                    )
                    charts.append({
                        "title": "Platforms by OS",
                        "svg": horizontal_bar_chart(
                            sorted_data,
                            title="Platforms by OS (30 days)",
                            width=520,
                            max_label_width=140,
                        ),
                    })

        elif result.section_name == "plugin_stats":
            for item in result.items:
                meta = item.metadata or {}
                metric = meta.get("metric", "")

                if metric == "top_downloads_30d" and meta.get("data"):
                    data_dict = meta["data"]
                    sorted_data = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)[:5]
                    charts.append({
                        "title": "Top Plugins This Month",
                        "svg": horizontal_bar_chart(
                            sorted_data,
                            title="Top 5 Plugins by Downloads (30 days)",
                            width=520,
                            max_label_width=150,
                        ),
                    })

                elif metric == "top_downloads_alltime" and meta.get("data"):
                    data_dict = meta["data"]
                    sorted_data = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)[:5]
                    charts.append({
                        "title": "Top Plugins All Time",
                        "svg": horizontal_bar_chart(
                            sorted_data,
                            title="Top 5 Plugins by Downloads (All Time)",
                            width=520,
                            max_label_width=150,
                        ),
                    })

                elif metric == "most_voted" and meta.get("data"):
                    data_dict = meta["data"]
                    sorted_data = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)[:5]
                    charts.append({
                        "title": "Most Voted Plugins",
                        "svg": horizontal_bar_chart(
                            sorted_data,
                            title="Most Voted Plugins",
                            width=520,
                            max_label_width=150,
                            value_suffix=" votes",
                            color=COLORS["gold"],
                            multi_color=False,
                        ),
                    })

                elif metric == "top_countries" and meta.get("data"):
                    data_dict = meta["data"]
                    sorted_data = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)[:5]
                    charts.append({
                        "title": "Plugin Download Countries",
                        "svg": horizontal_bar_chart(
                            sorted_data,
                            title="Top 5 Plugin Download Countries",
                            width=520,
                            max_label_width=100,
                        ),
                    })

        elif result.section_name == "sustaining_members":
            for item in result.items:
                desc = item.description or ""
                # Parse "Current sustaining members: 3 Flagship, 9 Large, 27 Medium, 95 Small"
                if "Flagship" in desc and "Large" in desc:
                    import re
                    counts = re.findall(r"(\d+)\s+(Flagship|Large|Medium|Small)", desc)
                    if counts:
                        pie_data = [(level, int(n)) for n, level in counts]
                        member_colors = ["#e65100", "#1565c0", "#589632", "#93b023"]
                        charts.append({
                            "title": "Sustaining Members",
                            "svg": pie_chart(
                                pie_data,
                                title="Sustaining Members by Level",
                                width=520,
                                height=280,
                                colors=member_colors,
                            ),
                        })

        elif result.section_name == "user_groups":
            for item in result.items:
                meta = item.metadata or {}
                if meta.get("metric") != "user_groups_summary":
                    continue
                dist = meta.get("year_distribution") or {}
                # Sort by year ascending so the bar chart reads chronologically
                sorted_data = sorted(
                    dist.items(),
                    key=lambda x: x[0] if x[0] and x[0].isdigit() else "0",
                )
                if sorted_data:
                    charts.append({
                        "title": "User Groups",
                        "svg": horizontal_bar_chart(
                            sorted_data,
                            title="User Groups Registered Per Year",
                            width=520,
                            max_label_width=80,
                            multi_color=False,
                        ),
                    })

    return charts




# --- YEAR-AT-A-GLANCE TIMELINE -------------------------------------------
#
# Styled after https://qgis.org/resources/roadmap/: three light "card"
# panels (one per third of the year) each holding a straight stepper line,
# a green-vs-pending-grey progress split at today's position, and a folded
# ribbon flagging "today" - the same visual language the roadmap uses for
# its release-phase steppers and "Current: x.y.z" ribbons.
#
# The QGIS project's calendar is grounded in publicly documented patterns
# rather than any single year's exact schedule (several of these events -
# notably the User Conference and FOSS4G - move around the calendar from
# year to year). Sources used to place these markers:
#   - Feature releases land roughly every 4 months (Feb / Jun / Oct), with
#     one release per cycle designated the Long Term Release; see
#     https://changelog.qgis.org/ and the QGIS 4.0/LTR roadmap posts on
#     https://blog.qgis.org.
#   - The grant programme call, discussion and award dates follow the
#     yearly "QGIS Grants" blog series, e.g.
#     https://blog.qgis.org/2026/03/16/qgis-grants-11-call-for-grant-proposals-2026/
#     and the matching results post in May.
#   - The AGM (budget approval, financial report, PSC elections) is held
#     virtually in Nov/Dec each year; see
#     https://www.qgis.org/community/foundation/annual_general_meetings/.
#   - The QGIS budget year is the calendar year (see the annual budget/
#     financial report PDFs under qgis.org/community/foundation/).
#   - FOSS4G International and the QGIS User Conference dates are taken
#     from their most recently announced editions and flagged as variable.
def _load_timeline_data() -> dict:
    """Load the year-at-a-glance timeline content from timeline.json.

    Kept as editable data (rather than code) so the recurring annual
    QGIS event calendar can be updated without touching chart logic.
    """
    raw = resources.files("qgis_news_gatherer.data").joinpath("timeline.json").read_text()
    return json.loads(raw)


_TIMELINE_DATA = _load_timeline_data()

_TIMELINE_REF_YEAR = _TIMELINE_DATA["reference_year"]  # non-leap year, used only for day-of-year math

_TIMELINE_CATEGORY_COLORS = {
    key: COLORS[spec["color"]] for key, spec in _TIMELINE_DATA["categories"].items()
}

_TIMELINE_CATEGORY_LABELS = {
    key: spec["label"] for key, spec in _TIMELINE_DATA["categories"].items()
}

# (key, label, month, day, category, size, note, label_side)
# size: "major" (ringed, larger) or "minor". label_side: -1 above, +1 below.
_TIMELINE_EVENTS = [
    (e["key"], e["label"], e["month"], e["day"], e["category"], e["size"], e["note"],
     e["label_side"])
    for e in _TIMELINE_DATA["events"]
]

# Months in which a feature release lands - bugfix/point releases for the
# active branch are skipped in those months since the feature release
# itself is the release event that month.
_TIMELINE_BUGFIX_MONTHS = _TIMELINE_DATA["bugfix_release"]["months"]
_TIMELINE_BUGFIX_DAY = _TIMELINE_DATA["bugfix_release"]["day"]

# Each card spans four months. Card boundaries are calendar-ordered (unlike
# a meandering river, a roadmap-style stepper reads left-to-right on every
# row) so "past" always means "earlier card, or earlier on this card's line".
_TIMELINE_CARDS = _TIMELINE_DATA["cards"]


def _timeline_doy(month: int, day: int) -> int:
    """Day-of-year for (month, day) in the timeline's reference year."""
    return date(_TIMELINE_REF_YEAR, month, day).timetuple().tm_yday


def _timeline_last_friday(month: int) -> int:
    """Day-of-month of the last Friday of the given month (reference year)."""
    last_day = calendar.monthrange(_TIMELINE_REF_YEAR, month)[1]
    d = date(_TIMELINE_REF_YEAR, month, last_day)
    offset = (d.weekday() - 4) % 7  # Friday == 4
    return d.day - offset


def _timeline_card_layout(width: float, height: float) -> list[dict]:
    """Compute pixel geometry for the three quarter cards.

    Returns each card's rect, its stepper line's y and x-range, and its
    day-of-year span, so callers can place ticks/dots/labels by date alone.
    """
    card_x = 24.0
    card_w = width - 2 * card_x
    card_gap = 16.0
    bottom_reserved = 66.0  # legend row + caption
    top_pad = 6.0
    card_h = (height - top_pad - bottom_reserved - 2 * card_gap) / 3

    cards = []
    for i, spec in enumerate(_TIMELINE_CARDS):
        card_y = top_pad + i * (card_h + card_gap)
        start_doy = _timeline_doy(spec["start_month"], 1)
        end_month = spec["end_month"]
        end_day = calendar.monthrange(_TIMELINE_REF_YEAR, end_month)[1]
        end_doy = _timeline_doy(end_month, end_day) + 1  # exclusive
        cards.append({
            **spec,
            "x": card_x,
            "y": card_y,
            "w": card_w,
            "h": card_h,
            "line_y": card_y + 72,
            "x0": card_x + 34,
            "x1": card_x + card_w - 34,
            "start_doy": start_doy,
            "end_doy": end_doy,
        })
    return cards


def _timeline_x_in_card(card: dict, doy: int) -> float:
    """Map a day-of-year to an x position along a card's stepper line."""
    span = card["end_doy"] - card["start_doy"]
    t = (doy - card["start_doy"]) / span if span else 0.0
    t = min(max(t, 0.0), 1.0)
    return card["x0"] + t * (card["x1"] - card["x0"])


def _timeline_card_for_doy(cards: list[dict], doy: int) -> int:
    """Index of the card whose month range contains ``doy``."""
    for i, card in enumerate(cards):
        if doy < card["end_doy"] or i == len(cards) - 1:
            return i
    return len(cards) - 1


_TIMELINE_LABEL_WRAP_CHARS = 18


def _wrap_timeline_label(label: str) -> list[str]:
    """Wrap a long event label onto two lines, breaking at the nearest space
    to the middle - two short lines take less horizontal room (and so
    collide with neighboring events less) than one long one.
    """
    if len(label) <= _TIMELINE_LABEL_WRAP_CHARS:
        return [label]
    spaces = [i for i, ch in enumerate(label) if ch == " "]
    if not spaces:
        return [label]
    mid = len(label) / 2
    split = min(spaces, key=lambda i: abs(i - mid))
    return [label[:split].rstrip(), label[split + 1 :].lstrip()]


def generate_year_timeline_svg(
    current_date: date,
    width: int = 1000,
    height: int = 580,
) -> str:
    """Generate the "QGIS Year at a Glance" timeline as an inline SVG.

    Plots the recurring annual cycle of QGIS project events (releases,
    grants, the AGM cycle, budget year, conferences, and monthly Open
    Days) as three stacked quarter-cards styled after the QGIS.org
    roadmap page: a stepper line that turns from green (elapsed) to grey
    (still ahead) at ``current_date``'s position, filled dots for events
    already past and hollow dots for events still ahead, and a folded
    ribbon flagging "today" on the current card.

    Args:
        current_date: The date to mark as "today" on the timeline.
        width: SVG width.
        height: SVG height.
    """
    cards = _timeline_card_layout(width, height)

    # Map onto the (non-leap) reference year by month/day so Feb 29 in a
    # leap year still lands sensibly on the timeline.
    today_doy = _timeline_doy(
        current_date.month,
        min(current_date.day, calendar.monthrange(_TIMELINE_REF_YEAR, current_date.month)[1]),
    )
    today_card_index = _timeline_card_for_doy(cards, today_doy)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'style="font-family: \'Segoe UI\', Tahoma, sans-serif;">',
    ]

    ribbon_green = COLORS["timeline_ribbon"]
    pending_grey = COLORS["timeline_pending"]
    progress_green = COLORS["primary"]

    for card_index, card in enumerate(cards):
        cx, cy, cw, ch = card["x"], card["y"], card["w"], card["h"]
        line_y, x0, x1 = card["line_y"], card["x0"], card["x1"]

        # Card panel
        lines.append(
            f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cw:.1f}" height="{ch:.1f}" '
            f'rx="10" fill="{COLORS["timeline_card_bg"]}"/>'
        )
        lines.append(
            f'<text x="{cx + 20:.1f}" y="{cy + 26:.1f}" '
            f'font-size="12.5" font-weight="700" letter-spacing="0.5" '
            f'fill="{COLORS["text"]}">{_escape(card["heading"])}</text>'
        )

        # Month-division gridlines, drawn before everything else in this
        # card so the stepper, dots, and labels all paint on top of them.
        for month in range(card["start_month"], card["end_month"] + 1):
            mx = _timeline_x_in_card(card, _timeline_doy(month, 1))
            lines.append(
                f'<line x1="{mx:.1f}" y1="{cy + 34:.1f}" x2="{mx:.1f}" y2="{cy + ch - 6:.1f}" '
                f'stroke="{COLORS["grid"]}" stroke-width="1"/>'
            )

        # Stepper line: green for elapsed days, pending-grey for the rest.
        if card_index < today_card_index:
            lines.append(
                f'<line x1="{x0:.1f}" y1="{line_y:.1f}" x2="{x1:.1f}" y2="{line_y:.1f}" '
                f'stroke="{progress_green}" stroke-width="3" stroke-linecap="round"/>'
            )
        elif card_index > today_card_index:
            lines.append(
                f'<line x1="{x0:.1f}" y1="{line_y:.1f}" x2="{x1:.1f}" y2="{line_y:.1f}" '
                f'stroke="{pending_grey}" stroke-width="3" stroke-linecap="round"/>'
            )
        else:
            tx = _timeline_x_in_card(card, today_doy)
            lines.append(
                f'<line x1="{x0:.1f}" y1="{line_y:.1f}" x2="{tx:.1f}" y2="{line_y:.1f}" '
                f'stroke="{progress_green}" stroke-width="3" stroke-linecap="round"/>'
            )
            lines.append(
                f'<line x1="{tx:.1f}" y1="{line_y:.1f}" x2="{x1:.1f}" y2="{line_y:.1f}" '
                f'stroke="{pending_grey}" stroke-width="3" stroke-linecap="round"/>'
            )
            # Today tick: a small flag crossing the line at its exact spot.
            lines.append(
                f'<line x1="{tx:.1f}" y1="{line_y - 11:.1f}" x2="{tx:.1f}" y2="{line_y + 11:.1f}" '
                f'stroke="{ribbon_green}" stroke-width="2.5"/>'
            )
            lines.append(
                f'<circle cx="{tx:.1f}" cy="{line_y:.1f}" r="4.5" fill="{ribbon_green}" '
                f'stroke="white" stroke-width="1.5"/>'
            )

            # "Today" ribbon, standing vertically at the tick. Drawn here -
            # before this card's month/event labels below - so it sits
            # behind them in paint order instead of covering them.
            ribbon_label = f"TODAY · {current_date.strftime('%-d %b %Y')}"
            ribbon_w = 26 + len(ribbon_label) * 5.6
            ribbon_cx = min(
                max(tx, card["x"] + 15),
                card["x"] + card["w"] - 15,
            )
            lines.append(f'<g transform="translate({ribbon_cx:.1f},{line_y:.1f}) rotate(-90)">')
            lines.append(
                f'<rect x="{-ribbon_w / 2:.1f}" y="-11" width="{ribbon_w:.1f}" height="22" '
                f'fill="{ribbon_green}"/>'
            )
            lines.append(
                f'<text x="0" y="4" text-anchor="middle" font-size="9.5" font-weight="700" '
                f'fill="white">{_escape(ribbon_label)}</text>'
            )
            lines.append("</g>")

        # Month tick marks + labels along the top of the line. The first
        # month's label is skipped - the card heading already names it,
        # and the two would otherwise collide.
        for month in range(card["start_month"], card["end_month"] + 1):
            mx = _timeline_x_in_card(card, _timeline_doy(month, 1))
            lines.append(
                f'<circle cx="{mx:.1f}" cy="{line_y:.1f}" r="2" fill="{COLORS["text_muted"]}"/>'
            )
            if month == card["start_month"]:
                continue
            lines.append(
                f'<text x="{mx:.1f}" y="{line_y - 42:.1f}" text-anchor="middle" '
                f'font-size="7.5" font-weight="600" letter-spacing="0.5" '
                f'fill="{COLORS["text_muted"]}">'
                f'{calendar.month_abbr[month].upper()}</text>'
            )

        # Recurring markers: QGIS Open Day (last Friday, monthly)
        for month in range(card["start_month"], card["end_month"] + 1):
            day = _timeline_last_friday(month)
            ox = _timeline_x_in_card(card, _timeline_doy(month, day))
            lines.append(
                f'<circle cx="{ox:.1f}" cy="{line_y:.1f}" r="2.5" '
                f'fill="{COLORS["primary_light"]}" opacity="0.7"/>'
            )
            if month == 1:
                lines.append(
                    f'<text x="{ox:.1f}" y="{line_y + 30:.1f}" text-anchor="middle" '
                    f'font-size="6.5" font-style="italic" fill="{COLORS["text_muted"]}">'
                    f'Open Day (last Fri, monthly)</text>'
                )

        # Recurring markers: bugfix/point releases
        for month in range(card["start_month"], card["end_month"] + 1):
            if month not in _TIMELINE_BUGFIX_MONTHS:
                continue
            bx = _timeline_x_in_card(card, _timeline_doy(month, _TIMELINE_BUGFIX_DAY))
            lines.append(
                f'<circle cx="{bx:.1f}" cy="{line_y:.1f}" r="2.5" '
                f'fill="{COLORS["accent"]}" opacity="0.7"/>'
            )
            if month == 4:
                lines.append(
                    f'<text x="{bx:.1f}" y="{line_y - 30:.1f}" text-anchor="middle" '
                    f'font-size="6.5" font-style="italic" fill="{COLORS["text_muted"]}">'
                    f'Bugfix releases (~monthly)</text>'
                )

        # Named milestone events for this card's month range
        for _key, label, month, day, category, size, note, side in _TIMELINE_EVENTS:
            if not (card["start_month"] <= month <= card["end_month"]):
                continue
            doy = _timeline_doy(month, day)
            ex = _timeline_x_in_card(card, doy)
            color = _TIMELINE_CATEGORY_COLORS[category]
            is_major = size == "major"
            is_past = doy <= today_doy
            r = 7 if is_major else 5.5

            if is_major:
                lines.append(
                    f'<circle cx="{ex:.1f}" cy="{line_y:.1f}" r="{r + 3}" '
                    f'fill="none" stroke="{color}" stroke-width="1.5" opacity="0.45"/>'
                )
            lines.append(
                f'<circle cx="{ex:.1f}" cy="{line_y:.1f}" r="{r}" '
                f'fill="{color if is_past else "white"}" stroke="{color}" '
                f'stroke-width="{2.5 if is_major else 1.5}"/>'
            )

            leader_len = 20 if is_major else 15
            label_y = line_y + side * leader_len
            lines.append(
                f'<line x1="{ex:.1f}" y1="{(line_y + side * r):.1f}" '
                f'x2="{ex:.1f}" y2="{(label_y - side * 9):.1f}" '
                f'stroke="{color}" stroke-width="1" opacity="0.5"/>'
            )
            font_size = 8.5 if is_major else 7.8
            font_weight = "700" if is_major else "600"
            line_height = font_size + 2.2
            label_lines = _wrap_timeline_label(label)

            # Keep long labels from overflowing the card near its left/right
            # edge: switch anchoring instead of letting text run off the
            # page (there's no clip-path, so overflow would just vanish
            # past the SVG viewBox).
            half_w = max(len(line) for line in label_lines) * font_size * 0.52
            card_left, card_right = card["x"] + 8, card["x"] + card["w"] - 8
            if ex - half_w < card_left:
                anchor, text_x = "start", max(ex - r - 4, card_left)
            elif ex + half_w > card_right:
                anchor, text_x = "end", min(ex + r + 4, card_right)
            else:
                anchor, text_x = "middle", ex

            # "Slot" 0 is the text position closest to the stepper line
            # (label_y); each slot further out adds one line_height in the
            # `side` direction. Below the line (side=+1), reading order
            # already runs outward, so wrapped line j is slot j. Above the
            # line (side=-1), reading order has to run the other way - the
            # line read *first* belongs farthest out - so slot assignment
            # reverses, otherwise a two-line label reads bottom-to-top.
            num_lines = len(label_lines)
            for line_index, line_text in enumerate(label_lines):
                slot = line_index if side > 0 else (num_lines - 1 - line_index)
                lines.append(
                    f'<text x="{text_x:.1f}" y="{(label_y + side * slot * line_height):.1f}" '
                    f'text-anchor="{anchor}" font-size="{font_size}" font-weight="{font_weight}" '
                    f'fill="{COLORS["text"]}">{_escape(line_text)}</text>'
                )
            if note:
                note_y = label_y + side * num_lines * line_height
                lines.append(
                    f'<text x="{text_x:.1f}" y="{note_y:.1f}" '
                    f'text-anchor="{anchor}" font-size="6.5" font-style="italic" '
                    f'fill="{COLORS["text_muted"]}">{_escape(note)}</text>'
                )

    # Legend
    legend_items = [
        (color, _TIMELINE_CATEGORY_LABELS[cat])
        for cat, color in _TIMELINE_CATEGORY_COLORS.items()
    ] + [
        (COLORS["primary_light"], "Open Day (monthly)"),
        (COLORS["accent"], "Bugfix release (recurring)"),
        (ribbon_green, "Today"),
    ]
    legend_y = height - 34
    legend_x = 40.0
    for color, text in legend_items:
        lines.append(
            f'<circle cx="{legend_x:.1f}" cy="{legend_y:.1f}" r="5" fill="{color}"/>'
        )
        lines.append(
            f'<text x="{legend_x + 11:.1f}" y="{legend_y + 3:.1f}" '
            f'font-size="8" fill="{COLORS["text_light"]}">{_escape(text)}</text>'
        )
        legend_x += 18 + len(text) * 4.6 + 20
    lines.append(
        f'<text x="40" y="{legend_y + 20:.1f}" '
        f'font-size="7.5" fill="{COLORS["text_muted"]}">'
        f'● filled = already happened this year    ○ hollow = still ahead</text>'
    )

    # Caption
    lines.append(
        f'<text x="{width / 2}" y="{height - 4}" text-anchor="middle" '
        f'font-size="7" font-style="italic" fill="{COLORS["text_muted"]}">'
        f'Illustrative annual cycle based on recent years’ patterns — '
        f'exact dates are announced each year at qgis.org</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines)
