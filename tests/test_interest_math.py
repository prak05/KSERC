"""
Pytest tests for KSERC Interest & Finance Charges math functions.
=================================================================

Unit tests for the 6 interest/finance functions in normative_math.py:
  - calculate_interest_on_normative_loan (Component B)
  - calculate_working_capital_interest (Component C)
  - calculate_security_deposit_interest (Component D)
  - classify_bank_charge (Component E)
  - calculate_carrying_cost (Component F)
  - calculate_notional_surplus_interest (Component G)
"""

import pytest
from src.tools.normative_math import (
    calculate_interest_on_normative_loan,
    calculate_working_capital_interest,
    calculate_security_deposit_interest,
    calculate_carrying_cost,
    calculate_notional_surplus_interest,
    classify_bank_charge,
)


# ═══════════════════════════════════════════════════════════════════════
# Component B — Interest on Normative Loan
# ═══════════════════════════════════════════════════════════════════════

class TestNormativeLoanInterest:
    """Tests for calculate_interest_on_normative_loan (full spec version)."""

    def test_standard_case(self):
        """Normal loan with opening, additions, depreciation repayment."""
        result = calculate_interest_on_normative_loan(
            opening_balance=100.0,
            qualifying_additions=20.0,
            surplus_funded_additions=0.0,
            repayment_depreciation=30.0,
            eblr_rate=0.0915,
        )
        # Closing = 100 + 20 - 30 = 90
        # Average = (100 + 90) / 2 = 95
        # Interest = 95 × 0.0915 = 8.69 (rounded)
        assert result["closing_balance"] == 90.0
        assert result["average_balance"] == 95.0
        assert result["interest_rs_lakhs"] == 8.69
        assert result["is_exhausted"] is False
        assert result["provisional"] is False

    def test_exhausted_loan_negative_closing(self):
        """Repayment exceeds balance → interest = 0, store closing as 0."""
        result = calculate_interest_on_normative_loan(
            opening_balance=50.0,
            qualifying_additions=0.0,
            surplus_funded_additions=0.0,
            repayment_depreciation=70.0,
            eblr_rate=0.0915,
        )
        # Closing = 50 + 0 - 70 = -20 → exhausted
        assert result["is_exhausted"] is True
        assert result["closing_balance"] == 0.0
        assert result["raw_closing_balance"] == -20.0
        assert result["interest_rs_lakhs"] == 0.0

    def test_zero_opening(self):
        """Zero opening, new additions only."""
        result = calculate_interest_on_normative_loan(
            opening_balance=0.0,
            qualifying_additions=100.0,
            surplus_funded_additions=0.0,
            repayment_depreciation=20.0,
            eblr_rate=0.10,
        )
        # Closing = 0 + 100 - 20 = 80
        # Average = (0 + 80) / 2 = 40
        # Interest = 40 × 0.10 = 4.0
        assert result["closing_balance"] == 80.0
        assert result["average_balance"] == 40.0
        assert result["interest_rs_lakhs"] == 4.0

    def test_surplus_funded_exclusion(self):
        """Additions ordered from surplus must be excluded."""
        result = calculate_interest_on_normative_loan(
            opening_balance=100.0,
            qualifying_additions=50.0,
            surplus_funded_additions=30.0,  # Only 20 qualifies
            repayment_depreciation=25.0,
            eblr_rate=0.10,
        )
        # Net additions = 50 - 30 = 20
        # Closing = 100 + 20 - 25 = 95
        # Average = (100 + 95) / 2 = 97.5
        assert result["net_additions"] == 20.0
        assert result["excluded_surplus_additions"] == 30.0
        assert result["closing_balance"] == 95.0
        assert result["average_balance"] == 97.5
        assert result["interest_rs_lakhs"] == 9.75

    def test_provisional_flag(self):
        """When depreciation is not approved, result is provisional."""
        result = calculate_interest_on_normative_loan(
            opening_balance=100.0,
            qualifying_additions=0.0,
            surplus_funded_additions=0.0,
            repayment_depreciation=30.0,
            eblr_rate=0.10,
            depreciation_is_approved=False,
        )
        assert result["provisional"] is True
        assert "claimed depreciation" in result["provisional_reason"]


# ═══════════════════════════════════════════════════════════════════════
# Component C — Working Capital Interest
# ═══════════════════════════════════════════════════════════════════════

