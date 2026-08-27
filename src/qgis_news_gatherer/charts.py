"""SVG chart generation for PDF reports.

Generates inline SVG charts compatible with WeasyPrint (no JavaScript).
Uses QGIS branding colors.
"""

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
                    data_dict = meta["data"]
                    sorted_data = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)[:8]
                    charts.append({
                        "title": "Top Platforms",
                        "svg": horizontal_bar_chart(
                            sorted_data,
                            title="Top Platforms (30 days)",
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

    return charts
