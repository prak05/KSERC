"""
Tests for extraction accuracy improvements:
- Smart column header detection (_detect_claimed_column_index)
- Row scan with column-aware extraction (_scan_arr_table)
- Number parsing (_num)
"""

import pytest
import pandas as pd
from src.agents.extractor import (
    _num,
    _detect_claimed_column_index,
    _scan_arr_table,
    _empty_expenses,
    _empty_revenues,
)


# ═══════════════════════════════════════════════════════════════════════════
# _num() tests — number parsing
# ═══════════════════════════════════════════════════════════════════════════

class TestNumParsing:
    def test_simple_number(self):
        assert _num("4652.88") == 4652.88

    def test_comma_separated(self):
        assert _num("4,652.88") == 4652.88

    def test_negative_parentheses(self):
        assert _num("(86.84)") == -86.84

    def test_zero(self):
        assert _num("0.0") == 0.0

    def test_integer(self):
        assert _num("100") == 100.0

    def test_blank_string(self):
        assert _num("") is None

    def test_non_numeric(self):
        assert _num("Power Purchase") is None

    def test_whitespace(self):
        assert _num("  4652.88  ") == 4652.88


# ═══════════════════════════════════════════════════════════════════════════
# _detect_claimed_column_index() tests
# ═══════════════════════════════════════════════════════════════════════════

class TestColumnDetection:
    def test_petition_header(self):
        """Should find 'Petition for Truing Up' column."""
        df = pd.DataFrame(
            {"Sl.No": [1], "Particulars": ["PPC"], "ARR Approved": [100], "Petition for Truing Up": [200]}
        )
        assert _detect_claimed_column_index(df) == 3

    def test_claimed_header(self):
        """Should find 'Claimed' column."""
        df = pd.DataFrame(
            {"Particulars": ["PPC"], "Approved in MYT": [100], "Claimed for Truing Up": [200], "Trued Up": [150]}
        )
        assert _detect_claimed_column_index(df) == 2

    def test_actual_header(self):
        """Should find 'Actual' column."""
        df = pd.DataFrame(
            {"Particulars": ["PPC"], "Projected": [100], "Actual": [200]}
        )
        assert _detect_claimed_column_index(df) == 2

    def test_skip_approved_column(self):
        """Should NOT select 'ARR Approved' even if no claimed column present."""
        df = pd.DataFrame(
            {"Particulars": ["PPC"], "ARR Approved": [100], "Other": [200]}
        )
        # No claimed column found → should return None
        assert _detect_claimed_column_index(df) is None

    def test_skip_trued_up(self):
        """'Trued Up' should not be selected as the claimed column."""
        df = pd.DataFrame(
            {"Particulars": ["PPC"], "Claimed": [200], "Trued Up by KSERC": [150]}
        )
        # Should pick 'Claimed' (index 1), NOT 'Trued Up' (index 2)
        assert _detect_claimed_column_index(df) == 1

    def test_merged_header_in_first_row(self):
        """Should detect column from first data row if headers are numeric."""
        df = pd.DataFrame(
            [[" Particulars ", " ARR Approved ", " Petition for Truing Up "],
             ["PPC", "100", "200"]],
            columns=["0", "1", "2"]
        )
        assert _detect_claimed_column_index(df) == 2


# ═══════════════════════════════════════════════════════════════════════════
# _scan_arr_table() tests — integrated row scan with column detection
# ═══════════════════════════════════════════════════════════════════════════

class TestScanArrTable:
    def test_picks_claimed_column_not_rightmost(self):
        """
        Critical test: 3-column table where 'Claimed' is col 2 but
        'Trued Up' (col 3) has a different value. Old code would pick col 3.
        New code should pick col 2.
        """
        df = pd.DataFrame({
            "Particulars": [
                "Cost of Power Purchase",
                "Employee Cost",
                "Depreciation",
            ],
            "ARR Approved": [5000.0, 25.0, 100.0],
            "Petition for Truing Up": [6000.0, 60.0, 70.0],
            "Trued Up by KSERC": [5500.0, 28.0, 69.0],
        })

        expenses = _empty_expenses()
        revenues = _empty_revenues()

        found = _scan_arr_table([df], expenses, revenues)

        assert found is True
        # Should pick from 'Petition for Truing Up' column, not rightmost 'Trued Up'
        assert expenses["power_purchase_cost"] == 6000.0
        assert expenses["employee_cost"] == 60.0
        assert expenses["depreciation"] == 70.0

    def test_fallback_rightmost_when_no_header_match(self):
        """When no claimed column header is detected, fall back to rightmost."""
        df = pd.DataFrame({
            "Particulars": ["Cost of Power Purchase"],
            "Col A": [5000.0],
            "Col B": [6000.0],
        })

        expenses = _empty_expenses()
        revenues = _empty_revenues()

        found = _scan_arr_table([df], expenses, revenues)

        assert found is True
        # Should fall back to rightmost = 6000.0
        assert expenses["power_purchase_cost"] == 6000.0

    def test_revenue_extraction(self):
        """Revenue items should also be extracted."""
        df = pd.DataFrame({
            "Particulars": ["Revenue from Sale of Power"],
            "Approved": [7000.0],
            "Claimed": [7400.0],
        })

        expenses = _empty_expenses()
        revenues = _empty_revenues()

        found = _scan_arr_table([df], expenses, revenues)

        assert found is True
        assert revenues["revenue_from_sale"] == 7400.0

    def test_empty_dataframe(self):
        """Empty DataFrame should not crash."""
        df = pd.DataFrame()
        expenses = _empty_expenses()
        revenues = _empty_revenues()

        found = _scan_arr_table([df], expenses, revenues)
        assert found is False
