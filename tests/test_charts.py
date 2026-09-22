# SPDX-FileCopyrightText: 2026 Kartoza <info@kartoza.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for SVG chart generation."""

import xml.etree.ElementTree as ET
from datetime import date

from qgis_news_gatherer.charts import generate_year_timeline_svg


class TestYearTimelineSvg:
    """Tests for the QGIS year-at-a-glance timeline SVG."""

    def test_produces_valid_xml(self) -> None:
        """The generated SVG must be well-formed XML."""
        svg = generate_year_timeline_svg(date(2026, 9, 21))
        ET.fromstring(svg)  # raises if malformed

    def test_includes_all_required_milestones(self) -> None:
        """All fourteen requested annual events appear on the timeline."""
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
            assert label in svg, f"missing timeline label: {label}"

    def test_marks_current_date(self) -> None:
        """The 'today' badge reflects the date passed in."""
        svg = generate_year_timeline_svg(date(2026, 1, 15))
        assert "TODAY · 15 Jan 2026" in svg

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
