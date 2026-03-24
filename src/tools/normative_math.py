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
# 7. Interest on Normative Loan (KSERC Spec Part 4 Component B)
# ═══════════════════════════════════════════════════════════════════════

def calculate_interest_on_normative_loan(
    opening_balance: float,
    qualifying_additions: float,
    surplus_funded_additions: float,
    repayment_depreciation: float,
    eblr_rate: float,
    depreciation_is_approved: bool = True,
) -> Dict:
    """
    Full normative loan interest per KSERC Regulation 28.

    Calculation flow:
        Net Additions  = qualifying_additions - surplus_funded_additions
        Closing        = Opening + Net Additions - Repayment(=depreciation)
        If Closing ≤ 0 → interest = 0, store closing as 0
        Average        = (Opening + Closing) / 2
        Interest       = Average × SBI EBLR rate on April 1

    Parameters
    ----------
    opening_balance : float
        Prior year closing normative loan (from Firestore/order). Rs Lakhs.
    qualifying_additions : float
        Capital additions approved this year, own-funded only. Rs Lakhs.
    surplus_funded_additions : float
        Additions that were ordered to be met from regulatory surplus.
        These MUST be excluded from qualifying additions. Rs Lakhs.
    repayment_depreciation : float
        Approved depreciation for current year (= loan repayment). Rs Lakhs.
    eblr_rate : float
        SBI EBLR as on April 1 of the financial year (e.g. 0.0915 for 9.15%).
    depreciation_is_approved : bool
        False if using claimed depreciation because approved is not yet final.
        Sets provisional flag on the result.

    Returns
    -------
    dict with keys:
        opening_balance, qualifying_additions, excluded_surplus_additions,
        net_additions, repayment_depreciation, closing_balance,
        is_exhausted, average_balance, eblr_rate, interest_rs_lakhs,
        provisional, provisional_reason
    """
    net_additions = max(qualifying_additions - surplus_funded_additions, 0.0)
    closing = opening_balance + net_additions - repayment_depreciation

    is_exhausted = closing <= 0.0
    if is_exhausted:
        # Loan fully repaid — store zero, interest = zero
        stored_closing = 0.0
        average = 0.0
        interest = 0.0
    else:
        stored_closing = closing
        average = (opening_balance + closing) / 2.0
        interest = average * eblr_rate

    provisional = not depreciation_is_approved
    provisional_reason = (
        "Using claimed depreciation as repayment because approved depreciation "
        "is not yet final. Interest will be recalculated when depreciation is approved."
        if provisional else ""
    )

    return {
        "opening_balance": round(opening_balance, 2),
        "qualifying_additions": round(qualifying_additions, 2),
        "excluded_surplus_additions": round(surplus_funded_additions, 2),
        "net_additions": round(net_additions, 2),
        "repayment_depreciation": round(repayment_depreciation, 2),
        "closing_balance": round(stored_closing, 2),
        "raw_closing_balance": round(closing, 2),
        "is_exhausted": is_exhausted,
        "average_balance": round(average, 2),
        "eblr_rate": eblr_rate,
        "interest_rs_lakhs": round(interest, 2),
        "provisional": provisional,
        "provisional_reason": provisional_reason,
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
# 9. Working Capital Interest (KSERC Spec Part 4 Component C)
# ═══════════════════════════════════════════════════════════════════════

def calculate_working_capital_interest(
    approved_om_annual: float,
    approved_revenue_from_sale: float,
    cash_security_deposit: float,
    maintenance_spares: float = 0.0,
    other_deductions: float = 0.0,
    eblr_rate: float = 0.0915,
    om_is_approved: bool = True,
) -> Dict:
    """
    KSERC Working Capital Interest per Regulation 32.

    Working capital components:
      + O&M expenses for 1 month      = approved_om_annual / 12
      + Receivables for 2 months       = (approved_revenue / 12) × 2
      + Maintenance spares             = as provided (usually zero for small licensees)
      − Cash security deposit          = EXCLUDING bank guarantees
      − Other deductions               = any additional deductions from petition

    Rate = SBI EBLR on April 1 + exactly 2 percentage points
    If net working capital ≤ 0 → interest = 0

    Parameters
    ----------
    approved_om_annual : float
        Approved total O&M (employee + R&M + A&G) for the year. Rs Lakhs.
        Must be APPROVED O&M, not claimed. If not yet approved, use claimed
        and set om_is_approved=False.
    approved_revenue_from_sale : float
        Approved revenue from sale of power for the year. Rs Lakhs.
    cash_security_deposit : float
        Cash security deposits held from consumers (EXCLUDING bank guarantees).
        Rs Lakhs.
    maintenance_spares : float
        One-twelfth of average stores value. Usually 0 for small licensees.
    other_deductions : float
        Additional deductions some licensees apply (e.g. Technopark). Rs Lakhs.
    eblr_rate : float
        SBI EBLR on April 1 of financial year (e.g. 0.0915 for 9.15%).
        The function adds 2% to this automatically.
    om_is_approved : bool
        False if using claimed O&M. Sets provisional flag.

    Returns
    -------
    dict with keys:
        om_one_month, receivables_two_months, maintenance_spares,
        cash_security_deposit, other_deductions, net_working_capital,
        is_zero, zero_reason, rate, interest_rs_lakhs,
        provisional, provisional_reason
    """
    # Step 1: O&M one month
    om_one_month = approved_om_annual / 12.0

    # Step 2: Receivables — 2 months (explicitly: revenue / 12 × 2)
    receivables_two_months = (approved_revenue_from_sale / 12.0) * 2.0

    # Step 3–5: Build net working capital
    net_wc = (
        om_one_month
        + receivables_two_months
        + maintenance_spares
        - cash_security_deposit
        - other_deductions
    )

    # Step 7: Zero or negative check
    is_zero = net_wc <= 0.0
    if is_zero:
        zero_reason = (
            f"Security deposit of Rs.{cash_security_deposit:.2f} lakh exceeds "
            f"working capital requirement of Rs.{(om_one_month + receivables_two_months + maintenance_spares):.2f} lakh. "
            f"Net working capital = Rs.{net_wc:.2f} lakh. "
            f"Interest on working capital = zero."
        )
        net_wc_final = 0.0
        interest = 0.0
    else:
        zero_reason = ""
        net_wc_final = net_wc
        # Step 8: Rate = EBLR + exactly 2 percentage points
        rate = eblr_rate + 0.02
        # Step 9: Interest
        interest = net_wc_final * rate

    rate_applied = eblr_rate + 0.02

    provisional = not om_is_approved
    provisional_reason = (
        "Using claimed O&M as approved O&M is not yet final. "
        "Working capital interest will be recalculated when O&M is approved."
        if provisional else ""
    )

    return {
        "om_one_month": round(om_one_month, 2),
        "receivables_two_months": round(receivables_two_months, 2),
        "maintenance_spares": round(maintenance_spares, 2),
        "cash_security_deposit": round(cash_security_deposit, 2),
        "other_deductions": round(other_deductions, 2),
        "net_working_capital": round(net_wc_final, 2),
        "is_zero": is_zero,
        "zero_reason": zero_reason,
        "rate": rate_applied,
        "interest_rs_lakhs": round(interest, 2),
        "provisional": provisional,
        "provisional_reason": provisional_reason,
    }


# ═══════════════════════════════════════════════════════════════════════
# 10. Interest on Security Deposits (KSERC Spec Part 4 Component D)
# ═══════════════════════════════════════════════════════════════════════

def calculate_security_deposit_interest(
    opening_balance: float,
    supply_code_rate: float,
) -> Dict:
    """
    Interest on consumer security deposits per Kerala Electricity Supply Code.

    KSERC approves interest ONLY on the opening balance.
    NOT on closing or average balance.
    NOT on pro-rata for new deposits added during the year.

    The rate is the Kerala Electricity Supply Code rate,
    which is DIFFERENT from SBI EBLR and SBI retail TD rate.

    Parameters
    ----------
    opening_balance : float
        Security deposit balance at start of year (= prior year closing).
        From Firestore or previous KSERC order. Rs Lakhs.
    supply_code_rate : float
        Rate per Kerala Electricity Supply Code (e.g. 0.06 for 6%).

    Returns
    -------
    dict with keys:
        opening_balance, supply_code_rate, interest_rs_lakhs
    """
    if opening_balance <= 0:
        return {
            "opening_balance": 0.0,
            "supply_code_rate": supply_code_rate,
            "interest_rs_lakhs": 0.0,
        }

    interest = opening_balance * supply_code_rate

    return {
        "opening_balance": round(opening_balance, 2),
        "supply_code_rate": supply_code_rate,
        "interest_rs_lakhs": round(interest, 2),
    }


# ═══════════════════════════════════════════════════════════════════════
# 11. Carrying Cost on Revenue Gaps (KSERC Spec Part 4 Component F)
# ═══════════════════════════════════════════════════════════════════════

def calculate_carrying_cost(
    cumulative_gap: float,
    retail_td_rate: float,
    position_type: str = "GAP",
) -> Dict:
    """
    Carrying cost for accumulated revenue deficit (gap).

    Only applies when cumulative position = GAP (not SURPLUS).
    Rate = SBI retail term deposit rate on April 1 (NOT EBLR).

    Parameters
    ----------
    cumulative_gap : float
        Absolute value of cumulative revenue gap from previous order. Rs Lakhs.
    retail_td_rate : float
        SBI retail term deposit rate for 1 year on April 1 (e.g. 0.068 for 6.8%).
    position_type : str
        "GAP" or "SURPLUS". If SURPLUS, carrying cost = 0.

    Returns
    -------
    dict with keys:
        applicable, cumulative_gap_base, retail_td_rate,
        carrying_cost_rs_lakhs
    """
    applicable = position_type.upper() == "GAP" and cumulative_gap > 0

    if not applicable:
        return {
            "applicable": False,
            "cumulative_gap_base": 0.0,
            "retail_td_rate": retail_td_rate,
            "carrying_cost_rs_lakhs": 0.0,
        }

    carrying_cost = cumulative_gap * retail_td_rate

    return {
        "applicable": True,
        "cumulative_gap_base": round(cumulative_gap, 2),
        "retail_td_rate": retail_td_rate,
        "carrying_cost_rs_lakhs": round(carrying_cost, 2),
    }


# ═══════════════════════════════════════════════════════════════════════
# 12. Notional Interest on Accumulated Surplus (KSERC Spec Component G)
# ═══════════════════════════════════════════════════════════════════════
# IMPORTANT: THIS IS INCOME — NOT EXPENSE
# Do NOT add to interest expense total.
# This goes into non-tariff income calculation.

def calculate_notional_surplus_interest(
    cumulative_surplus: float,
    surplus_additions_this_year: float,
    retail_td_rate: float,
    position_type: str = "SURPLUS",
    licensee_claimed_actual: float = 0.0,
) -> Dict:
    """
    Notional interest income on accumulated regulatory surplus.

    Only applies when cumulative position = SURPLUS (not GAP).
    The base is reduced by any asset additions ordered to be met from surplus.

    Comparison with what licensee claimed:
    - If licensee claimed actual bank interest < notional → add difference to NTI
    - If licensee claimed ≥ notional → cap at notional
    - If licensee did not claim → add full notional to NTI

    Rate = SBI retail term deposit rate on April 1 (same as carrying cost).

    Parameters
    ----------
    cumulative_surplus : float
        Closing cumulative surplus from previous order. Rs Lakhs.
    surplus_additions_this_year : float
        Amount of surplus deployed for asset additions this year. Rs Lakhs.
    retail_td_rate : float
        SBI retail term deposit rate for 1 year on April 1.
    position_type : str
        "GAP" or "SURPLUS". If GAP, not applicable.
    licensee_claimed_actual : float
        What the licensee claimed as actual interest income on surplus. Rs Lakhs.

    Returns
    -------
    dict with keys:
        applicable, cumulative_surplus_base, less_surplus_additions,
        net_base, retail_td_rate, notional_amount,
        licensee_claimed_actual, additional_to_nti
    """
    applicable = position_type.upper() == "SURPLUS" and cumulative_surplus > 0

    if not applicable:
        return {
            "applicable": False,
            "cumulative_surplus_base": 0.0,
            "less_surplus_additions": 0.0,
            "net_base": 0.0,
            "retail_td_rate": retail_td_rate,
            "notional_amount": 0.0,
            "licensee_claimed_actual": licensee_claimed_actual,
            "additional_to_nti": 0.0,
        }

    net_base = max(cumulative_surplus - surplus_additions_this_year, 0.0)
    notional = net_base * retail_td_rate

    # Compare with what licensee claimed
    if licensee_claimed_actual <= 0:
        # Licensee did not claim → add full notional to NTI
        additional_to_nti = notional
    elif licensee_claimed_actual < notional:
        # Claimed less than notional → add the difference
        additional_to_nti = notional - licensee_claimed_actual
    else:
        # Claimed ≥ notional → cap at notional, no additional
        additional_to_nti = 0.0

    return {
        "applicable": True,
        "cumulative_surplus_base": round(cumulative_surplus, 2),
        "less_surplus_additions": round(surplus_additions_this_year, 2),
        "net_base": round(net_base, 2),
        "retail_td_rate": retail_td_rate,
        "notional_amount": round(notional, 2),
        "licensee_claimed_actual": round(licensee_claimed_actual, 2),
        "additional_to_nti": round(additional_to_nti, 2),
    }


# ═══════════════════════════════════════════════════════════════════════
# 13. Bank Charge Classification (KSERC Spec Part 4 Component E)
# ═══════════════════════════════════════════════════════════════════════

# Signal words for each classification
_LC_SIGNALS = [
    "letter of credit", "lc ", "l.c.", "power purchase",
    "secure monthly bills", "cost of purchase",
]
_OPERATIONAL_BG_SIGNALS = [
    "bank guarantee for operations", "performance guarantee",
    "bank guarantee", "bg charges", "b.g. charges",
]
_LITIGATION_BG_SIGNALS = [
    "supreme court", "hon'ble supreme court", "aptel",
    "appellate tribunal", "civil appeal", "slp",
    "special leave petition", "interim order directed",
    "pursuant to appeal", "pending outcome", "pending final orders",
]


def classify_bank_charge(
    description: str,
    amount: float,
    litigation_bg_active: bool = False,
) -> Dict:
    """
    Classify a bank charge item per KSERC interest spec Component E.

    Classification priority:
      1. Litigation BG → DISALLOWED (if description matches OR Firestore says active)
      2. Letter of Credit → ALLOWABLE
      3. Operational BG → ALLOWABLE
      4. Unclassifiable → CLARIFICATION_NEEDED

    Parameters
    ----------
    description : str
        Text description of the bank charge from petition.
    amount : float
        Amount in Rs Lakhs.
    litigation_bg_active : bool
        Whether Firestore shows active litigation BG for this licensee.

    Returns
    -------
    dict with keys:
        description, amount, classification, allowable,
        reason, needs_clarification
    """
    desc_lower = description.lower().strip()

    # Test 1: Litigation BG — check first (highest disallowance risk)
    is_litigation = any(sig in desc_lower for sig in _LITIGATION_BG_SIGNALS)
    if is_litigation or (litigation_bg_active and "guarantee" in desc_lower):
        return {
            "description": description,
            "amount": round(amount, 2),
            "classification": "LITIGATION_BG",
            "allowable": False,
            "reason": (
                f"Bank guarantee charges of Rs.{amount:.2f} lakh relate to "
                f"litigation. Commission consistently disallows these charges "
                f"pending outcome of case. Amount disallowed."
            ),
            "needs_clarification": False,
        }

    # Test 2: Letter of Credit
    is_lc = any(sig in desc_lower for sig in _LC_SIGNALS)
    if is_lc:
        return {
            "description": description,
            "amount": round(amount, 2),
            "classification": "LC_CHARGES",
            "allowable": True,
            "reason": "Letter of Credit charges for power purchase — approved as claimed.",
            "needs_clarification": False,
        }

    # Test 3: Operational BG (non-litigation)
    is_operational = any(sig in desc_lower for sig in _OPERATIONAL_BG_SIGNALS)
    if is_operational:
        return {
            "description": description,
            "amount": round(amount, 2),
            "classification": "OPERATIONAL_BG",
            "allowable": True,
            "reason": "Operational bank guarantee charges — approved as claimed.",
            "needs_clarification": False,
        }

    # Test 4: Cannot classify
    return {
        "description": description,
        "amount": round(amount, 2),
        "classification": "UNCLASSIFIED",
        "allowable": False,
        "reason": (
            f"Bank charges of Rs.{amount:.2f} lakh described as '{description}'. "
            f"Please clarify whether this is for letter of credit, operational "
            f"bank guarantee, or related to any court proceedings or appeals."
        ),
        "needs_clarification": True,
    }
