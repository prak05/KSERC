import logging
from typing import Dict, Any

logger = logging.getLogger("calculator")

# Actual blended KSERC O&M escalation rates (70% CPI + 30% WPI, finalized at truing-up)
# These are the ACTUAL rates confirmed in KSERC orders, not estimates.
# For years not listed, the default is 4.84% (the MYT base period rate).
ANNUAL_BLENDED_ESCALATION_RATES: Dict[str, float] = {
    "2018-19": 4.84,
    "2019-20": 4.84,
    "2020-21": 2.10,  # COVID-suppressed inflation
    "2021-22": 5.82,
    "2022-23": 7.60,  # High WPI year
    "2023-24": 3.14,  # Confirmed: KSERC FY 2023-24 blended rate
    "2024-25": 4.84,  # Estimate until confirmed
    "2025-26": 4.84,
    "2026-27": 4.84,
}


def get_escalation_rate(financial_year: str, licensee_baselines: Dict = None) -> float:
    """
    Returns the actual blended CPI/WPI escalation rate for a given financial year.
    If the licensee's MYT baselines file has a specific rate, that takes priority.
    """
    # Try the licensee-specific rate from baselines file first
    if licensee_baselines and "escalation_rates" in licensee_baselines:
        rate = licensee_baselines["escalation_rates"].get(financial_year)
        if rate is not None:
            logger.info(f"Using licensee-specific escalation rate for {financial_year}: {rate}%")
            return float(rate) / 100.0

    # Fall back to the global dictionary
    rate = ANNUAL_BLENDED_ESCALATION_RATES.get(financial_year, 4.84)
    logger.info(f"Using global escalation rate for {financial_year}: {rate}%")
    return float(rate) / 100.0


def apply_escalation(base_norm: float, base_year: str, target_year: str, licensee_baselines: Dict = None) -> float:
    """
    Escalates a base year norm to the target year using the correct blended CPI/WPI rates.
    This replaces the old single-rate compounding formula.
    """
    if base_year == target_year:
        return base_norm

    try:
        base_yr_int = int(base_year[:4])
        target_yr_int = int(target_year[:4])
    except (ValueError, IndexError):
        return base_norm

    if target_yr_int <= base_yr_int:
        return base_norm

    result = base_norm
    for yr in range(base_yr_int, target_yr_int):
        fy = f"{yr}-{str(yr + 1)[2:]}"
        rate = get_escalation_rate(fy, licensee_baselines)
        result = result * (1 + rate)

    logger.info(f"Escalated {base_norm} from {base_year} to {target_year}: {round(result, 2)}")
    return round(result, 2)


def evaluate_om_expense(component_name: str, claimed: float, myt_norm: float) -> Dict[str, Any]:
    """
    Deterministic rule for O&M expenses (Employee Cost, R&M, A&G).
    
    ZERO-CLAIM RULE: If claimed is 0.0, licensee made no claim. Approve 0.0.
    Otherwise: Allow lower of Actual (Claimed) or MYT Normative.
    """
    # Zero-claim rule — never give money that wasn't claimed
    if claimed == 0.0:
        return {
            "amount": 0.0,
            "rule_applied": "No claim made by Licensee. Approved as Nil.",
            "status": "No Claim"
        }

    if claimed <= myt_norm:
        return {
            "amount": claimed,
            "rule_applied": "Claimed amount is lower than or equal to MYT Norm. Approved in full.",
            "status": "Approved in full"
        }
    else:
        return {
            "amount": myt_norm,
            "rule_applied": f"Claimed amount of {claimed} exceeds MYT Norm of {myt_norm}. Restricted to normative level per KSERC Tariff Regulations 2021.",
            "status": "Reduced to Norm"
        }


def calculate_distribution_loss_penalty(
    target_loss_pct: float,
    actual_loss_pct: float,
    power_purchase_cost: float,
    total_energy_sales: float
) -> float:
    """
    Calculate gain/loss for overachieving/underachieving the target distribution loss.
    Returns: positive value = penalty to deduct from power purchase cost.
             negative value = gain to add to revenue/sharing.
    
    Formula: Penalty = Power Purchase Cost × (Excess Loss % / 100)
    """
    if actual_loss_pct <= target_loss_pct:
        # Efficiency gain — shared 50:50 with licensee and consumers (simplified: no deduction)
        logger.info(f"Distribution loss target met: actual={actual_loss_pct}%, target={target_loss_pct}%. No penalty.")
        return 0.0
    else:
        excess_loss_pct = actual_loss_pct - target_loss_pct
        penalty = power_purchase_cost * (excess_loss_pct / 100)
        logger.info(f"Distribution loss penalty: excess={excess_loss_pct:.2f}%, penalty={penalty:.2f} Lakhs")
        return round(penalty, 2)


def evaluate_financial_expense(component_name: str, claimed: float, myt_norm: float) -> Dict[str, Any]:
    """
    Deterministic rule for financial items (Interest on LT Loans, Interest on Consumer Deposits,
    Interest on Working Capital, Depreciation, Return on NFA).
    
    ZERO-CLAIM RULE: If claimed is 0.0, approve 0.0 (licensee made no claim).
    Otherwise: Allow lower of Actual or Normative (these are actual items — no over-approval).
    """
    # Zero-claim rule — never give money that wasn't claimed
    if claimed == 0.0:
        return {
            "amount": 0.0,
            "rule_applied": "No claim made by Licensee. Approved as Nil.",
            "status": "No Claim"
        }

    if claimed <= myt_norm or myt_norm == 0.0:
        return {
            "amount": claimed,
            "rule_applied": "Claimed amount is within approved limits.",
            "status": "Approved in full"
        }
    else:
        return {
            "amount": myt_norm,
            "rule_applied": f"Claimed amount of {claimed} restricted to approved MYT norm of {myt_norm}.",
            "status": "Reduced to Norm"
        }
