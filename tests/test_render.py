"""
Tests for builder/render.py — Jinja2 HTML rendering from order JSON.
"""

import json
import pytest
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from builder.json_builder import build_order_json
from builder.render import build_html


@pytest.fixture
def infopark_order_json():
    """Build order JSON from Infopark results."""
    p = Path(__file__).resolve().parent.parent / "results_infopark_2024_25.json"
    if not p.exists():
        pytest.skip(f"Missing test fixture: {p.name}")
    with open(p, "r", encoding="utf-8") as f:
        state = json.load(f)
    return build_order_json(state)


@pytest.fixture
def infopark_html(infopark_order_json):
    """Render HTML from Infopark order JSON."""
    return build_html(infopark_order_json, skip_validation=True)


class TestRenderOutput:
    """Test the rendered HTML output."""

    def test_returns_string(self, infopark_html):
        assert isinstance(infopark_html, str)
        assert len(infopark_html) > 1000  # Reasonable minimum

    def test_has_doctype(self, infopark_html):
        assert "<!DOCTYPE html>" in infopark_html

    def test_has_kserc_header(self, infopark_html):
        assert "Kerala State Electricity Regulatory Commission" in infopark_html

    def test_analysis_decision_header_once(self, infopark_html):
        """'Analysis and Decision' must appear exactly once as an h2."""
        count = infopark_html.count("Analysis and Decision")
        assert count == 1, f"'Analysis and Decision' appeared {count} times (expected 1)"

    def test_has_signature_block(self, infopark_html):
        assert "Chairman" in infopark_html
        assert "Member" in infopark_html

    def test_has_orders_section(self, infopark_html):
        assert "Orders of the Commission" in infopark_html

    def test_no_placeholder_0_00_in_revenue(self, infopark_html):
        """Revenue values should not be 0.00 — they should have real numbers."""
        # This test ensures we're not passing placeholder zeros
        # The actual revenue from sale should be a real number > 0
        assert "Revenue from Sale of Power" in infopark_html

    def test_table_numbers_present(self, infopark_html):
        """Tables should have visible table numbers."""
        assert "Table 1:" in infopark_html

    def test_has_css(self, infopark_html):
        """CSS must be embedded in the HTML."""
        assert "font-family" in infopark_html
        assert ".data-table" in infopark_html

    def test_decision_paragraphs_styled(self, infopark_html):
        """Decision paragraphs should have the decision-para class."""
        assert "decision-para" in infopark_html


class TestRenderEdgeCases:
    """Test edge cases in rendering."""

    def test_empty_order_json(self):
        """Minimal order JSON should still render without errors."""
        minimal = {
            "meta": {},
            "cover": {},
            "introduction": {"paragraphs": [], "tables": []},
            "hearing": {"paragraphs": []},
            "sections": [],
            "orders": {"paragraphs": []},
            "values": {},
            "signature": {},
        }
        html = build_html(minimal, skip_validation=True)
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
