"""
Pytest tests for KSERC normative math functions.
=================================================

Each test uses known-good inputs and validates the deterministic outputs
to ensure no regressions in regulatory calculations.
"""

import pytest
from src.tools.normative_math import (
    calculate_distribution_loss_penalty,
    calculate_om_escalation,
    calculate_ronfa,
    impute_surplus_interest,
    calculate_revenue_gap_surplus,
    adjust_depreciation,
    calculate_interest_on_normative_loan,
    calculate_depreciation_90pct_cap,
    calculate_working_capital_interest,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. Distribution Loss Penalty Tests
# ═══════════════════════════════════════════════════════════════════════

class TestDistributionLossPenalty:
    """Tests for calculate_distribution_loss_penalty."""

    def test_no_excess_loss(self):
        """Actual loss ≤ target → zero penalty."""
        result = calculate_distribution_loss_penalty(
            actual_loss_pct=5.0,
            target_loss_pct=6.0,
            total_units_purchased_mu=100.0,
            avg_cost_per_unit=4.50,
        )
        assert result["excess_loss_pct"] == 0.0
        assert result["excess_units_mu"] == 0.0
        assert result["penalty_rs_lakhs"] == 0.0

    def test_equal_loss(self):
        """Actual loss == target → zero penalty."""
        result = calculate_distribution_loss_penalty(
            actual_loss_pct=6.0,
            target_loss_pct=6.0,
            total_units_purchased_mu=100.0,
            avg_cost_per_unit=4.50,
        )
        assert result["penalty_rs_lakhs"] == 0.0

    def test_excess_loss(self):
        """Actual 8.5% vs target 6% → 2.5% excess penalty."""
        result = calculate_distribution_loss_penalty(
            actual_loss_pct=8.5,
            target_loss_pct=6.0,
            total_units_purchased_mu=100.0,
            avg_cost_per_unit=4.50,
        )
        # excess = 2.5%, excess_units = 100 × 2.5/100 = 2.5 MU
        # penalty = 2.5 × 10 × 4.50 = 112.5 Lakhs
        assert result["excess_loss_pct"] == 2.5
        assert result["excess_units_mu"] == 2.5
        assert result["penalty_rs_lakhs"] == 112.5

    def test_small_excess(self):
        """Verify precision with fractional excess."""
        result = calculate_distribution_loss_penalty(
            actual_loss_pct=6.15,
            target_loss_pct=6.0,
            total_units_purchased_mu=50.0,
            avg_cost_per_unit=5.00,
        )
        # excess = 0.15%, excess_units = 50 × 0.15/100 = 0.075 MU
        # penalty = 0.075 × 10 × 5.00 = 3.75
        assert result["excess_loss_pct"] == 0.15
        assert result["excess_units_mu"] == 0.075
        assert result["penalty_rs_lakhs"] == 3.75


# ═══════════════════════════════════════════════════════════════════════
# 2. O&M Escalation Tests
# ═══════════════════════════════════════════════════════════════════════

class TestOMEscalation:
    """Tests for calculate_om_escalation (70:30 CPI/WPI formula)."""

    def test_basic_escalation(self):
        """Known CPI/WPI values → correct normative cap."""
        result = calculate_om_escalation(
            base_year_cost=100.0,
            cpi_current=330.0,
            cpi_previous=300.0,
            wpi_current=155.0,
            wpi_previous=150.0,
        )
        # CPI esc = (330−300)/300 = 0.1
        # WPI esc = (155−150)/150 = 0.033333
        # Blended  = 0.70 × 0.1 + 0.30 × 0.033333 = 0.07 + 0.01 = 0.08
        # Cap = 100 × 1.08 = 108.0
        assert result["cpi_escalation"] == pytest.approx(0.1, abs=1e-4)
        assert result["wpi_escalation"] == pytest.approx(0.033333, abs=1e-4)
        assert result["blended_escalation"] == pytest.approx(0.08, abs=1e-4)
        assert result["normative_cap_rs_lakhs"] == pytest.approx(108.0, abs=0.01)

    def test_zero_escalation(self):
        """No change in CPI/WPI → cap equals base cost."""
        result = calculate_om_escalation(
            base_year_cost=200.0,
            cpi_current=300.0,
            cpi_previous=300.0,
            wpi_current=150.0,
            wpi_previous=150.0,
        )
        assert result["blended_escalation"] == 0.0
        assert result["normative_cap_rs_lakhs"] == 200.0

    def test_negative_escalation(self):
        """Deflation scenario → cap below base cost."""
        result = calculate_om_escalation(
            base_year_cost=100.0,
            cpi_current=285.0,
            cpi_previous=300.0,
            wpi_current=145.0,
            wpi_previous=150.0,
        )
        # CPI esc = -0.05, WPI esc = -0.033333
        # Blended = 0.70 × (-0.05) + 0.30 × (-0.033333) = -0.035 + -0.01 = -0.045
        assert result["normative_cap_rs_lakhs"] == pytest.approx(95.5, abs=0.01)

    def test_zero_previous_raises(self):
        """Division by zero guard."""
        with pytest.raises(ValueError, match="Previous CPI/WPI cannot be zero"):
            calculate_om_escalation(100.0, 300.0, 0.0, 150.0, 150.0)

        with pytest.raises(ValueError, match="Previous CPI/WPI cannot be zero"):
            calculate_om_escalation(100.0, 300.0, 300.0, 150.0, 0.0)


# ═══════════════════════════════════════════════════════════════════════
# 3. Return on NFA Tests
# ═══════════════════════════════════════════════════════════════════════

class TestRoNFA:
    """Tests for calculate_ronfa."""

    def test_standard_ronfa(self):
        """Typical case with deductions."""
        result = calculate_ronfa(
            opening_nfa=1000.0,
            consumer_contributions=100.0,
            grants=200.0,
            normative_loan_assets=300.0,
        )
        # Eligible = 1000 - 100 - 200 - 300 = 400
        # RoNFA = 400 × 0.055 = 22.0
        assert result["eligible_base_rs_lakhs"] == 400.0
        assert result["ronfa_rs_lakhs"] == 22.0

    def test_negative_eligible_base(self):
        """Deductions exceed NFA → zero RoNFA."""
        result = calculate_ronfa(
            opening_nfa=100.0,
            consumer_contributions=50.0,
            grants=30.0,
            normative_loan_assets=80.0,
        )
        assert result["eligible_base_rs_lakhs"] == 0.0
        assert result["ronfa_rs_lakhs"] == 0.0

    def test_custom_rate(self):
        """Custom rate of return."""
        result = calculate_ronfa(
            opening_nfa=500.0,
            consumer_contributions=0.0,
            grants=0.0,
            normative_loan_assets=0.0,
            rate_of_return=0.10,
        )
        assert result["eligible_base_rs_lakhs"] == 500.0
        assert result["ronfa_rs_lakhs"] == 50.0


# ═══════════════════════════════════════════════════════════════════════
# 4. Imputed Surplus Interest Tests
# ═══════════════════════════════════════════════════════════════════════

class TestImputedSurplusInterest:
    """Tests for impute_surplus_interest."""

    def test_positive_surplus(self):
        """Standard surplus interest imputation."""
        result = impute_surplus_interest(
            accumulated_surplus=500.0,
            sbi_deposit_rate=0.065,
        )
        # 500 × 0.065 = 32.5
        assert result["imputed_interest_rs_lakhs"] == 32.5

    def test_zero_surplus(self):
        """No surplus → no interest."""
        result = impute_surplus_interest(0.0, 0.065)
        assert result["imputed_interest_rs_lakhs"] == 0.0

    def test_negative_surplus(self):
        """Negative surplus (gap) → no interest imputed."""
        result = impute_surplus_interest(-200.0, 0.065)
        assert result["imputed_interest_rs_lakhs"] == 0.0


# ═══════════════════════════════════════════════════════════════════════
# 5. Revenue Gap / Surplus Tests
# ═══════════════════════════════════════════════════════════════════════

class TestRevenueGapSurplus:
    """Tests for calculate_revenue_gap_surplus."""

    def test_surplus(self):
        result = calculate_revenue_gap_surplus(1000.0, 800.0)
        assert result["revenue_gap_surplus_rs_lakhs"] == 200.0
        assert result["position"] == "surplus"

    def test_gap(self):
        result = calculate_revenue_gap_surplus(800.0, 1000.0)
        assert result["revenue_gap_surplus_rs_lakhs"] == -200.0
        assert result["position"] == "gap"

    def test_breakeven(self):
        result = calculate_revenue_gap_surplus(500.0, 500.0)
        assert result["revenue_gap_surplus_rs_lakhs"] == 0.0
        assert result["position"] == "surplus"


# ═══════════════════════════════════════════════════════════════════════
# 6. Depreciation Adjustment Tests
# ═══════════════════════════════════════════════════════════════════════

class TestDepreciationAdjustment:
    """Tests for adjust_depreciation."""

    def test_partial_disallowance(self):
        result = adjust_depreciation(
            claimed_depreciation=100.0,
            depreciation_on_grant_funded_assets=20.0,
            depreciation_on_surplus_funded_assets=15.0,
        )
        assert result["disallowed_depreciation"] == 35.0
        assert result["approved_depreciation"] == 65.0

    def test_full_disallowance(self):
        """Disallowance exceeds claim → approved is zero."""
        result = adjust_depreciation(
            claimed_depreciation=30.0,
            depreciation_on_grant_funded_assets=20.0,
            depreciation_on_surplus_funded_assets=20.0,
        )
        assert result["approved_depreciation"] == 0.0

    def test_no_disallowance(self):
        result = adjust_depreciation(50.0, 0.0, 0.0)
        assert result["disallowed_depreciation"] == 0.0
        assert result["approved_depreciation"] == 50.0


# ═══════════════════════════════════════════════════════════════════════
# 7. Interest on Normative Loan Tests
# ═══════════════════════════════════════════════════════════════════════

class TestInterestOnNormativeLoan:
    """Tests for calculate_interest_on_normative_loan (updated to full spec)."""

    def test_standard_loan_calculation(self):
        """Basic normative loan interest with opening, additions, repayment."""
        result = calculate_interest_on_normative_loan(
            opening_balance=700.0,
            qualifying_additions=0.0,
            surplus_funded_additions=0.0,
            repayment_depreciation=100.0,
            eblr_rate=0.08,
        )
        # Closing = 700 - 100 = 600, Average = (700+600)/2 = 650
        # Interest = 650 × 0.08 = 52.0
        assert result["closing_balance"] == 600.0
        assert result["interest_rs_lakhs"] == 52.0

    def test_exhausted_loan(self):
        result = calculate_interest_on_normative_loan(
            opening_balance=50.0,
            qualifying_additions=0.0,
            surplus_funded_additions=0.0,
            repayment_depreciation=100.0,
            eblr_rate=0.10,
        )
        assert result["is_exhausted"] is True
        assert result["interest_rs_lakhs"] == 0.0


# ═══════════════════════════════════════════════════════════════════════
# 8. Depreciation 90% Cap Tests
# ═══════════════════════════════════════════════════════════════════════

class TestDepreciation90pctCap:
    """Tests for calculate_depreciation_90pct_cap."""

    def test_well_below_cap(self):
        """Current depreciation is well within 90% cap."""
        result = calculate_depreciation_90pct_cap(
            original_cost=1000.0,  # Max allowable = 900
            accumulated_depreciation=500.0,
            current_year_depreciation=100.0
        )
        assert result["approved_depreciation_rs_lakhs"] == 100.0
        assert result["disallowed_depreciation_rs_lakhs"] == 0.0
        assert result["capacity_remaining_rs_lakhs"] == 300.0

    def test_hitting_the_cap_partially(self):
        """Current depreciation partially exceeds the 90% cap limit."""
        result = calculate_depreciation_90pct_cap(
            original_cost=1000.0,  # Max allowable = 900
            accumulated_depreciation=850.0,
            current_year_depreciation=100.0
        )
        # Cap limits the allowed amount to 50
        assert result["approved_depreciation_rs_lakhs"] == 50.0
        assert result["disallowed_depreciation_rs_lakhs"] == 50.0
        assert result["capacity_remaining_rs_lakhs"] == 0.0

    def test_already_exceeded_cap(self):
        """If accumulated already hits 90%, nothing allowed this year."""
        result = calculate_depreciation_90pct_cap(
            original_cost=1000.0,  # Max allowable = 900
            accumulated_depreciation=900.0,
            current_year_depreciation=100.0
        )
        assert result["approved_depreciation_rs_lakhs"] == 0.0
        assert result["disallowed_depreciation_rs_lakhs"] == 100.0
        assert result["capacity_remaining_rs_lakhs"] == 0.0


# ═══════════════════════════════════════════════════════════════════════
# 9. Working Capital Interest Tests
# ═══════════════════════════════════════════════════════════════════════

class TestWorkingCapitalInterest:
    """Tests for calculate_working_capital_interest (updated to full spec)."""

    def test_standard_working_capital(self):
        result = calculate_working_capital_interest(
            approved_om_annual=120.0,              # 1 month = 10.0
            approved_revenue_from_sale=1200.0,     # 2 months = (1200/12)*2 = 200.0
            cash_security_deposit=10.0,
            maintenance_spares=10.0,               # explicit spares
            eblr_rate=0.07,                        # rate = 0.07 + 0.02 = 0.09
        )
        # Net WC = 10 + 200 + 10 - 10 = 210.0
        # Interest = 210.0 × 0.09 = 18.9
        assert result["net_working_capital"] == 210.0
        assert result["interest_rs_lakhs"] == 18.9

    def test_negative_working_capital(self):
        """Security deposits exceed WC → interest = 0."""
        result = calculate_working_capital_interest(
            approved_om_annual=120.0,              # 10.0
            approved_revenue_from_sale=1200.0,     # 200.0
            cash_security_deposit=300.0,
            eblr_rate=0.07,
        )
        assert result["net_working_capital"] == 0.0
        assert result["interest_rs_lakhs"] == 0.0