class TestWorkingCapitalInterest:
    """Tests for calculate_working_capital_interest (full spec version)."""

    def test_standard_case(self):
        """Normal WC with positive net balance."""
        result = calculate_working_capital_interest(
            approved_om_annual=120.0,          # 1 month = 10.0
            approved_revenue_from_sale=600.0,  # 2 months = (600/12)*2 = 100.0
            cash_security_deposit=50.0,
            eblr_rate=0.0915,
        )
        # Net WC = 10 + 100 + 0 - 50 - 0 = 60
        # Rate = 0.0915 + 0.02 = 0.1115
        # Interest = 60 × 0.1115 = 6.69
        assert result["om_one_month"] == 10.0
        assert result["receivables_two_months"] == 100.0
        assert result["net_working_capital"] == 60.0
        assert result["rate"] == pytest.approx(0.1115, abs=1e-4)
        assert result["interest_rs_lakhs"] == 6.69
        assert result["is_zero"] is False

    def test_sd_exceeds_wc(self):
        """Security deposit > working capital → interest = 0."""
        result = calculate_working_capital_interest(
            approved_om_annual=120.0,          # 10.0
            approved_revenue_from_sale=600.0,  # 100.0
            cash_security_deposit=200.0,       # exceeds 110
            eblr_rate=0.0915,
        )
        assert result["is_zero"] is True
        assert result["net_working_capital"] == 0.0
        assert result["interest_rs_lakhs"] == 0.0
        assert "exceeds" in result["zero_reason"]

    def test_two_months_receivables_formula(self):
        """Verify 2-month receivables = (revenue / 12) × 2."""
        result = calculate_working_capital_interest(
            approved_om_annual=0.0,
            approved_revenue_from_sale=1200.0,  # (1200/12)*2 = 200
            cash_security_deposit=0.0,
            eblr_rate=0.10,
        )
        assert result["receivables_two_months"] == 200.0

    def test_provisional_om(self):
        """When O&M is not approved, result is provisional."""
        result = calculate_working_capital_interest(
            approved_om_annual=120.0,
            approved_revenue_from_sale=600.0,
            cash_security_deposit=50.0,
            eblr_rate=0.0915,
            om_is_approved=False,
        )
        assert result["provisional"] is True
        assert "claimed O&M" in result["provisional_reason"]

    def test_other_deductions(self):
        """Additional deductions reduce net WC."""
        result = calculate_working_capital_interest(
            approved_om_annual=120.0,          # 10
            approved_revenue_from_sale=600.0,  # 100
            cash_security_deposit=50.0,
            other_deductions=20.0,
            eblr_rate=0.10,
        )
        # Net WC = 10 + 100 - 50 - 20 = 40
        assert result["net_working_capital"] == 40.0


# ═══════════════════════════════════════════════════════════════════════
# Component D — Interest on Security Deposits
# ═══════════════════════════════════════════════════════════════════════

class TestSecurityDepositInterest:
    """Tests for calculate_security_deposit_interest."""

    def test_standard_case(self):
        """Interest = opening × supply code rate."""
        result = calculate_security_deposit_interest(
            opening_balance=269.66,
            supply_code_rate=0.06,
        )
        # 269.66 × 0.06 = 16.18 (rounded to 2dp)
        assert result["interest_rs_lakhs"] == 16.18

    def test_zero_balance(self):
        """No security deposit → no interest."""
        result = calculate_security_deposit_interest(0.0, 0.06)
        assert result["interest_rs_lakhs"] == 0.0

    def test_negative_balance(self):
        """Negative balance (unusual) → no interest."""
        result = calculate_security_deposit_interest(-10.0, 0.06)
        assert result["interest_rs_lakhs"] == 0.0


# ═══════════════════════════════════════════════════════════════════════
# Component E — Bank Charge Classification
# ═══════════════════════════════════════════════════════════════════════

class TestBankChargeClassification:
    """Tests for classify_bank_charge."""

    def test_lc_charges(self):
        """Letter of credit → allowable."""
        result = classify_bank_charge(
            "Letter of Credit charges for power purchase", 3.50
        )
        assert result["classification"] == "LC_CHARGES"
        assert result["allowable"] is True

    def test_operational_bg(self):
        """Operational bank guarantee → allowable."""
        result = classify_bank_charge(
            "Bank guarantee for operations", 2.0
        )
        assert result["classification"] == "OPERATIONAL_BG"
        assert result["allowable"] is True

    def test_litigation_bg_by_description(self):
        """Supreme Court litigation BG → disallowed."""
        result = classify_bank_charge(
            "BG charges pursuant to Supreme Court order in Civil Appeal", 5.0
        )
        assert result["classification"] == "LITIGATION_BG"
        assert result["allowable"] is False

    def test_litigation_bg_by_firestore(self):
        """Firestore says litigation active + description has 'guarantee' → disallowed."""
        result = classify_bank_charge(
            "Bank guarantee renewal charges", 4.0,
            litigation_bg_active=True,
        )
        assert result["classification"] == "LITIGATION_BG"
        assert result["allowable"] is False

    def test_unclassifiable(self):
        """Vague description → needs clarification."""
        result = classify_bank_charge(
            "Miscellaneous banking fees", 1.5
        )
        assert result["classification"] == "UNCLASSIFIED"
        assert result["needs_clarification"] is True
        assert result["allowable"] is False


