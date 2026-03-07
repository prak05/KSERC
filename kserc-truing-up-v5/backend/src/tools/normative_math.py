"""
KSERC SDL Truing Up — Deterministic Math Tools
================================================

Pure-Python functions implementing KSERC regulatory formulas.
These must be called by agents; the LLM must NEVER perform arithmetic itself.

All monetary values are in Rs. Lakhs unless stated otherwise.
"""

from __future__ import annotations
from typing import Dict, Tuple


# ═══════════════════════════════════════════════════════════════════════
# 1. Distribution Loss Penalty
# ═══════════════════════════════════════════════════════════════════════

def calculate_distribution_loss_penalty(
    actual_loss_pct: float,
    target_loss_pct: float,
    total_units_purchased_mu: float,
    avg_cost_per_unit: float,
) -> Dict[str, float]:
    """
    If actual distribution loss exceeds the target, calculate penalty.

    Parameters
    ----------
    actual_loss_pct : float
        Actual distribution loss as percentage (e.g. 8.5 for 8.5%).
    target_loss_pct : float
        KSERC-approved target loss percentage.
    total_units_purchased_mu : float
        Total energy purchased in Million Units (MU).
    avg_cost_per_unit : float
        Average power purchase cost per unit (Rs./kWh).

    Returns
    -------
    dict with keys:
        excess_loss_pct, excess_units_mu, penalty_rs_lakhs
    """
    if actual_loss_pct <= target_loss_pct:
        return {
            "excess_loss_pct": 0.0,
            "excess_units_mu": 0.0,
            "penalty_rs_lakhs": 0.0,
        }

    excess_loss_pct = actual_loss_pct - target_loss_pct
    # excess_units in MU = total purchased × excess_loss / 100
    excess_units_mu = total_units_purchased_mu * (excess_loss_pct / 100.0)
    # 1 MU = 10 Lakh units; cost_per_unit is Rs./kWh
    # penalty in Rs. Lakhs = excess_units_mu × 10 × avg_cost_per_unit
    penalty_rs_lakhs = excess_units_mu * 10.0 * avg_cost_per_unit

    return {
        "excess_loss_pct": round(excess_loss_pct, 4),
        "excess_units_mu": round(excess_units_mu, 6),
        "penalty_rs_lakhs": round(penalty_rs_lakhs, 4),
    }


# ═══════════════════════════════════════════════════════════════════════
# 2. O&M Escalation (70:30 CPI/WPI Formula — Annexure-7)
# ═══════════════════════════════════════════════════════════════════════

def calculate_om_escalation(
    base_year_cost: float,
    cpi_current: float,
    cpi_previous: float,
    wpi_current: float,
    wpi_previous: float,
) -> Dict[str, float]:
    """
    Compute the normative O&M cap using the 70:30 CPI/WPI escalation formula.

    Formula:
        E_n = 0.70 × ((CPI_n − CPI_{n−1}) / CPI_{n−1})
            + 0.30 × ((WPI_n − WPI_{n−1}) / WPI_{n−1})
        Normative Cap = base_year_cost × (1 + E_n)

    Parameters
    ----------
    base_year_cost : float
        Approved O&M cost from the MYT base year (Rs. Lakhs).
    cpi_current : float
        Consumer Price Index for the current year.
    cpi_previous : float
        Consumer Price Index for the previous year.
    wpi_current : float
        Wholesale Price Index for the current year.
    wpi_previous : float
        Wholesale Price Index for the previous year.

    Returns
    -------
    dict with keys:
        cpi_escalation, wpi_escalation, blended_escalation,
        normative_cap_rs_lakhs
    """
    if cpi_previous == 0.0 or wpi_previous == 0.0:
        raise ValueError("Previous CPI/WPI cannot be zero.")

    cpi_esc = (cpi_current - cpi_previous) / cpi_previous
    wpi_esc = (wpi_current - wpi_previous) / wpi_previous
    blended = 0.70 * cpi_esc + 0.30 * wpi_esc
    normative_cap = base_year_cost * (1.0 + blended)

    return {
        "cpi_escalation": round(cpi_esc, 6),
        "wpi_escalation": round(wpi_esc, 6),
        "blended_escalation": round(blended, 6),
        "normative_cap_rs_lakhs": round(normative_cap, 4),
    }


# ═══════════════════════════════════════════════════════════════════════
# 3. Return on Net Fixed Assets (RoNFA)
# ═══════════════════════════════════════════════════════════════════════

