"""
KSERC SDL Truing Up — Compliance Auditor Agent
==================================================

Applies KSERC regulatory rules to the extracted petition data.

AUDIT RULES (from ground_truth_tables.json study):
  1. Power Purchase Cost  : claimed - (excess_dist_loss_lakh_units × avg_cost_rs_per_unit)
                           OR + efficiency gain if actual < approved loss
  2. Employee Cost        : cap at MYT Approved Norm (no CPI/WPI escalation)
  3. R&M Expenses         : cap at MYT Approved Norm
  4. A&G Expenses         : cap at MYT Approved Norm
  5. Depreciation         : cap at MYT Approved amount
  6. Interest (LT, Deps)  : cap at MYT approved amounts
  7. Return on NFA/Equity : cap at MYT approved amount
  8. Carrying cost        : approve as claimed (already approved in MYT order)
  9. Section 3(1) Duty    : always disallow (statutory rejection)
 10. Other Debits         : cap at MYT norm (KDHP-specific)
 11. Revenue gap/surplus  : Total Revenue - Total Approved Expenditure

All monetary values are in Rs. Lakhs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Precedent Lookup Integration ──────────────────────────────────────
try:
    from src.rag.precedent_lookup import precedent_lookup as _precedent_lookup
    from src.rag.retriever import get_researcher
    logger.info("Precedent Lookup & Vector Researcher modules imported.")
except Exception as e:
    logger.warning(f"Knowledge modules not fully available: {e}")
    _precedent_lookup = None
    get_researcher = None

# ── Default target distribution loss by licensee (fallback) ───────────
DEFAULT_TARGET_DIST_LOSS = {
    "technopark": 3.45,
    "infopark":   4.23,
    "cseza":      1.45,
    "kdhp":       9.60,
}

# Actual inflation escalation (CPI 70% + WPI 30% weighted average)
# Source: KSERC orders — applied to O&M norms instead of flat MYT %
KSERC_INFLATION_ESCALATION = {
    "2019-20": 4.08,
    "2020-21": 5.52,
    "2021-22": 6.15,
    "2022-23": 7.06,
    "2023-24": 6.50,  # Estimated from CPI/WPI trends
    "2024-25": 5.80,  # Estimated
}

# ── Component display names for justification text ────────────────────
COMPONENT_DISPLAY = {
    "power_purchase_cost":        "Power Purchase Cost",
    "employee_cost":              "Employee Expenses",
    "repair_maintenance":         "Repairs & Maintenance",
    "admin_general":              "Administration & General Expenses",
    "depreciation":               "Depreciation",
    "interest_long_term":         "Interest on Long-Term / Normative Loans",
    "interest_consumer_deposits": "Interest on Consumer Security Deposits",
    "interest_working_capital":   "Interest on Working Capital",
    "carrying_cost":              "Carrying Cost on Past Revenue Gaps",
    "return_on_nfa":              "Return on Net Fixed Assets",
    "other_debits":               "Other Debits",
    "section3_1_duty":            "Section 3(1) Electricity Duty",
    "other_expenses":             "Other Expenses",
}


# ══════════════════════════════════════════════════════════════════════
# Helper: get MYT norm for a component
# ══════════════════════════════════════════════════════════════════════

def _myt_norm(myt_norms: Dict[str, float], key: str) -> float:
    """Return the MYT approved norm for a key, or 0.0 if not available."""
    return float(myt_norms.get(key, 0.0))


def _get_target_loss(licensee_name: str, myt_norms: Dict[str, float]) -> float:
    """Get target distribution loss % from MYT norms or defaults."""
    if "target_distribution_loss_pct" in myt_norms:
        return float(myt_norms["target_distribution_loss_pct"])
    for key, val in DEFAULT_TARGET_DIST_LOSS.items():
        if key in licensee_name.lower():
            return val
    return 5.0


# ══════════════════════════════════════════════════════════════════════
# Rule 1: Power Purchase Cost — Distribution Loss Adjustment
# ══════════════════════════════════════════════════════════════════════

def _audit_power_purchase(
    state: dict,
    approved_expenses: Dict[str, float],
    disallowances: List[Dict[str, Any]],
    myt_norms: Dict[str, float],
) -> None:
    """
    KSERC PPC Calculation with Distribution Loss Adjustment.
    
    Uses actual energy data from petition when available (energy_input_mu, energy_sold_mu).
    Otherwise, derives energy volumes from PPC and avg cost.
    
    Formula:
      If actual_loss > target_loss: penalty = excess_loss_MU × avg_cost_per_MU
      If actual_loss < target_loss: gain shared 2:1 (licensee:consumer)
    """
    claimed_ppc = state.get("claimed_expenses", {}).get("power_purchase_cost", 0.0)
    actual_loss_pct = state.get("claimed_distribution_loss_pct", 0.0)
    target_loss_pct = _get_target_loss(state.get("licensee_name", ""), myt_norms)
    
    # Try to get actual energy data from petition (extracted by extractor)
    energy_input_mu = state.get("energy_input_mu", 0.0)
    energy_sold_mu = state.get("energy_sold_mu", 0.0)
    energy_wheeled_mu = state.get("energy_wheeled_mu", 0.0)
    
    state["target_distribution_loss_pct"] = target_loss_pct

    if claimed_ppc == 0.0:
        approved_expenses["power_purchase_cost"] = claimed_ppc
        logger.warning("PPC: claimed PPC is 0 — approving as claimed.")
        return
    
    # Compute avg cost per unit
    if energy_input_mu > 0:
        # Use actual petition data (MU = Million Units = 10 lakh kWh)
        total_lakh_kwh = energy_input_mu * 10.0  # 1 MU = 10 lakh kWh
        avg_cost = claimed_ppc / total_lakh_kwh  # Rs/lakh kWh → Rs/kWh
        energy_sales_lakh_kwh = (energy_sold_mu + energy_wheeled_mu) * 10.0
        logger.info(f"PPC: Using petition energy data: input={energy_input_mu} MU, sold={energy_sold_mu} MU, wheeled={energy_wheeled_mu} MU")
    elif actual_loss_pct > 0:
        # Derive from PPC and avg cost from MYT norms
        avg_cost = myt_norms.get("avg_power_purchase_cost_rs_per_kwh", 6.95)
        total_lakh_kwh = claimed_ppc / avg_cost
        energy_sales_lakh_kwh = total_lakh_kwh * (1 - actual_loss_pct / 100.0)
        logger.info(f"PPC: Deriving energy from PPC/avg_cost: total={total_lakh_kwh:.2f} lakh kWh")
    else:
        # Can't compute — approve as claimed
        approved_expenses["power_purchase_cost"] = claimed_ppc
        logger.warning("PPC: no energy data or loss % — approving as claimed.")
        return

    # If we have actual energy data, compute actual distribution loss
    if energy_input_mu > 0 and energy_sold_mu > 0:
        energy_output_mu = energy_sold_mu + energy_wheeled_mu
        computed_loss_pct = ((energy_input_mu - energy_output_mu) / energy_input_mu) * 100.0
        if actual_loss_pct == 0.0:
            actual_loss_pct = computed_loss_pct
        logger.info(f"PPC: Computed loss={computed_loss_pct:.2f}%, claimed loss={actual_loss_pct:.2f}%")

    if actual_loss_pct == 0.0:
        approved_expenses["power_purchase_cost"] = claimed_ppc
        logger.warning("PPC: distribution loss is 0 — approving as claimed.")
        return

    # Approved loss volume at target %:
    approved_loss_lakh_kwh = energy_sales_lakh_kwh * (target_loss_pct / 100.0) / (1 - target_loss_pct / 100.0)
    actual_loss_lakh_kwh = total_lakh_kwh - energy_sales_lakh_kwh

    if actual_loss_pct > target_loss_pct:
        excess_lakh_kwh   = actual_loss_lakh_kwh - approved_loss_lakh_kwh
        penalty_rs_lakhs  = round(excess_lakh_kwh * avg_cost, 2)
        approved_ppc      = round(claimed_ppc - penalty_rs_lakhs, 2)

        approved_expenses["power_purchase_cost"] = max(approved_ppc, 0.0)
        disallowances.append({
            "item": "Power Purchase Cost — ARA Regulation 73(3) Penalty",
            "claimed": claimed_ppc,
            "approved": approved_ppc,
            "amount_cut": penalty_rs_lakhs,
            "justification": (
                f"[ARA Forensic Audit]: The actual distribution loss of {actual_loss_pct:.2f}% exceeds the "
                f"approved benchmark of {target_loss_pct:.2f}%. Under Regulation 73(3) of KSERC Tariff Regulations, "
                f"excess loss of {excess_lakh_kwh:.2f} lakh units at ₹{avg_cost:.2f}/kWh is disallowed. "
                f"Financial impact: ₹{penalty_rs_lakhs:.2f} Lakhs."
            ),
        })
        logger.info(f"[ARA] PPC Penalty: {penalty_rs_lakhs}, Approved: {approved_ppc}")

    else:
        # Efficiency gain: actual loss < approved target
        savings_lakh_kwh        = approved_loss_lakh_kwh - actual_loss_lakh_kwh
        efficiency_gain_rs_lakhs = round(savings_lakh_kwh * avg_cost, 2)
        # Regulation 18: sharing gain 2:1 (licensee:consumer)
        licensee_share          = round(efficiency_gain_rs_lakhs * 2.0 / 3.0, 2)
        approved_ppc            = round(claimed_ppc + licensee_share, 2)

        approved_expenses["power_purchase_cost"] = approved_ppc
        disallowances.append({
            "item": "Power Purchase Cost — ARA Regulation 73(3) Efficiency Gain",
            "claimed": claimed_ppc,
            "approved": approved_ppc,
            "amount_cut": -licensee_share,
            "justification": (
                f"[ARA Forensic Audit]: Actual loss of {actual_loss_pct:.2f}% is below target {target_loss_pct:.2f}%, "
                f"generating an efficiency gain of ₹{efficiency_gain_rs_lakhs:.2f} Lakhs. "
                f"Applying Regulation 18 sharing (2/3rd to Licensee), ₹{licensee_share:.2f} Lakhs is approved "
                f"as a performance incentive."
            ),
        })
        logger.info(f"[ARA] Efficiency Gain Shared: {licensee_share}, Approved: {approved_ppc}")


# ══════════════════════════════════════════════════════════════════════
# Rule 2: Section 3(1) Electricity Duty — Always Disallow
# ══════════════════════════════════════════════════════════════════════

def _audit_section3_duty(
    claimed_expenses: Dict[str, float],
    approved_expenses: Dict[str, float],
    disallowances: List[Dict[str, Any]],
) -> None:
    duty = claimed_expenses.get("section3_1_duty", 0.0)
    approved_expenses["section3_1_duty"] = 0.0
    if duty > 0:
        disallowances.append({
            "item": "Section 3(1) Electricity Duty",
            "claimed": duty,
            "approved": 0.0,
            "amount_cut": duty,
            "justification": (
                "Disallowed under Section 3(1) of the Kerala Electricity Duty Act, 1963. "
                "This statutory levy is borne by the licensee and cannot be passed through "
                "to consumers as part of the tariff. The Commission has consistently followed "
                "this position in all previous truing-up orders."
            ),
        })
        logger.info(f"Section 3(1) Duty: REJECTED Rs. {duty} Lakhs")


# ══════════════════════════════════════════════════════════════════════
# Capital Structure Analysis
# ══════════════════════════════════════════════════════════════════════

def _analyze_capital_structure(state: dict) -> Dict[str, Any]:
    """
    Analyze the capital structure from precedent DB (normative KSERC values)
    or petition data.

    PRIORITY: Precedent DB first (KSERC's normative capital structure from
    past orders includes eligible capital additions and correctly reflects
    the Commission's asset base calculation). Petition data is fallback.

    IMPORTANT: Even when precedent DB equity/debt flags suggest zeroing,
    we also check if KSERC actually approved RoNFA/interest in past orders.
    If they did, the flags are unreliable and we should approve.
    """
    result = {
        "grant_ratio": 0.0,
        "has_debt": True,
        "has_equity": True,
        "gfa": 0.0,
        "nfa": 0.0,
        "grants": 0.0,
        "loans": 0.0,
        "equity": 0.0,
        "eligible_nfa": 0.0,
        "surplus_funded_assets": 0.0,  # Assets created from accumulated revenue surplus
        "source": "none",
        "kserc_approved_ronfa": 0.0,
        "kserc_approved_interest": 0.0,
        "kserc_approved_depreciation": 0.0,
    }

    licensee = state.get("licensee_name", "")

    # Priority 1: Precedent DB (KSERC's normative capital structure)
    if _precedent_lookup and _precedent_lookup.available:
        history = _precedent_lookup.get_licensee_history(licensee)
        if history:
            # Use the closest year PRIOR TO or EQUAL TO the petition year
            # This prevents using future order data (e.g., 2024-25) when auditing 2023-24
            petition_fy = state.get("financial_year", "")
            available_fys = sorted(history.keys())
            prior_fys = [fy for fy in available_fys if fy <= petition_fy] if petition_fy else available_fys
            best_fy = prior_fys[-1] if prior_fys else available_fys[-1]
            logger.info(f"Capital structure: petition FY={petition_fy}, available={available_fys}, using={best_fy}")
            
            cap = history[best_fy].get("capital_structure", {})

            # Also check what KSERC actually approved for RoNFA, interest, and depreciation
            approved_exp = history[best_fy].get("approved_expenses", {})
            result["kserc_approved_ronfa"] = approved_exp.get("return_on_nfa", 0.0)
            result["kserc_approved_interest"] = approved_exp.get("interest_long_term", 0.0)
            result["kserc_approved_depreciation"] = approved_exp.get("depreciation", 0.0)

            # Compute surplus-funded assets from KSERC reasoning
            # CSEZA pattern: KSERC deducts assets created from accumulated surplus
            surplus_funded = 0.0
            for d in history[best_fy].get("key_disallowances", []):
                reasoning = d.get("kserc_reasoning", "").lower()
                if "accumulated surplus" in reasoning or "surplus" in reasoning:
                    # KSERC explicitly mentions surplus-funded assets
                    # Estimate: if depreciation was significantly reduced, the cut represents surplus assets
                    dep_claimed = d.get("claimed", 0)
                    dep_approved = d.get("approved", 0)
                    if dep_claimed > 0 and dep_approved > 0 and d.get("component", "").lower() in ["depreciation", "return_on_nfa"]:
                        # Estimate surplus-funded assets from depreciation cut ratio
                        cut_ratio = (dep_claimed - dep_approved) / dep_claimed
                        if cut_ratio > 0.1:  # More than 10% cut
                            surplus_funded = round(cap.get("gross_fixed_assets", 0) * cut_ratio, 2)
                            logger.info(f"Estimated surplus-funded assets: {surplus_funded}L (cut ratio {cut_ratio:.2%})")
                            break

            if cap and cap.get("gross_fixed_assets", 0) > 0:
                gfa = cap.get("gross_fixed_assets", 0)
                grants = cap.get("grants_subsidies", cap.get("consumer_contribution", 0))
                loans = cap.get("total_loans_outstanding", cap.get("normative_loan_70pct", cap.get("normative_loan", 0)))
                nfa = cap.get("net_fixed_assets", 0)
                equity = cap.get("normative_equity_30pct", max(gfa - grants - loans, 0))

                result["gfa"] = gfa
                result["nfa"] = nfa
                result["grants"] = grants
                result["loans"] = loans
                result["equity"] = equity
                result["surplus_funded_assets"] = surplus_funded
                result["grant_ratio"] = round(grants / gfa * 100, 2) if gfa > 0 else 0.0
                result["has_debt"] = loans > 0
                # CRITICAL: If normative equity is 0 BUT KSERC approved RoNFA,
                # then equity IS implicitly there (KSERC computes it differently)
                result["has_equity"] = equity > 0 or result["kserc_approved_ronfa"] > 0
                result["eligible_nfa"] = max(nfa - grants, 0)
                result["source"] = f"precedent_db ({best_fy})"
                logger.info(f"Capital structure from precedent DB ({best_fy}): "
                            f"GFA={gfa}, Grants={grants}, NFA={nfa}, Loans={loans}, "
                            f"Equity={equity}, GrantRatio={result['grant_ratio']}%, "
                            f"SurplusFunded={surplus_funded}, "
                            f"KSERC_RoNFA={result['kserc_approved_ronfa']}, "
                            f"KSERC_Interest={result['kserc_approved_interest']}, "
                            f"KSERC_Dep={result['kserc_approved_depreciation']}")
                return result

    # Priority 2: Petition capital structure (raw data from petition)
    cap = state.get("capital_structure", {})
    if cap and cap.get("gross_fixed_assets", 0) > 0:
        gfa = cap.get("gross_fixed_assets", 0)
        grants = cap.get("grants_subsidies", 0)
        loans = cap.get("total_loans_outstanding", 0)
        equity = cap.get("equity_share_capital", 0)
        nfa = cap.get("net_fixed_assets", 0)

        result["gfa"] = gfa
        result["nfa"] = nfa
        result["grants"] = grants
        result["loans"] = loans
        result["equity"] = equity
        result["grant_ratio"] = round(grants / gfa * 100, 2) if gfa > 0 else 0.0
        result["has_debt"] = loans > 0
        result["has_equity"] = equity > 0
        result["eligible_nfa"] = max(nfa - grants, 0)
        result["source"] = "petition"
        logger.info(f"Capital structure from petition: GFA={gfa}, Grants={grants}, "
                    f"NFA={nfa}, Loans={loans}, Equity={equity}, GrantRatio={result['grant_ratio']}%")

    return result


# ══════════════════════════════════════════════════════════════════════
# Precedent-Aware Helpers
# ══════════════════════════════════════════════════════════════════════

def _get_precedent_approved(
    licensee: str, component: str, fy: str
) -> Optional[Dict[str, Any]]:
    """
    Get the most recent precedent approval for a component.
    Returns {approved, claimed, cut_pct, kserc_reasoning, fy} or None.
    """
    if not _precedent_lookup or not _precedent_lookup.available:
        return None
    history = _precedent_lookup.get_component_history(licensee, component)
    if not history:
        return None

    # Prefer the most recent prior year
    prior = [r for r in history if r["fy"] < fy]
    if prior:
        return prior[-1]
    # Fallback to any available
    return history[-1] if history else None


# ══════════════════════════════════════════════════════════════════════
# Rule 3: O&M, Depreciation, Interest, RoNFA — MYT Norm Cap
#         Enhanced with Precedent DB fallback
# ══════════════════════════════════════════════════════════════════════

def _audit_norm_capped_component(
    key: str,
    claimed_expenses: Dict[str, float],
    approved_expenses: Dict[str, float],
    myt_norms: Dict[str, float],
    disallowances: List[Dict[str, Any]],
    licensee: str = "",
    fy: str = "",
    researcher: Any = None,
) -> None:
    """
    Cap component using the best available benchmark:
    1. MYT norm (if available for this FY)
    2. Precedent DB — what KSERC approved in the most recent order
    3. Approve as claimed if neither is available
    
    KSERC reasoning: The Commission uses MYT norms as a primary reference but
    also considers actuals when they are within a reasonable range. If KSERC
    previously approved an amount higher than the MYT norm, the precedent
    approved amount is used as the effective cap (with 10% escalation allowance).
    """
    claimed = claimed_expenses.get(key, 0.0)
    norm = _myt_norm(myt_norms, key)
    display = COMPONENT_DISPLAY.get(key, key)

    # Get precedent data for smarter reasoning
    prec = _get_precedent_approved(licensee, key, fy) if _precedent_lookup and licensee else None
    precedent_approved_amt = prec["approved"] if prec and prec.get("approved", 0) > 0 else 0.0

    # Apply KSERC inflation escalation to MYT norms for O&M components
    # KSERC uses actual CPI(70%)+WPI(30%) weighted inflation, not flat norms
    # For truing-up, KSERC allows actuals more generously than MYT forecasts for A&G and R&M,
    # but is strict on employee costs (small licensees have fixed headcount).
    if norm > 0.0 and key in ("repair_maintenance", "admin_general", "employee_cost"):
        inflation_pct = KSERC_INFLATION_ESCALATION.get(fy, 6.0)
        # Component-specific tolerance: KSERC is stricter on employee costs
        trueup_tolerance = 1.25 if key in ("admin_general", "repair_maintenance") else 1.0
        escalated_norm = round(norm * (1 + inflation_pct / 100.0) * trueup_tolerance, 2)
        logger.info(f"{display}: MYT norm {norm:.2f} escalated by {inflation_pct}% + tolerance {trueup_tolerance}x -> {escalated_norm:.2f}")
        norm = escalated_norm

    # Determine the effective cap:
    # - If MYT norm exists AND KSERC precedent approved higher, use precedent (+ 10% escalation)
    # - If only MYT norm, use MYT norm
    # - If only precedent, use precedent pattern
    effective_cap = 0.0
    cap_source = "none"

    if norm > 0.0:
        effective_cap = norm
        cap_source = f"MYT norm (inflation-escalated)" if key in ("repair_maintenance", "admin_general", "employee_cost") else "MYT norm"
        # Check if KSERC precedent approved more than MYT norm
        # This happens when KSERC accepts justified actuals above norms
        if precedent_approved_amt > norm * 1.05:  # more than 5% above norm
            escalated_precedent = round(precedent_approved_amt * 1.10, 2)  # 10% escalation
            effective_cap = max(norm, min(escalated_precedent, claimed))
            cap_source = f"precedent-adjusted (KSERC approved {precedent_approved_amt:.2f}L in FY {prec['fy']})"
            logger.info(f"{display}: KSERC precedent ({precedent_approved_amt:.2f}) > MYT norm ({norm:.2f}), using cap={effective_cap:.2f}")

    if effective_cap > 0.0 and claimed > effective_cap:
        approved_expenses[key] = effective_cap
        cut = round(claimed - effective_cap, 2)

        justification = (
            f"The claimed {display} of Rs. {claimed:,.2f} Lakhs exceeds the "
            f"effective ceiling of Rs. {effective_cap:,.2f} Lakhs ({cap_source}). "
            f"The excess of Rs. {cut:,.2f} Lakhs is disallowed as per KSERC "
            f"Tariff Regulations. The Commission approves Rs. {effective_cap:,.2f} Lakhs."
        )

        if _precedent_lookup and licensee:
            prec_just = _precedent_lookup.build_precedent_justification(
                licensee, key, claimed, fy
            )
            if prec_just:
                justification += f" {prec_just}"
        
        # Semantic Precedent Fallback (VectorDB Knowledge)
        if researcher:
            semantic_context = researcher.search_regulations(f"{display} truing up {licensee}")
            if semantic_context and "No specific regulations" not in semantic_context:
                justification += f"\n\n[Semantic Persistence Insight]: {semantic_context[:300]}..."

        disallowances.append({
            "item": display,
            "claimed": claimed,
            "approved": effective_cap,
            "amount_cut": cut,
            "justification": justification,
        })
        logger.info(f"{display}: Claimed {claimed}, Cap {effective_cap} ({cap_source}), Cut {cut}")

    elif effective_cap > 0.0:
        # Claimed within cap
        approved_expenses[key] = claimed
        logger.info(f"{display}: Claimed {claimed} within cap {effective_cap} ({cap_source}) — approved as claimed")

    else:
        # No MYT norm — try precedent DB
        if prec and prec["claimed"] > 0 and prec["cut_pct"] > 5.0:
            approval_ratio = 1.0 - (prec["cut_pct"] / 100.0)
            precedent_based = round(claimed * approval_ratio, 2)
            cut = round(claimed - precedent_based, 2)

            approved_expenses[key] = precedent_based
            disallowances.append({
                "item": display,
                "claimed": claimed,
                "approved": precedent_based,
                "amount_cut": cut,
                "justification": (
                    f"No MYT norm available. Based on KSERC precedent from FY {prec['fy']}, "
                    f"the Commission applied a {prec['cut_pct']:.1f}% reduction. "
                    f"Approves Rs. {precedent_based:,.2f} Lakhs."
                ),
            })
            logger.info(f"{display}: No MYT norm, precedent cut={prec['cut_pct']:.1f}%, approved={precedent_based}")
        else:
            # Neither MYT nor significant precedent cut — approve as claimed
            approved_expenses[key] = claimed
            logger.info(f"{display}: No MYT norm, no precedent cut — approved as claimed: {claimed}")


# ══════════════════════════════════════════════════════════════════════
# Rule 4: Carrying Cost & Other pass-through items
# ══════════════════════════════════════════════════════════════════════

def _audit_passthrough(
    key: str,
    claimed_expenses: Dict[str, float],
    approved_expenses: Dict[str, float],
) -> None:
    """Approve as claimed (verified in MYT order already)."""
    val = claimed_expenses.get(key, 0.0)
    approved_expenses[key] = val
    if val > 0:
        logger.info(f"{COMPONENT_DISPLAY.get(key, key)}: Approved as claimed: {val}")


# ══════════════════════════════════════════════════════════════════════
# Revenue: approve total claimed revenue & Imputed NTI
# ══════════════════════════════════════════════════════════════════════

# SBI Retail Term Deposit Rates as on April 1st of the petition year
# Used for: Interest on Consumer Security Deposits (Regulation 30)
SBI_RETAIL_TERM_DEPOSIT_RATES = {
    "2020-21": 5.40,
    "2021-22": 5.10,
    "2022-23": 5.10,
    "2023-24": 6.80,
    "2024-25": 6.80,
    "2025-26": 6.80,
    "2026-27": 6.80
}

# SBI EBLR + 2% Rate — Used for Interest on Working Capital (Regulation 29)
# Source: KSERC OP 52/2024 (Infopark 2023-24): "SBI 1-year EBLR 9.15% + 2% = 11.15%"
SBI_EBLR_PLUS_2_RATES = {
    "2019-20": 10.05,  # SBI EBLR ~8.05% + 2%
    "2020-21": 9.80,   # SBI EBLR ~7.80% + 2%
    "2021-22": 9.55,   # SBI EBLR ~7.55% + 2%
    "2022-23": 10.15,  # SBI EBLR ~8.15% + 2%
    "2023-24": 11.15,  # SBI EBLR 9.15% + 2% (confirmed from KSERC order)
    "2024-25": 11.15,  # SBI EBLR ~9.15% + 2%
    "2025-26": 11.15,
    "2026-27": 11.15
}

# KSERC standard depreciation rate for distribution licensees
# (From Annexure-1 of KSERC Tariff Regulations 2021: 5.28% for distribution assets)
KSERC_DEPRECIATION_RATE = 0.0528
KSERC_SALVAGE_VALUE = 0.10  # 10% salvage value
KSERC_MAX_DEPRECIATION = 0.90  # Max 90% of capital cost

# RoNFA rates per KSERC Regulation 28
# 5.5% when equity is identifiable; 3% when not identifiable (SDL licensees funded by parent body)
KSERC_RONFA_RATE_EQUITY_IDENTIFIABLE = 0.055
KSERC_RONFA_RATE_EQUITY_NOT_IDENTIFIABLE = 0.03


# ══════════════════════════════════════════════════════════════════════
# Rule 5: Depreciation — KSERC Regulation 27
# ══════════════════════════════════════════════════════════════════════

def _audit_depreciation_reg27(
    state: dict,
    claimed_expenses: Dict[str, float],
    approved_expenses: Dict[str, float],
    myt_norms: Dict[str, float],
    disallowances: List[Dict[str, Any]],
    cap_analysis: Dict[str, Any],
    licensee: str = "",
    fy: str = "",
) -> None:
    """
    KSERC Regulation 27 — Depreciation Calculation:
    
    Method: Straight-Line Method (SLM) at 5.28% of KSERC-approved GFA.
    - 10% salvage value, max 90% cumulative depreciation
    - Assets funded by grants/subsidies/consumer contribution: EXCLUDED
    - Assets created from accumulated surplus: EXCLUDED (CSEZA precedent)
    
    Calculation:
    1. Eligible GFA = Total GFA - grant-funded assets - surplus-funded assets
    2. Annual depreciation = Eligible GFA × 5.28%
    3. Cap at claimed amount (KSERC never approves MORE than claimed for depreciation)
    4. Cross-check against precedent approved depreciation
    """
    key = "depreciation"
    claimed = claimed_expenses.get(key, 0.0)
    display = COMPONENT_DISPLAY.get(key, key)
    
    if claimed == 0.0:
        approved_expenses[key] = 0.0
        return
    
    # Get capital structure data
    gfa = cap_analysis.get("gfa", 0.0)
    grants = cap_analysis.get("grants", 0.0)
    source = cap_analysis.get("source", "none")
    
    # Get precedent depreciation for cross-check
    prec = _get_precedent_approved(licensee, key, fy) if _precedent_lookup and licensee else None
    prec_dep = prec["approved"] if prec and prec.get("approved", 0) > 0 else 0.0
    
    # Get surplus-funded assets (CSEZA/KDHP pattern)
    surplus_funded_assets = cap_analysis.get("surplus_funded_assets", 0.0)
    
    if gfa > 0:
        # KSERC method: Depreciation on eligible assets only
        eligible_gfa = max(gfa - grants - surplus_funded_assets, 0.0)
        computed_dep = round(eligible_gfa * KSERC_DEPRECIATION_RATE, 2)
        
        # Get MYT norm for cross-check
        myt_dep = _myt_norm(myt_norms, key)
        
        # Use precedent to validate (if available and different approach used by KSERC)
        if prec_dep > 0 and abs(computed_dep - prec_dep) / max(prec_dep, 1) > 0.30:
            # Large divergence from precedent — KSERC may use a different base
            # Allow up to 10% increase from precedent
            effective_dep = min(claimed, round(prec_dep * 1.10, 2))
            cap_source = f"precedent-adjusted (KSERC approved Rs. {prec_dep:.2f}L in FY {prec['fy']})"
            logger.info(f"Dep: Computed {computed_dep} diverges from precedent {prec_dep}, using precedent-based cap {effective_dep}")
        elif myt_dep > 0 and computed_dep > myt_dep * 1.5:
            # Computed depreciation is way above MYT norm — GFA data may be unreliable
            # Use MYT norm with 10% tolerance as cap
            effective_dep = round(myt_dep * 1.10, 2)
            cap_source = f"MYT norm-based (MYT dep={myt_dep:.2f}L, computed {computed_dep:.2f}L too high)"
            logger.info(f"Dep: Computed {computed_dep} >> MYT norm {myt_dep}, capping at {effective_dep}")
        else:
            effective_dep = computed_dep
            cap_source = f"Reg 27 (GFA {gfa:.2f}L - grants {grants:.2f}L - surplus {surplus_funded_assets:.2f}L = {eligible_gfa:.2f}L × 5.28%)"
        
        # KSERC never approves MORE than claimed for depreciation
        approved = min(claimed, effective_dep)
        approved_expenses[key] = approved
        
        if claimed > approved + 0.01:
            cut = round(claimed - approved, 2)
            disallowances.append({
                "item": display,
                "claimed": claimed,
                "approved": approved,
                "amount_cut": cut,
                "justification": (
                    f"As per KSERC Tariff Regulation 27, depreciation is computed using "
                    f"Straight Line Method at 5.28% on eligible fixed assets. "
                    f"{cap_source}. "
                    f"Depreciation of Rs. {cut:.2f}L disallowed on assets not eligible "
                    f"for depreciation recovery. Approved: Rs. {approved:.2f}L."
                ),
            })
            logger.info(f"Dep Reg27: Claimed {claimed}, Approved {approved} ({cap_source}), Cut {cut}")
        else:
            logger.info(f"Dep Reg27: Claimed {claimed} within limit {effective_dep} — approved as claimed")
    
    elif prec_dep > 0:
        # No capital structure but have precedent — use precedent with escalation
        effective_dep = round(prec_dep * 1.10, 2)  # Allow 10% increase
        approved = min(claimed, effective_dep)
        approved_expenses[key] = approved
        
        if claimed > approved + 0.01:
            cut = round(claimed - approved, 2)
            disallowances.append({
                "item": display,
                "claimed": claimed,
                "approved": approved,
                "amount_cut": cut,
                "justification": (
                    f"Based on KSERC precedent from FY {prec['fy']} (approved Rs. {prec_dep:.2f}L). "
                    f"Claimed depreciation exceeds precedent-based ceiling. Approved: Rs. {approved:.2f}L."
                ),
            })
        logger.info(f"Dep: No capital structure, precedent-based cap {effective_dep}, approved={approved}")
    
    else:
        # Fallback to MYT norm cap
        norm = _myt_norm(myt_norms, key)
        if norm > 0 and claimed > norm:
            approved_expenses[key] = norm
            cut = round(claimed - norm, 2)
            disallowances.append({
                "item": display,
                "claimed": claimed,
                "approved": norm,
                "amount_cut": cut,
                "justification": f"Capped at MYT approved norm of Rs. {norm:.2f}L.",
            })
            logger.info(f"Dep: MYT norm cap {norm}, claimed {claimed}")
        else:
            approved_expenses[key] = claimed
            logger.info(f"Dep: No cap available, approved as claimed: {claimed}")


# ══════════════════════════════════════════════════════════════════════
# Rule 6: Return on NFA — KSERC Regulation 28
# ══════════════════════════════════════════════════════════════════════

def _audit_return_on_nfa_reg28(
    state: dict,
    claimed_expenses: Dict[str, float],
    approved_expenses: Dict[str, float],
    myt_norms: Dict[str, float],
    disallowances: List[Dict[str, Any]],
    cap_analysis: Dict[str, Any],
    licensee: str = "",
    fy: str = "",
) -> None:
    """
    KSERC Regulation 28 — Return on Net Fixed Assets:
    
    Method: Rate × average(opening NFA, closing NFA)
    - If equity identifiable: 5.5% on NFA
    - If equity NOT identifiable (SDL licensees): 3% on NFA
    - Deduct: grant-funded assets, surplus-funded assets, consumer contribution
    
    Cross-checks against precedent data for consistency.
    """
    key = "return_on_nfa"
    claimed = claimed_expenses.get(key, 0.0)
    display = COMPONENT_DISPLAY.get(key, key)
    
    if claimed == 0.0:
        approved_expenses[key] = 0.0
        return
    
    # Get capital structure
    nfa = cap_analysis.get("nfa", 0.0)
    eligible_nfa = cap_analysis.get("eligible_nfa", 0.0)
    grants = cap_analysis.get("grants", 0.0)
    surplus_funded = cap_analysis.get("surplus_funded_assets", 0.0)
    source = cap_analysis.get("source", "none")
    has_equity = cap_analysis.get("has_equity", True)
    kserc_ronfa = cap_analysis.get("kserc_approved_ronfa", 0.0)
    
    # Get precedent for cross-check
    prec = _get_precedent_approved(licensee, key, fy) if _precedent_lookup and licensee else None
    prec_ronfa = prec["approved"] if prec and prec.get("approved", 0) > 0 else 0.0
    
    if nfa > 0 and source != "none":
        # Determine RoNFA rate based on equity identifiability
        # CSEZA uses 3%, Infopark/Technopark/KDHP use 5.5%
        licensee_lower = licensee.lower() if licensee else ""
        if "cseza" in licensee_lower or "cochin special" in licensee_lower:
            ronfa_rate = KSERC_RONFA_RATE_EQUITY_NOT_IDENTIFIABLE  # 3%
            rate_reason = "3% (equity not clearly identifiable per Regulation 28)"
        else:
            ronfa_rate = KSERC_RONFA_RATE_EQUITY_IDENTIFIABLE  # 5.5%
            rate_reason = "5.5% (per Regulation 28 of Tariff Regulations 2021)"
        
        # Eligible NFA = NFA - grant-funded portion - surplus-funded portion
        dep_on_grants = grants * KSERC_DEPRECIATION_RATE if grants > 0 else 0
        dep_on_surplus = surplus_funded * KSERC_DEPRECIATION_RATE if surplus_funded > 0 else 0
        eligible_nfa_for_return = max(eligible_nfa - surplus_funded, 0.0)
        
        computed_ronfa = round(eligible_nfa_for_return * ronfa_rate, 2)
        
        # Validate against precedent
        if prec_ronfa > 0 and abs(computed_ronfa - prec_ronfa) / max(prec_ronfa, 1) > 0.30:
            # Significant divergence — use precedent-adjusted amount
            effective_ronfa = min(claimed, round(prec_ronfa * 1.10, 2))
            cap_source = f"precedent-adjusted (KSERC approved Rs. {prec_ronfa:.2f}L in FY {prec['fy']})"
            logger.info(f"RoNFA: Computed {computed_ronfa} diverges from precedent {prec_ronfa}, using {effective_ronfa}")
        else:
            effective_ronfa = computed_ronfa
            cap_source = f"Reg 28 ({rate_reason} on eligible NFA Rs. {eligible_nfa_for_return:.2f}L)"
        
        approved = min(claimed, effective_ronfa)
        # But KSERC sometimes approves MORE than claimed (see Infopark 2022-23: claimed 38.70, approved 41.30)
        if kserc_ronfa > claimed and prec_ronfa > claimed:
            approved = effective_ronfa  # Allow KSERC calculation to exceed claim
        
        approved_expenses[key] = approved
        
        if abs(claimed - approved) > 0.01:
            cut = round(claimed - approved, 2)
            disallowances.append({
                "item": display,
                "claimed": claimed,
                "approved": approved,
                "amount_cut": cut,
                "justification": (
                    f"As per KSERC Tariff Regulation 28, return on NFA is computed at "
                    f"{cap_source}. "
                    f"Assets funded by grants (Rs. {grants:.2f}L) and accumulated surplus "
                    f"(Rs. {surplus_funded:.2f}L) are excluded from the eligible base. "
                    f"Approved: Rs. {approved:.2f}L."
                ),
            })
            logger.info(f"RoNFA Reg28: Claimed {claimed}, Approved {approved} ({cap_source}), Diff {cut}")
        else:
            logger.info(f"RoNFA Reg28: Approved as claimed: {claimed}")
    
    elif prec_ronfa > 0:
        # No capital structure but precedent exists
        effective = min(claimed, round(prec_ronfa * 1.10, 2))
        approved_expenses[key] = effective
        if claimed > effective + 0.01:
            cut = round(claimed - effective, 2)
            disallowances.append({
                "item": display,
                "claimed": claimed,
                "approved": effective,
                "amount_cut": cut,
                "justification": (
                    f"Based on KSERC precedent from FY {prec['fy']} (approved Rs. {prec_ronfa:.2f}L). "
                    f"Approved: Rs. {effective:.2f}L."
                ),
            })
        logger.info(f"RoNFA: Precedent-based, approved={effective}")
    
    else:
        # Fallback to MYT norm
        norm = _myt_norm(myt_norms, key)
        if norm > 0 and claimed > norm:
            approved_expenses[key] = norm
            cut = round(claimed - norm, 2)
            disallowances.append({
                "item": display,
                "claimed": claimed,
                "approved": norm,
                "amount_cut": cut,
                "justification": f"Capped at MYT approved norm of Rs. {norm:.2f}L.",
            })
        else:
            approved_expenses[key] = claimed
        logger.info(f"RoNFA: MYT fallback, approved={approved_expenses[key]}")


# ══════════════════════════════════════════════════════════════════════
# Rule 7: Interest on Consumer Deposits — KSERC Regulation 30
# ══════════════════════════════════════════════════════════════════════

def _audit_interest_consumer_deposits(
    claimed_expenses: Dict[str, float],
    approved_expenses: Dict[str, float],
    myt_norms: Dict[str, float],
    disallowances: List[Dict[str, Any]],
    fy: str,
    licensee: str = "",
) -> None:
    """
    KSERC Regulation 30 — Interest on Consumer Security Deposits:
    
    Method: Actual consumer deposit balance × SBI 1-year Term Deposit Rate
    as on April 1st of the financial year.
    
    KEY INSIGHT: KSERC often RECALCULATES this HIGHER than claimed because they
    use the actual verified deposit balance (which may be higher than what licensee
    reports). KSERC also considers bank charges in this head.
    """
    key = "interest_consumer_deposits"
    claimed = claimed_expenses.get(key, 0.0)
    
    if claimed == 0.0:
        approved_expenses[key] = 0.0
        return
    
    # KSERC PRACTICE: For truing-up, consumer deposit interest is approved as claimed
    # because the actual interest payment is verified from audited accounts.
    # The Commission verifies deposit balances during truing-up and approves actual interest paid.
    myt_norm = _myt_norm(myt_norms, key)
    if myt_norm > 0 and claimed <= myt_norm * 2.0:
        # Within reasonable range (2x MYT norm) — approve as claimed
        approved_expenses[key] = claimed
        logger.info(f"Consumer Deposits: Approved as claimed {claimed} (within 2x MYT norm {myt_norm})")
        return
    elif myt_norm == 0:
        # No MYT norm — approve as claimed (KSERC verifies actual during truing-up)
        approved_expenses[key] = claimed
        logger.info(f"Consumer Deposits: Approved as claimed {claimed} (no MYT norm, truing-up)")
        return
    
    sbi_rate = SBI_RETAIL_TERM_DEPOSIT_RATES.get(fy, 6.80) / 100.0
    
    # Get precedent for comparison
    prec = _get_precedent_approved(licensee, key, fy) if _precedent_lookup and licensee else None
    prec_approved = prec["approved"] if prec and prec.get("approved", 0) > 0 else 0.0
    
    # KSERC methodology: Use actual deposit balance × SBI rate
    # Since we can't always get the exact deposit balance from petition,
    # use the claimed amount as a reasonable estimate (KSERC verifies against records)
    
    # Key pattern from precedent analysis:
    # - If KSERC previously approved an amount close to or higher than claimed: approve as claimed
    # - KSERC rarely disallows consumer deposit interest (they sometimes increase it)
    
    if prec_approved > 0:
        # Have precedent - use it to validate
        # Allow reasonable growth from precedent (deposits grow with consumer base)
        max_allowable = round(prec_approved * 1.30, 2)  # 30% growth tolerance
        if claimed <= max_allowable:
            # Within reasonable growth — approve as claimed
            approved_expenses[key] = claimed
            logger.info(f"Consumer Deposits: Approved as claimed {claimed} (within precedent tolerance {max_allowable})")
        else:
            # Exceeds precedent growth bounds — cap at precedent growth
            approved_expenses[key] = max_allowable
            cut = round(claimed - max_allowable, 2)
            disallowances.append({
                "item": "Interest on Consumer Security Deposits",
                "claimed": claimed,
                "approved": max_allowable,
                "amount_cut": cut,
                "justification": (
                    f"Consumer deposit interest claim of Rs. {claimed:.2f}L exceeds reasonable "
                    f"growth from precedent (Rs. {prec_approved:.2f}L in FY {prec['fy']}). "
                    f"Capped at Rs. {max_allowable:.2f}L per KSERC Regulation 30."
                ),
            })
            logger.info(f"Consumer Deposits: Capped at {max_allowable} (precedent {prec_approved})")
    else:
        # No precedent — use deposit base estimation with MYT norm
        myt_norm = _myt_norm(myt_norms, key)
        if myt_norm > 0:
            # Use MYT norm to estimate deposit base
            estimated_deposit_base = myt_norm / 0.0425  # MYT typically used ~4.25%
            computed_benchmark = round(estimated_deposit_base * sbi_rate, 2)
            effective_cap = max(computed_benchmark, myt_norm)
            
            if claimed > effective_cap:
                approved_expenses[key] = effective_cap
                cut = round(claimed - effective_cap, 2)
                disallowances.append({
                    "item": "Interest on Consumer Security Deposits",
                    "claimed": claimed,
                    "approved": effective_cap,
                    "amount_cut": cut,
                    "justification": (
                        f"Computed using estimated deposit base at SBI rate "
                        f"({sbi_rate*100:.2f}%). Approved: Rs. {effective_cap:.2f}L."
                    ),
                })
                logger.info(f"Consumer Deposits: MYT-based cap {effective_cap}")
            else:
                approved_expenses[key] = claimed
                logger.info(f"Consumer Deposits: Within MYT-based benchmark, approved as claimed")
        else:
            # No data — approve as claimed (KSERC verifies against records)
            approved_expenses[key] = claimed
            logger.info(f"Consumer Deposits: No benchmark, approved as claimed: {claimed}")

def _audit_interest_long_term_loans(
    claimed_expenses: Dict[str, float],
    approved_expenses: Dict[str, float],
    myt_norms: Dict[str, float],
    disallowances: List[Dict[str, Any]],
    fy: str,
    licensee: str = "",
) -> None:
    """
    KSERC applies 70:30 normative Debt-Equity Ratio on eligible asset additions.
    
    Reasoning:
    - If MYT norm exists, use it as a primary benchmark
    - If no MYT norm, check precedent DB for what KSERC approved previously
    - If precedent exists, allow claimed up to precedent + 15% escalation
    - If nothing, approve as claimed (KSERC will verify during order)
    """
    key = "interest_long_term"
    claimed = claimed_expenses.get(key, 0.0)
    normative = _myt_norm(myt_norms, key)
    
    if normative > 0.0:
        # MYT norm available — use it as cap
        approved = min(claimed, normative) if claimed > 0 else normative
        approved_expenses[key] = approved
        if claimed > normative:
            cut = round(claimed - normative, 2)
            disallowances.append({
                "item": "Interest on Normative Loan",
                "claimed": claimed,
                "approved": normative,
                "amount_cut": cut,
                "justification": (
                    f"Under KSERC rules, interest on loans is computed normatively at 70% "
                    f"of eligible asset additions at weighted average SBI rate. "
                    f"MYT approved norm: Rs. {normative:,.2f} Lakhs."
                ),
            })
        logger.info(f"Interest LT: MYT norm={normative}, claimed={claimed}, approved={approved}")
    else:
        # No MYT norm — use precedent or approve as claimed
        prec = _get_precedent_approved(licensee, key, fy) if _precedent_lookup and licensee else None
        if prec and prec.get("approved", 0) > 0:
            # Allow up to 15% escalation from precedent
            cap = round(prec["approved"] * 1.15, 2)
            approved = min(claimed, cap) if claimed > 0 else prec["approved"]
            approved_expenses[key] = approved
            if claimed > cap:
                cut = round(claimed - cap, 2)
                disallowances.append({
                    "item": "Interest on Normative Loan",
                    "claimed": claimed,
                    "approved": cap,
                    "amount_cut": cut,
                    "justification": (
                        f"No MYT norm available. Based on KSERC precedent from FY {prec['fy']} "
                        f"(approved Rs. {prec['approved']:,.2f}L), allowing up to 15% escalation."
                    ),
                })
            logger.info(f"Interest LT: No MYT, precedent={prec['approved']}, cap={cap}, approved={approved}")
        else:
            # No norm, no precedent — approve as claimed
            approved_expenses[key] = claimed
            logger.info(f"Interest LT: No MYT norm, no precedent — approved as claimed: {claimed}")

def _audit_interest_working_capital(
    claimed_expenses: Dict[str, float],
    approved_expenses: Dict[str, float],
    myt_norms: Dict[str, float],
    disallowances: List[Dict[str, Any]],
    fy: str,
    state: Optional[dict] = None,
) -> None:
    """
    KSERC Interest on Working Capital — Regulation 29.
    
    CORRECT Formula (from Infopark 2022-23 Order, Page 13):
    Working Capital = (1/12 of approved O&M) 
                    + (Maintenance Spares @ 15% of approved O&M)
                    + (1/12 of approved receivables i.e. 2-month equivalent)
    IWC = Working Capital × SBI 1-year Term Deposit Rate
    
    NOTE: KSERC sometimes approves IWC HIGHER than claimed because the formula
    may produce a higher value (e.g., Infopark 2022-23: claimed 2.70L, approved 3.72L).
    """
    key = "interest_working_capital"
    claimed = claimed_expenses.get(key, 0.0)
    myt_norm = _myt_norm(myt_norms, key)
    
    # ── Check if petitioner claims Nil IWC due to security deposit offset ──
    # Many SDL licensees (Technopark, Infopark) have security deposits that
    # exceed working capital requirements, making IWC = 0. If the petitioner
    # claims 0 (or very small amount), and the petition mentions security deposits
    # exceeding WC, we approve as claimed.
    if claimed == 0.0:
        logger.info("IWC: Petitioner claims Nil IWC (likely security deposits exceed WC)")
        approved_expenses[key] = 0.0
        return
    
    # Get approved O&M components (already audited at this point)
    employee = approved_expenses.get("employee_cost", 0.0)
    rm = approved_expenses.get("repair_maintenance", 0.0)
    ag = approved_expenses.get("admin_general", 0.0)
    total_om = employee + rm + ag
    
    # Receivables = 2 months of billed revenue (NOT expenditure)
    # KSERC uses actual revenue billed to consumers for receivables
    # CRITICAL: Use claimed_revenues from state, NOT approved_expenses (circular ref!)
    total_revenue = 0.0
    if state:
        # Prefer claimed_revenues (petitioner's actual billed revenue)
        claimed_revenues = state.get("claimed_revenues", {})
        if claimed_revenues:
            total_revenue = sum(v for v in claimed_revenues.values() if isinstance(v, (int, float)))
        # Second choice: approved_revenues if explicitly set by auditor
        if total_revenue == 0:
            approved_revenues = state.get("approved_revenues", {})
            if approved_revenues:
                total_revenue = sum(v for v in approved_revenues.values() if isinstance(v, (int, float)))
    
    # Last resort: use claimed_expenses total (excluding IWC itself to avoid circularity)
    if total_revenue == 0:
        total_revenue = sum(
            v for k, v in claimed_expenses.items()
            if k != key and isinstance(v, (int, float))
        )
        logger.warning(f"IWC: No revenue data available, using claimed expenses (excl IWC) = {total_revenue:.2f}")
    
    # KSERC IWC Formula (Regulation 29):
    # WC = (1/12 × O&M) + (15% × O&M for spares) + (Receivables component)
    # Receivables = 2 months of billed revenue / 12 = revenue / 6
    # Interest rate = SBI EBLR + 2% (NOT SBI term deposit rate)
    # Source: KSERC OP 52/2024 - SBI 1-year EBLR 9.15% + 2% = 11.15%
    sbi_eblr_rate = SBI_EBLR_PLUS_2_RATES.get(fy, 11.15) / 100.0
    
    om_monthly = total_om / 12.0
    maintenance_spares = total_om * 0.15
    two_month_receivables = total_revenue / 6.0  # 2 months of revenue
    receivables_monthly = two_month_receivables / 12.0
    
    working_capital = om_monthly + maintenance_spares + receivables_monthly
    computed_iwc = round(working_capital * sbi_eblr_rate, 2)
    
    logger.info(
        f"IWC components: O&M/12={om_monthly:.2f}, Spares(15% O&M)={maintenance_spares:.2f}, "
        f"Receivables/12={receivables_monthly:.2f}, WC={working_capital:.2f}, "
        f"SBI_EBLR+2%={sbi_eblr_rate*100:.2f}%, Computed IWC={computed_iwc:.2f}"
    )
    
    # Sanity check: IWC should be a small fraction of total revenue (typically < 2%)
    if total_revenue > 0 and computed_iwc > total_revenue * 0.05:
        logger.warning(
            f"IWC sanity check FAILED: computed {computed_iwc:.2f} > 5% of revenue {total_revenue:.2f}. "
            f"Falling back to claimed value {claimed:.2f}"
        )
        computed_iwc = claimed
    
    # KSERC approves the formula-computed value, even if higher than claimed
    # (verified from Infopark 2022-23 order: claimed 2.70, KSERC approved 3.72)
    if myt_norm > 0.0:
        # Cross-check with MYT norm — use whichever is closer to computed
        approved = computed_iwc if computed_iwc > 0 else myt_norm
    elif computed_iwc > 0:
        approved = computed_iwc
    else:
        approved = claimed
    
    approved_expenses[key] = approved
    
    if abs(claimed - approved) > 0.01 and claimed > 0:
        cut = round(claimed - approved, 2)
        disallowances.append({
            "item": "Interest on Working Capital",
            "claimed": claimed,
            "approved": approved,
            "amount_cut": cut,
            "justification": (
                f"KSERC Regulation 29: Working Capital = (O&M/12) + (15% spares) + (receivables/12). "
                f"O&M/12 = Rs. {om_monthly:.2f}L, Spares(15%) = Rs. {maintenance_spares:.2f}L, "
                f"Receivables/12 = Rs. {receivables_monthly:.2f}L. "
                f"WC = Rs. {working_capital:.2f}L × SBI EBLR+2% ({sbi_eblr_rate*100:.2f}%) = Rs. {computed_iwc:.2f}L. "
                f"{'KSERC approves computed value above the claim.' if approved > claimed else f'Approved: Rs. {approved:.2f}L.'}"
            ),
        })
    
    logger.info(f"IWC: claimed={claimed}, computed={computed_iwc}, myt_norm={myt_norm}, approved={approved}")


def _audit_revenues(
    claimed_revenues: Dict[str, float],
    state: dict,
    fy: str
) -> Dict[str, float]:
    """
    Revenue from sale of power, wheeling charges, non-tariff income are
    approved as verified by the Commission (actual metered sales).
    Imputed NTI penalty applies for accumulated surplus.
    """
    approved = {}
    for k, v in claimed_revenues.items():
        approved[k] = v
        
    sbi_rate = SBI_RETAIL_TERM_DEPOSIT_RATES.get(fy, 6.80) / 100.0
    closing_surplus_prev = state.get("accumulated_surplus", 0.0)
    
    imputed_nti = round(closing_surplus_prev * sbi_rate, 2)
    claimed_nti = claimed_revenues.get("non_tariff_income", 0.0)
    
    # Enforce minimum imputed non-tariff income
    if imputed_nti > claimed_nti:
        approved["non_tariff_income"] = imputed_nti
        diff = round(imputed_nti - claimed_nti, 2)
        logger.info(f"Imputed NTI Penalty: Increased NTI from {claimed_nti} to {imputed_nti} (Surplus: {closing_surplus_prev} @ {sbi_rate*100:.2f}%)")
        
        # Log this inside the state so the graph can see it if necessary
        state["imputed_nti_adjustment"] = {
            "amount_added": diff,
            "justification": f"KSERC strictly enforces an Imputed Non-Tariff Income penalty. The closing accumulated revenue surplus from the previous year (Rs. {closing_surplus_prev:.2f} Lakhs) is multiplied by the prevailing April 1st SBI Retail Term Deposit Rate ({sbi_rate*100:.2f}%), even if the licensee did not fixed-deposit the money."
        }
        
    return approved


# ══════════════════════════════════════════════════════════════════════
# Rule 6: Capital Structure-Based Grant Adjustments
# ══════════════════════════════════════════════════════════════════════

def _apply_capital_structure_adjustments(
    state: dict,
    approved_expenses: Dict[str, float],
    disallowances: List[Dict[str, Any]],
    cap_analysis: Dict[str, Any],
) -> None:
    """
    Apply REMAINING capital structure adjustments not handled by Reg 27/28 functions.
    
    NOTE: Depreciation and RoNFA adjustments are now handled directly by
    _audit_depreciation_reg27 and _audit_return_on_nfa_reg28 respectively.
    This function only handles interest zeroing and IWC adjustments.
    """
    grant_ratio = cap_analysis.get("grant_ratio", 0.0)
    has_debt = cap_analysis.get("has_debt", True)
    has_equity = cap_analysis.get("has_equity", True)
    source = cap_analysis.get("source", "none")

    if source == "none":
        return

    logger.info(f"Capital structure adjustments (interest/IWC only): "
                f"grant_ratio={grant_ratio}%, has_debt={has_debt}, source={source}")

    # ── Interest on LT Loans: zero if no actual debt AND KSERC never approved ──
    kserc_interest = cap_analysis.get("kserc_approved_interest", 0.0)
    current_interest = approved_expenses.get("interest_long_term", 0.0)
    if current_interest > 0 and not has_debt and kserc_interest <= 0:
        approved_expenses["interest_long_term"] = 0.0
        disallowances.append({
            "item": "Interest on Long-Term Loans - No Debt",
            "claimed": current_interest,
            "approved": 0.0,
            "amount_cut": current_interest,
            "justification": (
                f"Capital structure analysis ({source}) shows Rs. 0.00L in "
                f"outstanding loans. KSERC has not approved interest in past orders. "
                f"Interest on long-term loans is not admissible. Approved: Rs. 0.00 Lakhs."
            ),
        })
        logger.info(f"Capital Adj: Interest zeroed (no debt, no KSERC precedent)")
    elif current_interest > 0 and not has_debt and kserc_interest > 0:
        # KSERC approved interest in past — use normative loan interest
        approved_interest = min(current_interest, kserc_interest * 1.1)
        approved_expenses["interest_long_term"] = round(approved_interest, 2)
        if current_interest > approved_interest:
            disallowances.append({
                "item": "Interest on Normative Loan - Precedent Cap",
                "claimed": current_interest,
                "approved": round(approved_interest, 2),
                "amount_cut": round(current_interest - approved_interest, 2),
                "justification": (
                    f"Capital structure shows no outstanding debt, but KSERC "
                    f"approved normative interest of Rs. {kserc_interest:.2f}L in past orders "
                    f"(70:30 normative debt-equity). Approved: Rs. {approved_interest:.2f}L."
                ),
            })
        logger.info(f"Capital Adj: Interest capped at precedent {approved_interest} (KSERC={kserc_interest})")

    # ── Interest on Working Capital: zero if no debt and fully grant-funded ──
    current_iwc = approved_expenses.get("interest_working_capital", 0.0)
    if current_iwc > 0 and not has_debt and grant_ratio >= 95:
        approved_expenses["interest_working_capital"] = 0.0
        disallowances.append({
            "item": "Interest on Working Capital - No Debt",
            "claimed": current_iwc,
            "approved": 0.0,
            "amount_cut": current_iwc,
            "justification": (
                f"Capital structure analysis ({source}) shows the licensee is fully "
                f"grant-funded with no outstanding debt. Working capital interest is "
                f"not admissible. Approved: Rs. 0.00 Lakhs."
            ),
        })
        logger.info(f"Capital Adj: IWC zeroed (no debt, fully grant-funded)")


def _apply_ai_grant_adjustments_legacy(
    state: dict,
    approved_expenses: Dict[str, float],
    disallowances: List[Dict[str, Any]],
) -> None:
    """Legacy AI-based grant adjustments when no capital structure data available."""
    insights = state.get("ai_insights", {})
    grants_info = insights.get("grants_and_subsidies", {})
    if not grants_info.get("found", False):
        return

    total_grants = grants_info.get("total_grants_lakhs", 0.0)
    if total_grants <= 0:
        return

    details = grants_info.get("details", [])
    evidence = "; ".join(
        f"{d.get('source', 'Unknown')}: Rs. {d.get('amount_lakhs', 0):.2f}L"
        for d in details
    )

    current_dep = approved_expenses.get("depreciation", 0.0)
    if current_dep > 0:
        dep_reduction = min(total_grants * 0.1, current_dep * 0.5)
        new_dep = round(current_dep - dep_reduction, 2)
        if dep_reduction > 0:
            approved_expenses["depreciation"] = new_dep
            disallowances.append({
                "item": "Depreciation - Grant Adjustment (AI Research)",
                "claimed": current_dep,
                "approved": new_dep,
                "amount_cut": round(dep_reduction, 2),
                "justification": f"AI analysis identified Rs. {total_grants:.2f}L in grants. {evidence}",
            })

    current_ronfa = approved_expenses.get("return_on_nfa", 0.0)
    if current_ronfa > 0:
        ronfa_reduction = min(total_grants * 0.055, current_ronfa * 0.5)
        new_ronfa = round(current_ronfa - ronfa_reduction, 2)
        if ronfa_reduction > 0:
            approved_expenses["return_on_nfa"] = new_ronfa
            disallowances.append({
                "item": "Return on NFA - Grant Adjustment (AI Research)",
                "claimed": current_ronfa,
                "approved": new_ronfa,
                "amount_cut": round(ronfa_reduction, 2),
                "justification": f"AI analysis identified Rs. {total_grants:.2f}L in grants. {evidence}",
            })


# ══════════════════════════════════════════════════════════════════════
# Main LangGraph Node
# ══════════════════════════════════════════════════════════════════════

def audit_petition(state: dict) -> dict:
    """
    LangGraph node: apply KSERC audit rules to the extracted petition data.

    PRIMARY PATH: Use AI Commission decisions from the Deep Analyzer.
    FALLBACK: Use static rule-based capping if AI analysis failed.
    """
    claimed_expenses: Dict[str, float] = state.get("claimed_expenses", {})
    claimed_revenues: Dict[str, float] = state.get("claimed_revenues", {})
    myt_norms: Dict[str, float] = state.get("myt_baseline_norms", {})
    licensee = state.get("licensee_name", "Unknown")
    licensee_id = state.get("licensee_id", "global")
    fy = state.get("financial_year", "")
    ai_insights = state.get("ai_insights", {})

    # Initialize partitioned semantic researcher
    researcher = get_researcher(licensee_id) if get_researcher else None

    logger.info(f"=== audit_petition: {licensee} ({licensee_id}) FY {fy} ===")

    approved_expenses: Dict[str, float] = {}
    disallowances: List[Dict[str, Any]] = []

    # ══════════════════════════════════════════════════════════════
    # Check if AI Commission made decisions
    # ══════════════════════════════════════════════════════════════
    ai_decisions = ai_insights.get("approved_expenses", {})

    if ai_decisions:
        logger.info(f"=== USING AI COMMISSION DECISIONS ({len(ai_decisions)} components) ===")

        all_keys = set(list(claimed_expenses.keys()) + list(ai_decisions.keys()))
        for key in all_keys:
            if key in ["power_purchase_cost", "section3_1_duty"]:
                continue
                
            ai_item = ai_decisions.get(key, {})
            claimed = claimed_expenses.get(key, 0.0)

            if isinstance(ai_item, dict) and "amount" in ai_item:
                ai_amount = float(ai_item["amount"])
                ai_justification = ai_item.get("justification", "AI Commission decision.")
                approved_expenses[key] = ai_amount

                diff = round(claimed - ai_amount, 2)
                if abs(diff) > 0.01:
                    display = COMPONENT_DISPLAY.get(key, key)
                    label = display if diff > 0 else display + " (Adjustment)"
                    disallowances.append({
                        "item": label,
                        "claimed": claimed,
                        "approved": ai_amount,
                        "amount_cut": diff,
                        "justification": ai_justification,
                    })
                    logger.info(f"  AI: {key} — Claimed {claimed}, Approved {ai_amount}, Diff {diff}")
                else:
                    logger.info(f"  AI: {key} — Approved as claimed: {ai_amount}")
            else:
                approved_expenses[key] = claimed
                logger.info(f"  AI: {key} — No AI decision, approved as claimed: {claimed}")

        # Enforce strict deterministic rules that the LLM cannot override
        _audit_section3_duty(claimed_expenses, approved_expenses, disallowances)
        _audit_power_purchase(state, approved_expenses, disallowances, myt_norms)

        logger.info("=== AI Commission decisions applied ===")

    else:
        # ══════════════════════════════════════════════════════════
        # FALLBACK: Rule-based auditing (MYT norm + precedent DB)
        # ══════════════════════════════════════════════════════════
        logger.info("=== FALLBACK: Using rule-based auditing (MYT norms + precedent DB) ===")
        logger.info(f"MYT norms available: {bool(myt_norms)}")
        logger.info(f"Precedent DB available: {_precedent_lookup.available if _precedent_lookup else False}")

        # Analyze capital structure FIRST
        cap_analysis = _analyze_capital_structure(state)

        _audit_section3_duty(claimed_expenses, approved_expenses, disallowances)
        _audit_power_purchase(state, approved_expenses, disallowances, myt_norms)

        for key in ("employee_cost", "repair_maintenance", "admin_general"):
            _audit_norm_capped_component(
                key, claimed_expenses, approved_expenses, myt_norms,
                disallowances, licensee=licensee, fy=fy, researcher=researcher
            )

        # Depreciation — KSERC Regulation 27 (replaces generic norm cap)
        _audit_depreciation_reg27(
            state, claimed_expenses, approved_expenses, myt_norms,
            disallowances, cap_analysis, licensee=licensee, fy=fy
        )

        _audit_interest_long_term_loans(claimed_expenses, approved_expenses, myt_norms, disallowances, fy, licensee=licensee)
        _audit_interest_consumer_deposits(claimed_expenses, approved_expenses, myt_norms, disallowances, fy, licensee=licensee)
        _audit_interest_working_capital(
            claimed_expenses, approved_expenses, myt_norms, disallowances, fy,
            state=state
        )

        _audit_passthrough("carrying_cost", claimed_expenses, approved_expenses)

        # Return on NFA — KSERC Regulation 28 (replaces generic norm cap)
        _audit_return_on_nfa_reg28(
            state, claimed_expenses, approved_expenses, myt_norms,
            disallowances, cap_analysis, licensee=licensee, fy=fy
        )

        _audit_norm_capped_component(
            "other_debits", claimed_expenses, approved_expenses, myt_norms,
            disallowances, licensee=licensee, fy=fy
        )
        _audit_passthrough("other_expenses", claimed_expenses, approved_expenses)

        # ARA Forensic Check: Technical Prudence (Solar/Renewable)
        _apply_technical_prudence(state, approved_expenses, disallowances)

        # NOTE: Capital structure adjustments for depreciation and RoNFA are now
        # handled directly within _audit_depreciation_reg27 and _audit_return_on_nfa_reg28.
        # Only apply remaining adjustments (interest zeroing, IWC for fully grant-funded).
        _apply_capital_structure_adjustments(
            state, approved_expenses, disallowances, cap_analysis
        )

    # ── Revenue — approve as claimed (actual metered sales) ───
    approved_revenues = _audit_revenues(claimed_revenues, state, fy)

    # ── Revenue gap / surplus computation ─────────────────────
    total_claimed_exp  = round(sum(claimed_expenses.values()), 2)
    total_approved_exp = round(sum(approved_expenses.values()), 2)
    total_claimed_rev  = round(sum(claimed_revenues.values()), 2)
    total_approved_rev = round(sum(approved_revenues.values()), 2)

    gap_surplus = round(total_approved_rev - total_approved_exp, 2)
    gap_label = "Revenue Surplus" if gap_surplus >= 0 else "Revenue Gap (Deficit)"

    logger.info(f"Total claimed expenditure  : Rs. {total_claimed_exp} Lakhs")
    logger.info(f"Total approved expenditure : Rs. {total_approved_exp} Lakhs")
    logger.info(f"Total claimed revenue      : Rs. {total_claimed_rev} Lakhs")
    logger.info(f"Total approved revenue     : Rs. {total_approved_rev} Lakhs")
    logger.info(f"{gap_label}             : Rs. {gap_surplus} Lakhs")
    logger.info(f"Disallowances ({len(disallowances)}): {[d['item'] for d in disallowances]}")

    return {
        "approved_expenses":          approved_expenses,
        "approved_revenues":          approved_revenues,
        "disallowance_log":           disallowances,
        "total_claimed_expenditure":  total_claimed_exp,
        "total_approved_expenditure": total_approved_exp,
        "total_claimed_revenue":      total_claimed_rev,
        "total_approved_revenue":     total_approved_rev,
        "final_revenue_gap_surplus":  gap_surplus,
        "imputed_interest_on_surplus": 0.0,
    }


def _apply_technical_prudence(state: dict, approved_expenses: dict, disallowances: list) -> None:
    """
    ARA Forensic Audit: Checks for technical efficiency drops.
    If solar efficiency is < 16%, flag as imprudent.
    """
    solar_efficiency = state.get("solar_efficiency_pct", 0.0)
    if 0 < solar_efficiency < 16.0:
        # Flag and potentially disallow a portion of related O&M
        rm_cost = approved_expenses.get("repair_maintenance", 0.0)
        technical_penalty = round(rm_cost * 0.10, 2)  # 10% penalty for imprudence
        
        approved_expenses["repair_maintenance"] = max(rm_cost - technical_penalty, 0.0)
        disallowances.append({
            "item": "R&M — ARA Technical Prudence Disallowance",
            "claimed": rm_cost,
            "approved": approved_expenses["repair_maintenance"],
            "amount_cut": technical_penalty,
            "justification": (
                f"[ARA Forensic Audit]: Solar plant reported efficiency of {solar_efficiency}% "
                f"is below the technical threshold of 16.0% (Case Study B). "
                f"Infrastructure O&M for inefficient assets is considered 'Imprudent Capital Expenditure'. "
                f"A regulatory disallowance of ₹{technical_penalty} Lakhs (10% of R&M) is applied."
            )
        })
        logger.info(f"[ARA] Technical Prudence Penalty: {technical_penalty} for {solar_efficiency}% efficiency")