# ═══════════════════════════════════════════════════════════════════════
# Component F — Carrying Cost on Revenue Gaps
# ═══════════════════════════════════════════════════════════════════════

class TestCarryingCost:
    """Tests for calculate_carrying_cost."""

    def test_standard_gap(self):
        """Gap × retail TD rate = carrying cost."""
        result = calculate_carrying_cost(
            cumulative_gap=915.59,
            retail_td_rate=0.068,
            position_type="GAP",
        )
        # 915.59 × 0.068 = 62.26
        assert result["applicable"] is True
        assert result["carrying_cost_rs_lakhs"] == 62.26

    def test_surplus_not_applicable(self):
        """Surplus position → carrying cost = 0."""
        result = calculate_carrying_cost(
            cumulative_gap=500.0,
            retail_td_rate=0.068,
            position_type="SURPLUS",
        )
        assert result["applicable"] is False
        assert result["carrying_cost_rs_lakhs"] == 0.0

    def test_zero_gap(self):
        """Zero gap → not applicable."""
        result = calculate_carrying_cost(0.0, 0.068, "GAP")
        assert result["applicable"] is False
        assert result["carrying_cost_rs_lakhs"] == 0.0


# ═══════════════════════════════════════════════════════════════════════
# Component G — Notional Surplus Interest
# ═══════════════════════════════════════════════════════════════════════

class TestNotionalSurplusInterest:
    """Tests for calculate_notional_surplus_interest."""

    def test_standard_surplus(self):
        """Notional interest on full surplus."""
        result = calculate_notional_surplus_interest(
            cumulative_surplus=500.0,
            surplus_additions_this_year=0.0,
            retail_td_rate=0.065,
            position_type="SURPLUS",
        )
        # 500 × 0.065 = 32.5
        assert result["applicable"] is True
        assert result["notional_amount"] == 32.5
        assert result["additional_to_nti"] == 32.5  # licensee didn't claim

    def test_surplus_with_deduction(self):
        """Surplus reduced by additions deployed from surplus."""
        result = calculate_notional_surplus_interest(
            cumulative_surplus=500.0,
            surplus_additions_this_year=100.0,
            retail_td_rate=0.065,
            position_type="SURPLUS",
        )
        # Net base = 500 - 100 = 400
        # 400 × 0.065 = 26.0
        assert result["net_base"] == 400.0
        assert result["notional_amount"] == 26.0
        assert result["additional_to_nti"] == 26.0

    def test_licensee_claimed_partial(self):
        """Licensee claimed actual interest < notional → add difference."""
        result = calculate_notional_surplus_interest(
            cumulative_surplus=500.0,
            surplus_additions_this_year=0.0,
            retail_td_rate=0.065,
            position_type="SURPLUS",
            licensee_claimed_actual=20.0,
        )
        # Notional = 32.5, claimed = 20 → additional = 12.5
        assert result["notional_amount"] == 32.5
        assert result["additional_to_nti"] == 12.5

    def test_licensee_claimed_excess(self):
        """Licensee claimed ≥ notional → cap at notional, no additional."""
        result = calculate_notional_surplus_interest(
            cumulative_surplus=500.0,
            surplus_additions_this_year=0.0,
            retail_td_rate=0.065,
            position_type="SURPLUS",
            licensee_claimed_actual=40.0,
        )
        assert result["notional_amount"] == 32.5
        assert result["additional_to_nti"] == 0.0

    def test_gap_position_not_applicable(self):
        """GAP position → notional interest not applicable."""
        result = calculate_notional_surplus_interest(
            cumulative_surplus=500.0,
            surplus_additions_this_year=0.0,
            retail_td_rate=0.065,
            position_type="GAP",
        )
        assert result["applicable"] is False
        assert result["notional_amount"] == 0.0