def calculate_ronfa(
    opening_nfa: float,
    consumer_contributions: float,
    grants: float,
    normative_loan_assets: float,
    rate_of_return: float = 0.055,
) -> Dict[str, float]:
    """
    Calculate Return on NFA per Regulation 27(2).

    Eligible Base = Opening NFA − Consumer Contributions − Grants
                    − Normative Loan-funded Assets
    RoNFA = Eligible Base × Rate (default 5.5%)

    Parameters
    ----------
    opening_nfa : float
        Opening Net Fixed Assets (Rs. Lakhs).
    consumer_contributions : float
        Assets funded by consumer contributions (Rs. Lakhs).
    grants : float
        Assets funded by government grants (Rs. Lakhs).
    normative_loan_assets : float
        Assets financed through normative loans (Rs. Lakhs).
    rate_of_return : float
        Rate of return (default 5.5% = 0.055).

    Returns
    -------
    dict with keys:
        eligible_base_rs_lakhs, ronfa_rs_lakhs
    """
    eligible_base = (
        opening_nfa
        - consumer_contributions
        - grants
        - normative_loan_assets
    )
    # If eligible base is negative, RoNFA is zero
    if eligible_base < 0:
        eligible_base = 0.0

    ronfa = eligible_base * rate_of_return

    return {
        "eligible_base_rs_lakhs": round(eligible_base, 4),
        "ronfa_rs_lakhs": round(ronfa, 4),
    }


# ═══════════════════════════════════════════════════════════════════════
# 4. Imputed Interest on Accumulated Surplus
# ═══════════════════════════════════════════════════════════════════════

def impute_surplus_interest(
    accumulated_surplus: float,
    sbi_deposit_rate: float,
) -> Dict[str, float]:
    """
    Impute notional interest income on the licensee's accumulated
    regulatory surplus, per KSERC practice.

    Parameters
    ----------
    accumulated_surplus : float
        Accumulated regulatory surplus (Rs. Lakhs).
    sbi_deposit_rate : float
        SBI fixed deposit interest rate (e.g. 0.065 for 6.5%).

    Returns
    -------
    dict with keys:
        imputed_interest_rs_lakhs
    """
    if accumulated_surplus <= 0:
        return {"imputed_interest_rs_lakhs": 0.0}

    interest = accumulated_surplus * sbi_deposit_rate
    return {"imputed_interest_rs_lakhs": round(interest, 4)}


# ═══════════════════════════════════════════════════════════════════════
# 5. Revenue Gap / Surplus Computation
# ═══════════════════════════════════════════════════════════════════════

def calculate_revenue_gap_surplus(
    total_approved_revenue: float,
    total_approved_expenditure: float,
) -> Dict[str, float]:
    """
    Compute the net revenue position.

    Positive = surplus (revenue exceeds expenditure)
    Negative = gap (expenditure exceeds revenue)

    Returns
    -------
    dict with keys:
        revenue_gap_surplus_rs_lakhs, position ("surplus" | "gap")
    """
    gap_surplus = total_approved_revenue - total_approved_expenditure
    position = "surplus" if gap_surplus >= 0 else "gap"

    return {
        "revenue_gap_surplus_rs_lakhs": round(gap_surplus, 4),
        "position": position,
    }


# ═══════════════════════════════════════════════════════════════════════
# 6. Depreciation Adjustment (Grant / Surplus-Funded Assets)
# ═══════════════════════════════════════════════════════════════════════

def adjust_depreciation(
    claimed_depreciation: float,
    depreciation_on_grant_funded_assets: float,
    depreciation_on_surplus_funded_assets: float,
) -> Dict[str, float]:
    """
    Reduce claimed depreciation by the portion attributable to assets
    not funded by the licensee's own equity.

    Per Regulation 27(2): Depreciation is disallowed on assets funded
    by Government Grants or Accumulated Regulatory Surplus.

    Returns
    -------
    dict with keys:
        disallowed_depreciation, approved_depreciation
    """
    disallowed = (
        depreciation_on_grant_funded_assets
        + depreciation_on_surplus_funded_assets
    )
    approved = max(claimed_depreciation - disallowed, 0.0)

    return {
        "disallowed_depreciation": round(disallowed, 4),
        "approved_depreciation": round(approved, 4),
    }


# ═══════════════════════════════════════════════════════════════════════
# 7. Interest on Normative Loan
# ═══════════════════════════════════════════════════════════════════════

