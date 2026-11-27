# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for SVG chart generation."""

import re
import xml.etree.ElementTree as ET
from datetime import date

from qgis_news_gatherer.charts import COLORS, _wrap_timeline_label, generate_year_timeline_svg


class TestYearTimelineSvg:
    """Tests for the QGIS year-at-a-glance timeline SVG."""

    def test_produces_valid_xml(self) -> None:
        """The generated SVG must be well-formed XML."""
        svg = generate_year_timeline_svg(date(2026, 9, 21))
        ET.fromstring(svg)  # raises if malformed

    def test_includes_all_required_milestones(self) -> None:
        """All fourteen requested annual events appear on the timeline.

        Long labels wrap onto two lines, so a label is "present" when every
        wrapped line of it appears - not necessarily as one literal string.
        """
        svg = generate_year_timeline_svg(date(2026, 9, 21))

        expected_labels = [
            "QGIS User Conference",
            "Financial report published",
            "Budget year starts",
            "Budget year ends",
            "Feature release",
            "Feature release + LTR designation",
            "Bugfix releases",
            "Call for grant proposals opens",
            "Grant awards announced",
            "Open Day",
            "FOSS4G International Conference",
            "AGM: call for matters arising",
            "AGM: discussion period",
            "AGM: PSC election nominations",
            "AGM: PSC elections",
        ]
        for label in expected_labels:
            for wrapped_line in _wrap_timeline_label(label):
                assert wrapped_line in svg, f"missing timeline label line: {wrapped_line!r}"

    def test_wraps_long_labels_onto_two_lines(self) -> None:
        """A label past the wrap threshold splits at the nearest space to its middle."""
        assert _wrap_timeline_label("Feature release") == ["Feature release"]
        assert _wrap_timeline_label("FOSS4G International Conference") == [
            "FOSS4G International",
            "Conference",
        ]

    def test_marks_current_date(self) -> None:
        """The 'today' badge reflects the date passed in."""
        svg = generate_year_timeline_svg(date(2026, 1, 15))
        assert "TODAY · 15 Jan 2026" in svg

    def test_today_ribbon_sits_near_the_today_tick(self) -> None:
        """The TODAY ribbon tracks the actual tick, not a fixed card corner.

        A date late in its quarter-card used to still show the ribbon in
        the same spot as a date early in the card (a fixed offset from the
        card's right edge) - the ribbon must instead move with the tick.
        """
        tick_x = re.search(
            r'<line x1="([\d.]+)" y1="[\d.]+" x2="\1" y2="[\d.]+" '
            r'stroke="#3a9800" stroke-width="2.5"/>',
            generate_year_timeline_svg(date(2026, 11, 27)),
        )
        ribbon_x = re.search(
            r'<g transform="translate\(([\d.]+),[\d.]+\) rotate\(-90\)">',
            generate_year_timeline_svg(date(2026, 11, 27)),
        )
        assert tick_x and ribbon_x
        assert abs(float(tick_x.group(1)) - float(ribbon_x.group(1))) < 80

    def test_today_ribbon_is_vertical_and_behind_other_text(self) -> None:
        """The ribbon stands at 90 degrees and paints before (under) labels."""
        svg = generate_year_timeline_svg(date(2026, 11, 27))
        ribbon_match = re.search(r'<g transform="translate\([\d.]+,[\d.]+\) rotate\(-90\)">', svg)
        assert ribbon_match
        # It must appear in the document before the card's own text labels
        # (e.g. the month-heading), since SVG paints later elements on top.
        later_text = svg.index("AGM: PSC elections")
        assert ribbon_match.start() < later_text

    def test_month_divisions_have_gridlines(self) -> None:
        """Each month boundary gets a gray vertical divider line."""
        svg = generate_year_timeline_svg(date(2026, 6, 1))
        assert svg.count(f'stroke="{COLORS["grid"]}" stroke-width="1"/>') == 12

    def test_handles_leap_day(self) -> None:
        """29 February on a leap year does not raise."""
        svg = generate_year_timeline_svg(date(2028, 2, 29))
        ET.fromstring(svg)
        assert "TODAY · 29 Feb 2028" in svg

    def test_quarter_cards_present(self) -> None:
        """Each quarter card's heading names its first month directly."""
        svg = generate_year_timeline_svg(date(2026, 6, 1))
        assert "JANUARY – APRIL" in svg
        assert "MAY – AUGUST" in svg
        assert "SEPTEMBER – DECEMBER" in svg

    def test_non_heading_months_labelled(self) -> None:
        """The three non-heading months in each card get a tick label.

        The first month of each quarter card is named by the card's own
        heading (e.g. "JANUARY - APRIL") rather than repeated as a tick
        label underneath it, so only the other three months per card get
        a standalone tick label.
        """
        svg = generate_year_timeline_svg(date(2026, 6, 1))
        for month in [
            "FEB", "MAR", "APR", "JUN", "JUL", "AUG", "OCT", "NOV", "DEC",
        ]:
            assert svg.count(f">{month}<") == 1