def calculate_interest_on_normative_loan(
    approved_capex: float,
    equity_ratio: float = 0.30,
    interest_rate: float = 0.08,
) -> Dict[str, float]:
    """
    Regulation 28: Calculate interest on normative loan.

    Normative loan is the portion of approved capital expenditure not
    funded by equity, consumer contributions, or grants. By default, 
    equity is considered 30%, so loan is 70%.

    Parameters
    ----------
    approved_capex : float
        Approved capital expenditure (Rs. Lakhs).
    equity_ratio : float
        Equity proportion (default 0.30).
    interest_rate : float
        Interest rate to apply (default 8% = 0.08).

    Returns
    -------
    dict with keys:
        normative_loan_rs_lakhs, interest_rs_lakhs
    """
    loan_portion = 1.0 - equity_ratio
    normative_loan = approved_capex * loan_portion
    interest = normative_loan * interest_rate

    return {
        "normative_loan_rs_lakhs": round(normative_loan, 4),
        "interest_rs_lakhs": round(interest, 4),
    }


# ═══════════════════════════════════════════════════════════════════════
# 8. Depreciation 90% Cap
# ═══════════════════════════════════════════════════════════════════════

def calculate_depreciation_90pct_cap(
    original_cost: float,
    accumulated_depreciation: float,
    current_year_depreciation: float,
) -> Dict[str, float]:
    """
    Regulation 27(4): Cap cumulative depreciation at 90% of original cost.

    Parameters
    ----------
    original_cost : float
        Original capital cost of the asset (Rs. Lakhs).
    accumulated_depreciation : float
        Depreciation accumulated until previous year (Rs. Lakhs).
    current_year_depreciation : float
        Claimed depreciation for the current year (Rs. Lakhs).

    Returns
    -------
    dict with keys:
        claimed_depreciation, approved_depreciation_rs_lakhs,
        disallowed_depreciation_rs_lakhs, capacity_remaining_rs_lakhs
    """
    if original_cost <= 0:
        return {
            "claimed_depreciation": round(current_year_depreciation, 4),
            "approved_depreciation_rs_lakhs": 0.0,
            "disallowed_depreciation_rs_lakhs": round(current_year_depreciation, 4),
            "capacity_remaining_rs_lakhs": 0.0
        }

    max_depreciation = original_cost * 0.90
    available_depreciation = max_depreciation - accumulated_depreciation

    if available_depreciation <= 0:
        approved = 0.0
    else:
        approved = min(current_year_depreciation, available_depreciation)

    disallowed = current_year_depreciation - approved
    
    # Just in case negative amounts are passed, ensure no negative disallowances
    if disallowed < 0:
        disallowed = 0.0

    return {
        "claimed_depreciation": round(current_year_depreciation, 4),
        "approved_depreciation_rs_lakhs": round(approved, 4),
        "disallowed_depreciation_rs_lakhs": round(disallowed, 4),
        "capacity_remaining_rs_lakhs": round(max(0.0, available_depreciation - approved), 4)
    }


# ═══════════════════════════════════════════════════════════════════════
# 9. Working Capital Interest
# ═══════════════════════════════════════════════════════════════════════

def calculate_working_capital_interest(
    om_expenses_annual: float,
    receivables_annual: float,
    security_deposits_held: float,
    historical_gfa: float = 0.0,
    fuel_cost_annual: float = 0.0,
    interest_rate: float = 0.09,
) -> Dict[str, float]:
    """
    Regulation 32: Compute normative interest on working capital.
    
    Working capital includes:
    - O&M expenses for 1 month
    - Receivables for 2 months
    - Cost of maintenance spares (1% of historical cost of GFA)
    - Fuel costs for 1 month (if applicable)
    LESS: Amount held as security deposits from consumers.

    Parameters
    ----------
    om_expenses_annual : float
        Annual Operations & Maintenance expenses (Rs. Lakhs).
    receivables_annual : float
        Annual expected revenue (Rs. Lakhs).
    security_deposits_held : float
        Security deposits held from consumers (Rs. Lakhs).
    historical_gfa : float
        Historical cost of Gross Fixed Assets (Rs. Lakhs). Default 0.
    fuel_cost_annual : float
        Annual fuel cost (Rs. Lakhs). Default 0.
    interest_rate : float
        Interest rate to apply (default 9% = 0.09).

    Returns
    -------
    dict with keys:
        working_capital_rs_lakhs, interest_on_working_capital_rs_lakhs
    """
    om_1_month = om_expenses_annual / 12.0
    receivables_2_months = (receivables_annual / 12.0) * 2.0
    fuel_1_month = fuel_cost_annual / 12.0
    maintenance_spares = historical_gfa * 0.01

    total_working_capital = (
        om_1_month 
        + receivables_2_months 
        + fuel_1_month 
        + maintenance_spares 
        - security_deposits_held
    )

    # Working capital cannot be negative for interest calculation
    if total_working_capital < 0:
        total_working_capital = 0.0

    interest = total_working_capital * interest_rate

    return {
        "working_capital_rs_lakhs": round(total_working_capital, 4),
        "interest_on_working_capital_rs_lakhs": round(interest, 4)
    }
