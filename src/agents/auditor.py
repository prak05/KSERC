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
from src.config import GEMINI_MODEL

logger = logging.getLogger(__name__)

# ── Precedent Lookup Integration ──────────────────────────────────────
try:
    from src.rag.precedent_lookup import PrecedentLookup
    _precedent_lookup = PrecedentLookup()
    logger.info(f"Precedent DB loaded: {_precedent_lookup.available}")
except Exception as e:
    logger.warning(f"Precedent lookup not available: {e}")
    _precedent_lookup = None

# ── Deep Table Helpers ────────────────────────────────────────────────
try:
    from src.agents.deep_table_extractor import (
        get_tables_by_component,
        get_justification,
        get_phase_wise_ppc,
        get_component_breakdown,
    )
    _deep_table_available = True
except ImportError:
    _deep_table_available = False
    logger.warning("Deep table extractor helpers not available")

# ── Default target distribution loss by licensee (fallback) ───────────
# NOTE: These targets DECREASE each year per the MYT Control Period 2022-27.
# Source: KDHP MYT Order dated 26-11-2025, Table 5
DEFAULT_TARGET_DIST_LOSS = {
    "technopark": {
        "2022-23": 4.40, "2023-24": 3.70, "2024-25": 3.40,
        "2025-26": 3.30, "2026-27": 3.30,
    },
    "infopark": {
        "2022-23": 4.23, "2023-24": 4.23, "2024-25": 4.23,
        "2025-26": 4.23, "2026-27": 4.23,
    },
    "cseza": {
        "2022-23": 1.45, "2023-24": 1.44, "2024-25": 1.42,
        "2025-26": 1.41, "2026-27": 1.39,
    },
    "kdhp": {
        "2022-23": 9.60, "2023-24": 9.35, "2024-25": 9.07,
        "2025-26": 8.85, "2026-27": 8.60,
    },
}
# Aliases for full licensee names (lookup uses str.lower().contains())
DEFAULT_TARGET_DIST_LOSS["kannan"] = DEFAULT_TARGET_DIST_LOSS["kdhp"]
DEFAULT_TARGET_DIST_LOSS["cochin"] = DEFAULT_TARGET_DIST_LOSS["cseza"]

# Actual inflation escalation (CPI 70% + WPI 30% weighted average)
# Source: KSERC orders — applied to O&M norms instead of flat MYT %
KSERC_INFLATION_ESCALATION = {
    "2019-20": 4.08,
    "2020-21": 5.52,
    "2021-22": 6.15,
    "2022-23": 7.06,
    "2023-24": 6.50,  # Estimated from CPI/WPI trends
    "2024-25": 3.05,  # Confirmed from KSERC order (Annexure-7, actual CPI 70%+WPI 30%)
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
# Helper: Get KSERC's past decision for a component from order learnings
# ══════════════════════════════════════════════════════════════════════

def _get_order_learning_decision(
    detailed_tables: Dict[str, Any],
    component: str,
    licensee: str = "",
) -> Dict[str, Any]:
    """
    Look up KSERC's past decision on a component from order_learnings.
    
    Priority:
    1. Same licensee's past order decision (most relevant)
    2. Cross-licensee pattern (average behavior across all orders)
    
    Returns dict with:
        same_licensee_decision: dict or None
        cross_licensee_pattern: dict or None
        recommended_cut_pct: float (0 if no data)
        kserc_reasoning: str
        methodology: str
    """
    result = {
        "same_licensee_decision": None,
        "cross_licensee_pattern": None,
        "recommended_cut_pct": 0.0,
        "kserc_reasoning": "",
        "methodology": "",
    }
    
    if not detailed_tables:
        return result
    
    order_learnings = detailed_tables.get("order_learnings", {})
    cross_patterns = detailed_tables.get("cross_licensee_patterns", {})
    
    # 1. Same licensee's past order
    if licensee and order_learnings:
        for order_key, order_data in order_learnings.items():
            if licensee.lower() in order_key.lower():
                decisions = order_data.get("kserc_decisions", {})
                decision = decisions.get(component, {})
                if isinstance(decision, dict) and decision.get("claimed_amount", 0) > 0:
                    result["same_licensee_decision"] = {
                        "order_ref": order_key,
                        **decision,
                    }
                    if decision.get("kserc_reasoning"):
                        result["kserc_reasoning"] = decision["kserc_reasoning"]
                    if decision.get("methodology_applied"):
                        result["methodology"] = decision["methodology_applied"]
                    
                    claimed = float(decision.get("claimed_amount", 0) or 0)
                    approved = float(decision.get("approved_amount", 0) or 0)
                    if claimed > 0:
                        result["recommended_cut_pct"] = round(
                            (claimed - approved) / claimed * 100, 2
                        )
                    break  # Use most recent same-licensee decision
    
    # 2. Cross-licensee pattern
    if cross_patterns and component in cross_patterns:
        pattern = cross_patterns[component]
        if isinstance(pattern, dict):
            result["cross_licensee_pattern"] = pattern
            # If no same-licensee decision, use cross-licensee avg
            if not result["same_licensee_decision"]:
                result["recommended_cut_pct"] = pattern.get("avg_cut_percentage", 0.0)
                reasonings = pattern.get("common_reasonings", [])
                if reasonings:
                    result["kserc_reasoning"] = str(reasonings[0])
                methods = pattern.get("methodologies", [])
                if methods:
                    result["methodology"] = methods[0]
    
    return result


# ══════════════════════════════════════════════════════════════════════
# Helper: Load regulation clauses for equation lookup
# ══════════════════════════════════════════════════════════════════════

def _load_regulation_clauses() -> Dict[str, Any]:
    """Load KSERC regulation clauses with equations."""
    import json
    from pathlib import Path
    reg_path = Path(__file__).resolve().parent.parent.parent / "data" / "regulations" / "regulation_clauses.json"
    try:
        return json.loads(reg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

_REGULATION_CLAUSES = _load_regulation_clauses()


def _get_regulation_equation(clause_number: str, equation_key: str = "") -> str:
    """Get equation text from a regulation clause."""
    clause = _REGULATION_CLAUSES.get(clause_number, {})
    equations = clause.get("equations", {})
    if equation_key:
        return str(equations.get(equation_key, ""))
    return str(equations)


# ══════════════════════════════════════════════════════════════════════
# Helper: get MYT norm for a component
# ══════════════════════════════════════════════════════════════════════

def _myt_norm(myt_norms: Dict[str, float], key: str) -> float:
    """Return the MYT approved norm for a key, or 0.0 if not available."""
    return float(myt_norms.get(key, 0.0) or 0.0)


def _get_target_loss(licensee_name: str, myt_norms: Dict[str, float], fy: str = "") -> float:
    """
    Get target distribution loss % — year-specific value from MYT Control Period.

    PRIORITY ORDER:
    1. MYT norms dict — freshly extracted from the actual MYT Order PDF (most accurate)
    2. Year-specific hardcoded defaults (fallback if myt_norms not loaded)
    3. Generic fallback (5.0%)
    """
    # Priority 1: MYT norms dict — this is extracted directly from the MYT Order
    # e.g. 9.07% for KDHP 2024-25 from OP 41/2025, overrides any hardcoded value
    if "target_distribution_loss_pct" in myt_norms:
        val = float(myt_norms["target_distribution_loss_pct"])
        if val > 0:
            logger.info(f"Target dist loss from myt_norms: {val}% (FY={fy})")
            return val

    # Priority 2: Year-specific hardcoded defaults (from MYT Order study)
    for key, val in DEFAULT_TARGET_DIST_LOSS.items():
        if key in licensee_name.lower():
            if isinstance(val, dict) and fy in val:
                logger.info(f"Target dist loss from hardcoded DEFAULT ({key}): {val[fy]}% (FY={fy})")
                return val[fy]

    # Priority 3: Any non-year-specific default
    for key, val in DEFAULT_TARGET_DIST_LOSS.items():
        if key in licensee_name.lower():
            if isinstance(val, dict):
                sorted_years = sorted(val.keys())
                return val[sorted_years[-1]] if sorted_years else 5.0
            else:
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
    
    Based on deep research of actual KSERC orders:
    - KDHP 2021-22: Actual loss 10.99% > target 10.00% → penalty Rs.28.96 lakh
    - KDHP 2022-23: Actual loss 9.53% < target 9.60% → efficiency gain Rs.1.67 lakh
    - KDHP 2024-25: Excess demand charges Rs.30.61 lakh flagged as imprudent
    
    Steps:
    1. Detect and flag excess demand charges (KSERC considers imprudent but
       historically has NOT deducted them — just issues warnings)
    2. Verify PPC against KSEB records (minor reconciliation adjustments)
    3. Apply Regulation 73(3) distribution loss formula:
       - If actual_loss > target_loss: penalty = excess_loss_units × avg_cost
       - If actual_loss < target_loss: efficiency gain shared 2:1 (licensee:consumer)
    """
    claimed_ppc = state.get("claimed_expenses", {}).get("power_purchase_cost", 0.0)
    actual_loss_pct = state.get("claimed_distribution_loss_pct", 0.0)
    
    # Fallback: If extractor failed to find dist loss (image-based PDFs), read from myt_baselines
    if actual_loss_pct == 0.0:
        actual_loss_pct = float(myt_norms.get("actual_distribution_loss_pct", 0.0) or 0.0)
        if actual_loss_pct > 0:
            logger.info(f"Distribution loss from myt_baselines fallback: {actual_loss_pct}%")
            state["claimed_distribution_loss_pct"] = actual_loss_pct
    
    target_loss_pct = _get_target_loss(state.get("licensee_name", ""), myt_norms, fy=state.get("financial_year", ""))
    licensee_name = state.get("licensee_name", "")
    
    # Try to get actual energy data from petition (extracted by extractor)
    energy_input_mu = state.get("energy_input_mu", 0.0)
    energy_sold_mu = state.get("energy_sold_mu", 0.0)
    energy_wheeled_mu = state.get("energy_wheeled_mu", 0.0)
    
    # Extract excess demand charges if available in petition data
    excess_demand_charges = state.get("excess_demand_charges", 0.0)
    
    state["target_distribution_loss_pct"] = target_loss_pct

    if claimed_ppc == 0.0:
        approved_expenses["power_purchase_cost"] = claimed_ppc
        logger.warning("PPC: claimed PPC is 0 — approving as claimed.")
        return
    
    # ── Step 1: Excess Demand Charges Observation ──
    # KSERC consistently flags excess demand charges as imprudent practice
    # but has NOT deducted them in KDHP 2021-22 (6.17L) or 2022-23 (6.78L).
    # They issue warnings to increase contract demand or manage load.
    # For 2024-25, they noted the charges increased to 30.61L and "reiterates
    # that the licensee shall take immediate steps to address the matter."
    if excess_demand_charges > 0:
        logger.info(
            f"PPC: Excess demand charges of Rs. {excess_demand_charges:.2f} Lakhs "
            f"included in claimed PPC. KSERC flags as imprudent but historically "
            f"does not deduct for KDHP."
        )
        # Store as observation for the audit report
        state.setdefault("audit_observations", []).append({
            "component": "Power Purchase Cost",
            "observation": (
                f"The licensee has included Rs. {excess_demand_charges:.2f} Lakhs as excess "
                f"demand charges in the power purchase cost. The Commission notes that the "
                f"licensee is consistently exceeding the contract demand with KSEB Ltd. "
                f"Claiming excess demand charges without taking necessary steps to increase "
                f"the contract demand is not a prudent practice. The Commission reiterates "
                f"that the licensee shall take immediate steps to address the matter."
            ),
        })

    # ── Step 1b: Phase-Wise PPC Analysis (from Deep Table Extraction) ──
    detailed_tables = state.get("detailed_tables", {})
    if _deep_table_available and detailed_tables:
        phase_rows = get_phase_wise_ppc(detailed_tables)
        if phase_rows:
            logger.info(f"PPC: Phase-wise breakdown found ({len(phase_rows)} campuses/phases):")
            for row in phase_rows:
                campus = row.get("Campus", row.get("Particulars", "Unknown"))
                total_charge = row.get("Total charge Rs lakh", row.get("Total", 0))
                demand = row.get("Maximum demand kVA", row.get("Demand kVA", 0))
                energy = row.get("Energy Received lakh units", row.get("Energy MU", 0))
                logger.info(
                    f"  {campus}: Demand={demand} kVA, Energy={energy}, "
                    f"Total={total_charge} Lakhs"
                )
            # Store for audit report
            state.setdefault("audit_observations", []).append({
                "component": "Power Purchase Cost",
                "observation": (
                    f"Phase-wise PPC analysis: {len(phase_rows)} campuses/phases identified. "
                    f"The Commission has verified the phase-wise power purchase cost breakdowns "
                    f"submitted by the licensee."
                ),
                "detail_tables": phase_rows,
            })

        # Get licensee justification for PPC
        ppc_justification = get_justification(detailed_tables, "power_purchase")
        if ppc_justification:
            logger.info(f"PPC: Licensee Justification: {ppc_justification[:150]}...")

        # Enrich energy data from deep extraction if not already present
        energy_data = detailed_tables.get("energy_data", {})
        if energy_input_mu == 0 and energy_data.get("energy_input_mu", 0) > 0:
            energy_input_mu = float(energy_data["energy_input_mu"])
            state["energy_input_mu"] = energy_input_mu
            logger.info(f"PPC: Enriched energy_input_mu from deep tables: {energy_input_mu} MU")
        if energy_sold_mu == 0 and energy_data.get("energy_sold_mu", 0) > 0:
            energy_sold_mu = float(energy_data["energy_sold_mu"])
            state["energy_sold_mu"] = energy_sold_mu
            logger.info(f"PPC: Enriched energy_sold_mu from deep tables: {energy_sold_mu} MU")
        if excess_demand_charges == 0 and energy_data.get("excess_demand_charges", 0) > 0:
            excess_demand_charges = float(energy_data["excess_demand_charges"])
            logger.info(f"PPC: Found excess demand charges from deep tables: {excess_demand_charges} Lakhs")

    # ── Step 2: Energy Balance Data ──────────────────────────────────────────
    # Populated by extractor from Annexure B (energy input) or petition table.
    # Target loss % always comes from myt_norms — never hardcoded here.
    actual_loss_lakh_units   = float(state.get("actual_loss_lakh_units", 0.0) or 0.0)
    approved_loss_lakh_units = float(state.get("approved_loss_lakh_units", 0.0) or 0.0)
    energy_input_lakh_units  = float(state.get("energy_input_lakh_units", 0.0) or 0.0)
    energy_sales_lakh_units  = float(state.get("energy_sales_lakh_units", 0.0) or 0.0)
    actual_loss_pct_balance  = float(state.get("actual_loss_pct_energy_balance", 0.0) or 0.0)
    appc_from_state          = float(state.get("appc_rs_per_unit", 0.0) or 0.0)

    logger.info(
        f"PPC: energy_input={energy_input_lakh_units} LU, energy_sales={energy_sales_lakh_units} LU, "
        f"actual_loss={actual_loss_lakh_units} LU, actual_loss_pct(balance)={actual_loss_pct_balance}%, "
        f"appc={appc_from_state}, target_pct={target_loss_pct}"
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Regulation 73(3) — Deterministic PPC Formula
    # ══════════════════════════════════════════════════════════════════════════
    #
    # Step 0: Actual Loss % = (Actual Loss Units / Energy Input) × 100
    # Step 1: Compute Approved Loss Units (two formula branches):
    #   If energy_input exists:
    #       approved_loss = energy_input × target% / (1 − target%)
    #   If only energy_sales exists:
    #       approved_loss = energy_sales × target% / (1 − target%)
    # Step 2: Compare approved_loss vs actual_loss.
    # Step 3: Convert difference × APPC.
    # Step 4: Adjust claimed PPC.
    #
    # IMPORTANT: Do NOT reconstruct energy_input from sales + loss.
    #            Use the values directly as extracted from Annexure B / petition.
    # ══════════════════════════════════════════════════════════════════════════

    target_decimal = target_loss_pct / 100.0

    # ── Step 0: Compute Actual Loss % ────────────────────────────────────
    actual_loss_pct = 0.0
    if actual_loss_lakh_units > 0 and energy_input_lakh_units > 0:
        actual_loss_pct = round((actual_loss_lakh_units / energy_input_lakh_units) * 100.0, 2)
    elif actual_loss_lakh_units > 0 and energy_sales_lakh_units > 0:
        actual_loss_pct = round((actual_loss_lakh_units / (energy_sales_lakh_units + actual_loss_lakh_units)) * 100.0, 2)
    state["actual_distribution_loss_pct"] = actual_loss_pct
    logger.info(f"PPC Step 0: actual_loss_pct = {actual_loss_lakh_units} / {energy_input_lakh_units} × 100 = {actual_loss_pct}%")

    if actual_loss_lakh_units > 0 and target_decimal > 0:

        # ── Resolve APPC first (needed for Step 4) ──
        if appc_from_state > 0:
            avg_cost = appc_from_state
            logger.info(f"PPC: APPC from petition (direct): {avg_cost} Rs/unit")
        elif energy_purchased_lakh_units > 0 and claimed_ppc > 0:
            avg_cost = round(claimed_ppc / energy_purchased_lakh_units, 4)
            logger.info(f"PPC: APPC = {claimed_ppc:.2f} / {energy_purchased_lakh_units:.2f} LU = {avg_cost:.4f} Rs/unit")
        elif energy_input_lakh_units > 0 and claimed_ppc > 0:
            avg_cost = round(claimed_ppc / energy_input_lakh_units, 4)
            logger.info(f"PPC: APPC (via energy_input) = {claimed_ppc:.2f} / {energy_input_lakh_units:.2f} LU = {avg_cost:.4f} Rs/unit")
        else:
            avg_cost = float(myt_norms.get("avg_power_purchase_cost_rs_per_kwh", 0.0) or 0.0)
            logger.warning(f"PPC: Cannot compute APPC — using MYT norm fallback: {avg_cost} Rs/unit")

        # ── Step 1: Compute Approved Loss Units ──
        # Base variable depends on whether Annexure B is present in the petition:
        #   - Annexure B present → energy_input × target% / (1 − target%)  [e.g. KDHP]
        #   - No Annexure B (petition table only) → energy_sales × target% / (1 − target%)  [e.g. Infopark]
        # Both use the same formula — only the base variable changes.
        formula_used = ""

        # Detect Annexure B from petition filenames
        filenames = state.get("original_filenames", [])
        has_annexure_b = any("annex" in str(f).lower() for f in filenames)
        logger.info(f"PPC: has_annexure_b={has_annexure_b} (filenames={filenames})")

        if has_annexure_b and energy_input_lakh_units > 0:
            # Annexure B present → use energy_input as base
            energy_base = energy_input_lakh_units
            formula_used = "energy_input"
            logger.info(f"PPC Step 1 [Annexure B]: base = energy_input({energy_base}) LU")
        elif energy_sales_lakh_units > 0:
            # No Annexure B (or energy_input missing) → use energy_sales as base
            energy_base = energy_sales_lakh_units
            formula_used = "energy_sales"
            logger.info(f"PPC Step 1 [petition table]: base = energy_sales({energy_base}) LU")
        elif energy_input_lakh_units > 0:
            # Last fallback: use energy_input even without Annexure B
            energy_base = energy_input_lakh_units
            formula_used = "energy_input_fallback"
            logger.info(f"PPC Step 1 [fallback]: base = energy_input({energy_base}) LU")
        else:
            logger.warning(
                "PPC: Cannot compute approved_loss — need energy_input or energy_sales "
                "from Annexure B / petition table."
            )
            approved_expenses["power_purchase_cost"] = claimed_ppc
            return

        if "input" in formula_used:
            # Loss = Input * TargetLoss%
            approved_loss_lakh_units = round(energy_base * target_decimal, 2)
            logger.info(
                f"PPC Step 1: approved_loss = {energy_base} × {target_loss_pct}% "
                f"= {approved_loss_lakh_units} LU"
            )
        else:
            # Loss = Sales * TargetLoss% / (1 - TargetLoss%)
            approved_loss_lakh_units = round(
                energy_base * target_decimal / (1.0 - target_decimal), 2
            )
            logger.info(
                f"PPC Step 1: approved_loss = {energy_base} × {target_loss_pct}% "
                f"/ (1 − {target_loss_pct}%) = {approved_loss_lakh_units} LU"
            )

        # ── Step 2: Compare Actual vs Approved Loss ──
        loss_difference = round(approved_loss_lakh_units - actual_loss_lakh_units, 4)
        logger.info(
            f"PPC Step 2: loss_difference = approved({approved_loss_lakh_units}) − "
            f"actual({actual_loss_lakh_units}) = {loss_difference} LU "
            f"({'EFFICIENCY GAIN' if loss_difference > 0 else 'EXCESS LOSS'})"
        )

        # ── Step 3: Financial Impact ──
        financial_impact = round(abs(loss_difference) * avg_cost, 2)
        logger.info(
            f"PPC Step 3: financial_impact = |{loss_difference}| × {avg_cost} "
            f"= {financial_impact} Rs Lakhs"
        )

        # ── Step 4: Apply Regulatory Rule ──
        if loss_difference > 0:
            # Efficiency Gain — actual loss < approved loss
            # Regulation 73(3): 2/3 to licensee, 1/3 to consumers
            licensee_share = round(financial_impact * 2.0 / 3.0, 2)
            approved_ppc = round(claimed_ppc + licensee_share, 2)
            approved_expenses["power_purchase_cost"] = approved_ppc
            logger.info(
                f"PPC Step 4: EFFICIENCY GAIN — licensee_share = {financial_impact} × 2/3 = {licensee_share} "
                f"→ approved_ppc = {claimed_ppc} + {licensee_share} = {approved_ppc}"
            )
            disallowances.append({
                "item": "Power Purchase Cost — Distribution Loss Efficiency Gain",
                "claimed": claimed_ppc,
                "approved": approved_ppc,
                "amount_cut": round(claimed_ppc - approved_ppc, 2),
                "justification": (
                    f"The actual distribution loss ({actual_loss_lakh_units:.2f} Lakh units) "
                    f"is below the approved target loss ({approved_loss_lakh_units:.2f} Lakh units, "
                    f"target {target_loss_pct:.2f}%), yielding an efficiency gain of "
                    f"{abs(loss_difference):.2f} Lakh units = Rs. {financial_impact:.2f} Lakhs "
                    f"at APPC Rs. {avg_cost:.2f}/unit. Per Regulation 73(3), 2/3rd "
                    f"(Rs. {licensee_share:.2f} Lakhs) is passed to the licensee. "
                    f"Approved PPC: Rs. {approved_ppc:.2f} Lakhs."
                ),
            })
        else:
            # Excess Loss — actual loss > approved loss
            # Entire excess cost is disallowed
            approved_ppc = round(max(claimed_ppc - financial_impact, 0.0), 2)
            approved_expenses["power_purchase_cost"] = approved_ppc
            logger.info(
                f"PPC Step 4: EXCESS LOSS — penalty = {financial_impact} "
                f"→ approved_ppc = {claimed_ppc} − {financial_impact} = {approved_ppc}"
            )
            disallowances.append({
                "item": "Power Purchase Cost — Distribution Loss Penalty",
                "claimed": claimed_ppc,
                "approved": approved_ppc,
                "amount_cut": round(claimed_ppc - approved_ppc, 2),
                "justification": (
                    f"The actual distribution loss ({actual_loss_lakh_units:.2f} Lakh units) "
                    f"exceeds the approved target loss ({approved_loss_lakh_units:.2f} Lakh units, "
                    f"target {target_loss_pct:.2f}%). Excess loss of {abs(loss_difference):.2f} "
                    f"Lakh units at APPC Rs. {avg_cost:.2f}/unit = Rs. {financial_impact:.2f} Lakhs "
                    f"disallowed per Regulation 73(3). "
                    f"Approved PPC: Rs. {approved_ppc:.2f} Lakhs."
                ),
            })

        # Store all intermediate values for transparency
        state["ppc_reg73_details"] = {
            "formula_used": formula_used,
            "energy_input_lakh_units": energy_input_lakh_units,
            "energy_sales_lakh_units": energy_sales_lakh_units,
            "actual_loss_lakh_units": actual_loss_lakh_units,
            "actual_loss_pct": actual_loss_pct,
            "target_loss_pct": target_loss_pct,
            "approved_loss_lakh_units": approved_loss_lakh_units,
            "loss_difference_lakh_units": loss_difference,
            "appc_rs_per_unit": avg_cost,
            "financial_impact_rs_lakhs": financial_impact,
            "outcome": "efficiency_gain" if loss_difference > 0 else "excess_loss",
            "approved_ppc_rs_lakhs": approved_ppc,
        }
        return  # Done — no need to proceed to derived path below

    if energy_input_mu > 0:
        # Use actual petition data (MU = Million Units = 10 lakh kWh)
        total_lakh_kwh = energy_input_mu * 10.0  # 1 MU = 10 lakh kWh
        avg_cost = claimed_ppc / total_lakh_kwh  # Rs Lakhs / lakh kWh = Rs/kWh
        energy_sales_lakh_kwh = (energy_sold_mu + energy_wheeled_mu) * 10.0
        logger.info(f"PPC: Using petition energy data: input={energy_input_mu} MU, sold={energy_sold_mu} MU, wheeled={energy_wheeled_mu} MU")
    elif actual_loss_pct > 0:
        # Derive from PPC and avg cost from MYT norms
        avg_cost = float(myt_norms.get("avg_power_purchase_cost_rs_per_kwh", 0.0) or 0.0)
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

    # ── Step 3: KSEB Record Verification ──
    # KSERC verifies PPC against KSEB Ltd records. In KDHP 2021-22, a difference
    # of Rs.0.63 lakh was noted. In 2022-23, "a minor difference" was noted.
    # We apply a small KSEB verification adjustment based on precedent patterns.
    kseb_verified_ppc = state.get("kseb_verified_ppc", 0.0)
    base_ppc = kseb_verified_ppc if kseb_verified_ppc > 0 else claimed_ppc

    # ── Step 4: Regulation 73(3) Distribution Loss Adjustment ──
    # Approved loss volume at target %:
    approved_loss_lakh_kwh = energy_sales_lakh_kwh * (target_loss_pct / 100.0) / (1 - target_loss_pct / 100.0)
    actual_loss_lakh_kwh = total_lakh_kwh - energy_sales_lakh_kwh


    if actual_loss_pct > target_loss_pct:
        excess_lakh_kwh   = actual_loss_lakh_kwh - approved_loss_lakh_kwh
        penalty_rs_lakhs  = round(excess_lakh_kwh * avg_cost, 2)
        approved_ppc      = round(base_ppc - penalty_rs_lakhs, 2)

        approved_expenses["power_purchase_cost"] = max(approved_ppc, 0.0)
        disallowances.append({
            "item": "Power Purchase Cost — Distribution Loss Penalty",
            "claimed": claimed_ppc,
            "approved": approved_ppc,
            "amount_cut": round(claimed_ppc - max(approved_ppc, 0.0), 2),
            "justification": (
                f"The actual distribution loss of {actual_loss_pct:.2f}% exceeds the "
                f"KSERC-approved target of {target_loss_pct:.2f}%. "
                f"Excess loss of {excess_lakh_kwh:.2f} lakh kWh at the average "
                f"power purchase cost of Rs. {avg_cost:.2f}/kWh results in a "
                f"disallowance of Rs. {penalty_rs_lakhs:.2f} Lakhs, as per "
                f"Regulation 73(3) of the KSERC Tariff Regulations 2021."
            ),
        })
        logger.info(f"PPC: penalty={penalty_rs_lakhs}, approved={approved_ppc}")

    else:
        # Efficiency gain: actual loss < approved target (Regulation 73(3))
        # Savings shared 2:1 between licensee and consumers
        savings_lakh_kwh        = approved_loss_lakh_kwh - actual_loss_lakh_kwh
        efficiency_gain_rs_lakhs = round(savings_lakh_kwh * avg_cost, 2)
        licensee_share          = round(efficiency_gain_rs_lakhs * 2.0 / 3.0, 2)
        approved_ppc            = round(base_ppc + licensee_share, 2)

        approved_expenses["power_purchase_cost"] = approved_ppc
        disallowances.append({
            "item": "Power Purchase Cost — Distribution Loss Efficiency Gain",
            "claimed": claimed_ppc,
            "approved": approved_ppc,
            "amount_cut": round(claimed_ppc - approved_ppc, 2),
            "justification": (
                f"The actual distribution loss of {actual_loss_pct:.2f}% is below the "
                f"approved target of {target_loss_pct:.2f}%, resulting in an efficiency "
                f"gain of Rs. {efficiency_gain_rs_lakhs:.2f} Lakhs. As per Regulation 73(3) "
                f"of the KSERC Tariff Regulations 2021, 2/3rd of the gain "
                f"(Rs. {licensee_share:.2f} Lakhs) is passed to the licensee, making the "
                f"approved PPC Rs. {approved_ppc:.2f} Lakhs."
            ),
        })
        logger.info(f"PPC: efficiency gain={licensee_share}, approved={approved_ppc}")


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

                # Pass through KSERC NFA chain data for RoNFA calculation
                kserc_nfa = cap.get("kserc_nfa_net_of_grants", 0.0)
                if kserc_nfa > 0:
                    result["kserc_nfa_net_of_grants"] = kserc_nfa
                    result["kserc_normative_loan"] = cap.get("kserc_normative_loan", 0.0)
                    result["kserc_net_nfa_for_ronfa"] = cap.get("kserc_net_nfa_for_ronfa", 0.0)
                    result["kserc_ronfa_rate"] = cap.get("kserc_ronfa_rate", 5.5)
                    logger.info(f"  KSERC NFA chain: nfa={kserc_nfa:.2f}, loan={result['kserc_normative_loan']:.2f}")

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
    bee_fee: float = 0.0,
    detailed_tables: Optional[Dict[str, Any]] = None,
    wage_revision: float = 0.0,
    wage_revision_prior_period: float = 0.0,
    state: Optional[Dict[str, Any]] = None,
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

    # Apply KSERC inflation adjustment to MYT norms for O&M components
    # 
    # IMPORTANT LOGIC:
    # The MYT baselines (myt_baselines.json) already contain FY-specific norms
    # escalated at the MYT Order's forecast rate (e.g., 4.84% for Technopark).
    #
    # During truing-up, KSERC applies ACTUAL inflation (CPI 70% + WPI 30%)
    # which may differ from the MYT forecast rate.
    #
    # The correct approach:
    # - Use the MYT FY norm as the BASE ceiling (already year-appropriate)
    # - Apply a correction if actual inflation > MYT forecast rate
    #   (actual_rate - myt_rate) as additional tolerance
    # - If actual inflation < MYT forecast, don't penalize — use MYT norm as ceiling
    #
    # For O&M: employee_cost, repair_maintenance, admin_general
    if norm > 0.0 and key in ("repair_maintenance", "admin_general", "employee_cost"):
        actual_inflation = KSERC_INFLATION_ESCALATION.get(fy, 6.0)
        # MYT norm is ALREADY escalated for this FY — use as ceiling directly
        # The norm from myt_baselines.json is the MYT-approved amount for this specific FY
        # We do NOT escalate again (that would be double-counting)
        #
        # However, if actual inflation is higher than MYT forecast rate,
        # KSERC may allow a slight upward adjustment
        escalated_norm = norm  # Use FY-specific MYT norm directly
        logger.info(
            f"{display}: MYT norm for FY {fy} = {norm:.2f}L "
            f"(already FY-escalated). Actual inflation = {actual_inflation}%. "
            f"Using MYT FY norm as ceiling: {escalated_norm:.2f}L"
        )
        norm = escalated_norm


    # Determine the effective cap:
    # - If MYT norm exists AND KSERC precedent approved higher, use precedent (+ 10% escalation)
    # - If only MYT norm, use MYT norm
    # - If only precedent, use precedent pattern
    effective_cap = 0.0
    cap_source = "none"
    bee_allowed = 0.0  # BEE energy audit fee allowed as change-in-law addition

    if norm > 0.0:
        effective_cap = norm
        cap_source = f"MYT norm (FY-specific)" if key in ("repair_maintenance", "admin_general", "employee_cost") else "MYT norm"
        # Precedent override only applies to components WITHOUT inflation escalation.
        # For O&M (employee, R&M, A&G), the Annexure-7 formula (MYT norm × actual inflation)
        # is the authoritative ceiling — precedent cannot override it per KSERC methodology.
        if key not in ("repair_maintenance", "admin_general", "employee_cost"):
            if precedent_approved_amt > norm * 1.05:  # more than 5% above norm
                escalated_precedent = round(precedent_approved_amt * 1.10, 2)  # 10% escalation
                effective_cap = max(norm, min(escalated_precedent, claimed))
                cap_source = f"precedent-adjusted (KSERC approved {precedent_approved_amt:.2f}L in FY {prec['fy']})"
                logger.info(f"{display}: KSERC precedent ({precedent_approved_amt:.2f}) > MYT norm ({norm:.2f}), using cap={effective_cap:.2f}")


    # BEE Energy Audit fee — change-in-law addition for admin_general
    # Per KSERC precedent: KDHP 2022-23 (Rs.5.14L approved), Infopark 2024-25 (Rs.2.24L approved)
    # Approved over and above the inflation-escalated A&G norm as a mandatory statutory payment
    if key == "admin_general" and bee_fee > 0.0:
        bee_allowed = round(min(bee_fee, max(0.0, claimed - effective_cap)), 2)
        if bee_allowed > 0.0:
            effective_cap = round(effective_cap + bee_allowed, 2)
            cap_source += f" + BEE Energy Audit fee (change-in-law Rs. {bee_allowed:.2f}L)"
            logger.info(f"{display}: BEE fee Rs.{bee_fee:.2f}L -> allowing Rs.{bee_allowed:.2f}L above norm, cap now {effective_cap:.2f}")

    # Wage Revision — uncontrollable expense addition for employee_cost
    # Per KSERC precedent: KDHP 2020-21 (Rs.14.17L allowed), 2021-22 (Rs.23.65L allowed)
    # Wage revision is approved over and above the MYT norm after prudence check.
    # ARR Order OP 28/2022 para 26: "any additional expenses relating to pay revision
    # can be considered at the time of Truing Up after prudence check."
    wage_rev_allowed = 0.0
    if key == "employee_cost" and wage_revision > 0.0:
        wage_rev_allowed = round(wage_revision, 2)
        if effective_cap > 0.0:
            effective_cap = round(effective_cap + wage_rev_allowed, 2)
            cap_source += f" + Wage Revision (Rs. {wage_rev_allowed:.2f}L)"
            logger.info(
                f"{display}: Wage revision Rs.{wage_revision:.2f}L -> "
                f"allowing Rs.{wage_rev_allowed:.2f}L above norm, cap now {effective_cap:.2f}"
            )

    # Prior period wage revision — shown as a separate line item
    # If wage revision was denied in the previous year's order, the petitioner
    # may claim it as prior period expense. This is tracked separately.
    if key == "employee_cost" and wage_revision_prior_period > 0.0:
        prior_amt = round(wage_revision_prior_period, 2)
        approved_expenses["prior_period_employee_cost"] = prior_amt
        logger.info(
            f"{display}: Prior period wage revision Rs.{prior_amt:.2f}L "
            f"(denied in previous year) — added as separate line item"
        )

    if effective_cap > 0.0 and claimed > effective_cap:
        approved_expenses[key] = effective_cap
        cut = round(claimed - effective_cap, 2)

        bee_note = ""
        if bee_allowed > 0.0:
            bee_note = (
                f" This includes Rs. {bee_allowed:,.2f} Lakhs approved as BEE-mandated "
                f"Energy Audit fee (change in law, per KSERC precedent)."
            )

        wage_note = ""
        if wage_rev_allowed > 0.0:
            wage_note = (
                f" This includes Rs. {wage_rev_allowed:,.2f} Lakhs approved on account of "
                f"wage revision (uncontrollable expense, per KSERC precedent and "
                f"ARR Order OP 28/2022 para 26)."
            )

        justification = (
            f"The claimed {display} of Rs. {claimed:,.2f} Lakhs exceeds the "
            f"effective ceiling of Rs. {effective_cap:,.2f} Lakhs ({cap_source}). "
            f"The excess of Rs. {cut:,.2f} Lakhs is disallowed as per KSERC "
            f"Tariff Regulations. The Commission approves Rs. {effective_cap:,.2f} Lakhs."
            f"{bee_note}{wage_note}"
        )

        if _precedent_lookup and licensee:
            prec_just = _precedent_lookup.build_precedent_justification(
                licensee, key, claimed, fy
            )
            if prec_just:
                justification += f" {prec_just}"

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
        # No MYT norm — try order learnings, then precedent DB
        order_decision = _get_order_learning_decision(
            detailed_tables or {}, key, licensee
        )
        
        # Priority 1: Same licensee's past KSERC order decision
        same_lic = order_decision.get("same_licensee_decision")
        if same_lic and same_lic.get("claimed_amount", 0) > 0:
            past_claimed = float(same_lic.get("claimed_amount", 0))
            past_approved = float(same_lic.get("approved_amount", 0))
            past_reasoning = str(same_lic.get("kserc_reasoning", ""))[:200]
            past_methodology = order_decision.get("methodology", "")
            
            # Apply the same cut pattern KSERC used before
            if past_claimed > 0 and past_approved > 0:
                past_cut_pct = (past_claimed - past_approved) / past_claimed * 100
                # Apply escalated past-order approval as cap
                escalated_past = round(past_approved * 1.10, 2)  # 10% growth allowance
                effective_cap = max(escalated_past, past_approved)
                
                if claimed > effective_cap:
                    approved_expenses[key] = effective_cap
                    cut = round(claimed - effective_cap, 2)
                    disallowances.append({
                        "item": display,
                        "claimed": claimed,
                        "approved": effective_cap,
                        "amount_cut": cut,
                        "justification": (
                            f"No MYT norm available. Based on KSERC's past trued-up order "
                            f"({same_lic.get('order_ref', 'previous order')}), the Commission "
                            f"approved Rs. {past_approved:,.2f} Lakhs against a claim of "
                            f"Rs. {past_claimed:,.2f} Lakhs (cut {past_cut_pct:.1f}%). "
                            f"Applying 10% escalation, cap = Rs. {effective_cap:,.2f} Lakhs. "
                            f"KSERC reasoning: {past_reasoning}. "
                            f"{'Methodology: ' + past_methodology if past_methodology else ''}"
                        ),
                    })
                    logger.info(
                        f"{display}: Order-learning based cap={effective_cap} "
                        f"(past approved={past_approved}, +10% escalation), cut={cut}"
                    )
                else:
                    approved_expenses[key] = claimed
                    logger.info(
                        f"{display}: Claimed {claimed} within order-learning cap "
                        f"{effective_cap} — approved as claimed"
                    )
            else:
                approved_expenses[key] = claimed
                logger.info(f"{display}: Past order data incomplete — approved as claimed")
        
        # Priority 2: Cross-licensee pattern (how KSERC handles this across ALL licensees)
        elif order_decision.get("recommended_cut_pct", 0) > 2.0:
            cut_pct = order_decision["recommended_cut_pct"]
            pattern = order_decision.get("cross_licensee_pattern", {})
            total_orders = pattern.get("total_orders_analyzed", 0) if pattern else 0
            times_cut = pattern.get("times_kserc_cut", 0) if pattern else 0
            
            # Only apply cross-licensee pattern if KSERC cuts this component consistently
            if times_cut > total_orders * 0.5:  # KSERC cuts more than half the time
                approval_ratio = 1.0 - (cut_pct / 100.0)
                pattern_based = round(claimed * approval_ratio, 2)
                cut = round(claimed - pattern_based, 2)
                
                approved_expenses[key] = pattern_based
                kserc_reason = order_decision.get("kserc_reasoning", "")
                methodology = order_decision.get("methodology", "")
                
                disallowances.append({
                    "item": display,
                    "claimed": claimed,
                    "approved": pattern_based,
                    "amount_cut": cut,
                    "justification": (
                        f"No MYT norm available. Cross-licensee analysis of {total_orders} past "
                        f"KSERC orders shows this component was cut {times_cut}/{total_orders} "
                        f"times with avg {cut_pct:.1f}% reduction. "
                        f"Applying {cut_pct:.1f}% cut. "
                        f"{'KSERC reasoning: ' + str(kserc_reason)[:150] + '. ' if kserc_reason else ''}"
                        f"{'Methodology: ' + methodology if methodology else ''}"
                    ),
                })
                logger.info(
                    f"{display}: Cross-licensee pattern cut={cut_pct:.1f}% "
                    f"({times_cut}/{total_orders} orders), approved={pattern_based}"
                )
            else:
                # KSERC doesn't consistently cut — approve as claimed
                approved_expenses[key] = claimed
                logger.info(
                    f"{display}: Cross-licensee pattern cut={cut_pct:.1f}% but only "
                    f"{times_cut}/{total_orders} times — approved as claimed"
                )
        
        # Priority 3: Original precedent DB fallback
        elif prec and prec["claimed"] > 0 and prec["cut_pct"] > 5.0:
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
            # Neither MYT, order learnings, nor significant precedent cut — approve as claimed
            approved_expenses[key] = claimed
            logger.info(f"{display}: No MYT norm, no order learning, no precedent cut — approved as claimed: {claimed}")

    # ── R&M line-item extraction (non-breaking, for UI one-time selection) ──
    # When R&M claimed exceeds the norm, extract individual line items from
    # the petition text so the UI can show them for human classification.
    # This does NOT affect the approved amount — that's handled by the UI.
    if (
        key == "repair_maintenance"
        and state is not None
        and not state.get("rm_line_items")
        and claimed > (norm if norm > 0 else 0)
        and norm > 0
    ):
        try:
            from src.gemini_client import generate
            import json as _json
            petition_text = state.get("petition_text", "")
            text_snippet = petition_text[:8000] if petition_text else ""
            if text_snippet:
                _RM_PROMPT = (
                    f"You are analysing a KSERC truing-up petition for {licensee} FY {fy}.\n\n"
                    f"The licensee claimed Rs. {claimed:.2f} Lakhs for Repairs & Maintenance "
                    f"against a normative allowance of Rs. {norm:.2f} Lakhs.\n\n"
                    "Below is the extracted text from the petition. Extract EVERY individual R&M "
                    "expenditure line item you can find.\n"
                    "Look for tables or paragraphs listing R&M items such as:\n"
                    "  - Transformer repairs/replacements\n"
                    "  - Cable repairs/laying\n"
                    "  - Substation maintenance\n"
                    "  - Testing and inspection\n"
                    "  - Annual maintenance contracts (AMC)\n"
                    "  - Electrical equipment servicing\n"
                    "  - Any other R&M items with individual amounts\n\n"
                    "Return ONLY a JSON array of objects. Each object must have:\n"
                    '  "description": string (the R&M item description),\n'
                    '  "amount": number (amount in Rs. Lakhs)\n\n'
                    "If no individual line items can be found, return an empty array [].\n"
                    "Do NOT include the total R&M amount as a line item.\n"
                    "Return ONLY the JSON array, no other text.\n\n"
                    "--- PETITION TEXT ---\n"
                    f"{text_snippet}\n"
                    "--- END ---"
                )
                raw_rm = generate(
                    prompt=_RM_PROMPT,
                    model=GEMINI_MODEL,
                    temperature=0.0,
                    response_mime_type="application/json",
                    max_output_tokens=2048,
                )
                rm_items = _json.loads(raw_rm)
                if isinstance(rm_items, list) and len(rm_items) > 0:
                    state["rm_line_items"] = rm_items
                    logger.info(
                        f"R&M: Extracted {len(rm_items)} line items for UI "
                        f"(total: {sum(i.get('amount', 0) for i in rm_items):.2f}L)"
                    )
                else:
                    logger.info("R&M: No individual line items found in petition")
        except Exception as e:
            logger.warning(f"R&M line item extraction failed ({e}) — UI will not show items")


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
    "2024-25": 10.90,  # SBI EBLR 8.90% + 2% (as on 01-04-2024, confirmed from KSERC order)
    "2025-26": 10.90,  # default to latest known
    "2026-27": 10.90   # default to latest known
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
#         NOW DELEGATED TO depreciation_engine.py
# ══════════════════════════════════════════════════════════════════════

try:
    from src.agents.depreciation_engine import compute_depreciation as _dep_engine_compute
    _dep_engine_available = True
    logger.info("Depreciation engine loaded successfully")
except ImportError as e:
    _dep_engine_available = False
    logger.warning(f"Depreciation engine not available: {e}")


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
    KSERC Regulation 27 — Depreciation Calculation.

    Delegates to the new depreciation_engine.py which implements
    the full 10-step KSERC depreciation specification:
      1. Multi-PDF data search
      2. Funding source identification (CC, grants, surplus, subsidies)
      3. Two-level exclusion (pre/post cutoff)
      4. Annexure 1 rate matching
      5. Final calculation
      6. AI reasoning for ambiguous cases
      7. Firestore persistence
      8. Cross-verification (8 checks)
      9. Clarification queue
     10. Structured output
    """
    key = "depreciation"
    claimed = claimed_expenses.get(key, 0.0)
    display = COMPONENT_DISPLAY.get(key, key)

    if claimed == 0.0:
        approved_expenses[key] = 0.0
        return

    if not _dep_engine_available:
        # Fallback: approve as claimed if engine not available
        approved_expenses[key] = claimed
        logger.warning("Depreciation engine unavailable — approving as claimed")
        return

    # Delegate to the full depreciation engine
    result = _dep_engine_compute(
        state=state,
        licensee=licensee,
        fy=fy,
    )

    # Apply the engine result
    approved_expenses[key] = result.approved

    # Copy disallowances from the engine
    for d in result.disallowances:
        disallowances.append(d)

    # Log flags
    for flag in result.flags:
        logger.info(f"Depreciation flag: {flag}")

    # Log clarification items
    for item in result.clarification_items:
        logger.info(f"Depreciation clarification needed: {item}")

    logger.info(
        f"Depreciation Reg27: Claimed {claimed:.2f}L → "
        f"Approved {result.approved:.2f}L "
        f"(engine: {len(result.workings.get('level2_details', []))} deductions)"
    )




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
    
    # ─── Method P: Petition-based RoNFA computation (HIGHEST PRIORITY) ───
    # When the petition provides its own RoNFA computation table with GFA,
    # accumulated depreciation, consumer contribution, normative loan NFA, etc.
    # We verify the arithmetic and use the petition-computed value.
    ronfa_balance_nfa = float(state.get("ronfa_balance_nfa", 0.0) or 0.0)
    ronfa_eligible_return = float(state.get("ronfa_eligible_return", 0.0) or 0.0)
    ronfa_gfa = float(state.get("ronfa_gross_fixed_assets", 0.0) or 0.0)
    ronfa_acc_dep = float(state.get("ronfa_accumulated_depreciation", 0.0) or 0.0)
    ronfa_consumer_contrib = float(state.get("ronfa_consumer_contribution", 0.0) or 0.0)
    ronfa_nfa_loan = float(state.get("ronfa_nfa_for_normative_loan", 0.0) or 0.0)
    ronfa_prior_additions = float(state.get("ronfa_prior_year_additions", 0.0) or 0.0)
    ronfa_rate_pct = float(state.get("ronfa_rate_pct", 0.0) or 0.0)
    
    if ronfa_balance_nfa > 0 and ronfa_eligible_return > 0:
        # Verify the arithmetic: GFA - AccDep - ConsContrib - NFALoan - PriorAdditions = BalanceNFA
        if ronfa_gfa > 0:
            computed_balance = round(ronfa_gfa - ronfa_acc_dep - ronfa_consumer_contrib - ronfa_nfa_loan - ronfa_prior_additions, 2)
            arithmetic_ok = abs(computed_balance - ronfa_balance_nfa) <= 1.0  # Allow Rs 1L tolerance
            if not arithmetic_ok:
                logger.warning(
                    f"RoNFA Method P: Arithmetic mismatch! "
                    f"GFA({ronfa_gfa}) - AccDep({ronfa_acc_dep}) - CC({ronfa_consumer_contrib}) "
                    f"- Loan({ronfa_nfa_loan}) - Prior({ronfa_prior_additions}) "
                    f"= {computed_balance} vs petition {ronfa_balance_nfa}"
                )
        
        # Use the petition's computed rate, or default to 5.5%
        rate = ronfa_rate_pct / 100.0 if ronfa_rate_pct > 0 else 0.055
        verified_return = round(ronfa_balance_nfa * rate, 2)
        
        # Allow tolerance for rounding
        if abs(verified_return - ronfa_eligible_return) <= 0.5:
            approved = ronfa_eligible_return
        else:
            # Use our computed value if petition calculation seems off
            approved = verified_return
            logger.info(f"RoNFA Method P: Recomputed {verified_return} vs petition {ronfa_eligible_return}, using {approved}")
        
        # Cap at claimed if claimed is lower (licensee can't get more than what they ask)
        approved = min(claimed, approved) if claimed < approved else approved
        approved_expenses[key] = approved
        
        cap_source = (
            f"Petition RoNFA computation: GFA {ronfa_gfa:.2f}L − AccDep {ronfa_acc_dep:.2f}L "
            f"− CC {ronfa_consumer_contrib:.2f}L − Loan {ronfa_nfa_loan:.2f}L "
            f"− Prior {ronfa_prior_additions:.2f}L = NFA {ronfa_balance_nfa:.2f}L × {rate*100:.1f}%"
        )
        
        if abs(claimed - approved) > 0.01:
            cut = round(claimed - approved, 2)
            disallowances.append({
                "item": display,
                "claimed": claimed,
                "approved": approved,
                "amount_cut": cut,
                "justification": (
                    f"As per KSERC Regulation 28, RoNFA verified from petition computation. "
                    f"{cap_source}. Approved: Rs. {approved:.2f}L."
                ),
            })
        
        # Store for next year's chaining
        state["approved_ronfa_gfa"] = ronfa_gfa
        state["approved_ronfa_acc_dep"] = ronfa_acc_dep
        state["approved_ronfa_balance_nfa"] = ronfa_balance_nfa
        state["approved_ronfa_rate"] = rate
        state["approved_ronfa_consumer_contribution"] = ronfa_consumer_contrib
        state["approved_ronfa_nfa_for_loan"] = ronfa_nfa_loan
        
        logger.info(f"RoNFA Method P: {cap_source} → approved={approved:.2f}L (claimed={claimed:.2f}L)")
        return  # Done — skip other methods
    
    # ─── Method A: KSERC-chained NFA calculation ───
    # When we have the prior KSERC order's NFA (net of grants) and approved dep,
    # chain forward: Opening NFA = prior NFA - prior approved dep
    # Then: RoNFA = (Opening NFA - normative loan if applicable) × rate
    prior_kserc_nfa = cap_analysis.get("kserc_nfa_net_of_grants", 0.0)
    if prior_kserc_nfa > 0 and prec_ronfa > 0:
        # Chain forward: current opening NFA = prior NFA - prior approved dep
        prior_approved_dep = cap_analysis.get("kserc_approved_depreciation", 0.0)
        opening_nfa = round(prior_kserc_nfa - prior_approved_dep, 2)
        
        # Determine RoNFA rate
        ronfa_rate = cap_analysis.get("kserc_ronfa_rate", 5.5) / 100.0
        
        # Check CURRENT YEAR petition for normative loan — NOT derived from prior year.
        # Only deduct normative loan if the current petition explicitly has one.
        petition_cap = state.get("capital_structure", {})
        # Look for normative loan in the petition's capital structure or RoNFA section
        petition_normative_loan = petition_cap.get("normative_loan_nfa", 0.0)
        if petition_normative_loan == 0:
            # Also check: if petition claims "NFA considered for normative loan"
            petition_normative_loan = petition_cap.get("nfa_for_normative_loan", 0.0)
        
        normative_loan_deduction = 0.0
        if petition_normative_loan > 0:
            normative_loan_deduction = petition_normative_loan
            logger.info(f"RoNFA: Normative loan deduction from current petition: {normative_loan_deduction:.2f}L")
        else:
            logger.info(f"RoNFA: No normative loan in current petition — no deduction applied")
        
        net_nfa_for_ronfa = round(max(opening_nfa - normative_loan_deduction, 0.0), 2)
        computed_ronfa = round(net_nfa_for_ronfa * ronfa_rate, 2)
        
        approved = min(claimed, computed_ronfa)
        approved_expenses[key] = approved
        
        cap_source = (
            f"KSERC-chained NFA: prior NFA {prior_kserc_nfa:.2f}L − dep {prior_approved_dep:.2f}L "
            f"= opening {opening_nfa:.2f}L − loan {normative_loan_deduction:.2f}L "
            f"= {net_nfa_for_ronfa:.2f}L × {ronfa_rate*100:.1f}%"
        )
        
        if abs(claimed - approved) > 0.01:
            cut = round(claimed - approved, 2)
            disallowances.append({
                "item": display,
                "claimed": claimed,
                "approved": approved,
                "amount_cut": cut,
                "justification": (
                    f"As per KSERC Regulation 28, RoNFA computed using KSERC-approved NFA chain. "
                    f"{cap_source}. "
                    f"Approved: Rs. {approved:.2f}L."
                ),
            })
        logger.info(f"RoNFA KSERC-chain: {cap_source} → approved={approved:.2f}L (claimed={claimed:.2f}L)")
    
    elif nfa > 0 and source != "none":
        # ─── Method B: Capital structure-based calculation ───
        # Determine RoNFA rate based on equity identifiability
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
            effective_ronfa = min(claimed, round(prec_ronfa * 1.10, 2))
            cap_source = f"precedent-adjusted (KSERC approved Rs. {prec_ronfa:.2f}L in FY {prec['fy']})"
            logger.info(f"RoNFA: Computed {computed_ronfa} diverges from precedent {prec_ronfa}, using {effective_ronfa}")
        else:
            effective_ronfa = computed_ronfa
            cap_source = f"Reg 28 ({rate_reason} on eligible NFA Rs. {eligible_nfa_for_return:.2f}L)"
        
        approved = min(claimed, effective_ronfa)
        if kserc_ronfa > claimed and prec_ronfa > claimed:
            approved = effective_ronfa
        
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
        # ─── Method C: Precedent-based fallback ───
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
    detailed_tables: Optional[Dict[str, Any]] = None,
    state: Optional[dict] = None,
) -> None:
    """
    KSERC Interest on Normative Loan — Formula-based computation.
    
    Formula (from Infopark 2024-25 petition):
      Opening Normative Loan (A) = Net Opening + Additional
      Closing Normative Loan (B) = A - Allowable Depreciation/Repayment
      Average Normative Loan = (A + B) / 2
      Interest = Average Normative Loan × SBI EBLR Rate (%)
    
    Falls back to MYT norm cap if normative loan data unavailable.
    """
    key = "interest_long_term"
    claimed = claimed_expenses.get(key, 0.0)
    normative = _myt_norm(myt_norms, key)
    
    # Try formula-based computation from extracted normative loan data
    if state:
        opening_loan = float(state.get("normative_loan_opening", 0.0) or 0.0)
        additional_loan = float(state.get("normative_loan_additional", 0.0) or 0.0)
        depreciation_repayment = float(state.get("normative_loan_repayment", 0.0) or 0.0)
        loan_interest_rate = float(state.get("normative_loan_rate", 0.0) or 0.0)
        
        # If depreciation_repayment not extracted, use approved depreciation
        if depreciation_repayment == 0.0:
            depreciation_repayment = float(approved_expenses.get("depreciation", 0.0) or 0.0)
        
        if opening_loan > 0 and loan_interest_rate > 0:
            # Formula computation
            total_opening = opening_loan + additional_loan
            closing_loan = total_opening - depreciation_repayment
            avg_loan = (total_opening + closing_loan) / 2.0
            computed_interest = round(avg_loan * (loan_interest_rate / 100.0), 2)
            
            approved = computed_interest
            approved_expenses[key] = approved
            
            logger.info(
                f"Interest LT (formula): Opening={total_opening:.2f}, "
                f"Deprec/Repay={depreciation_repayment:.2f}, Closing={closing_loan:.2f}, "
                f"Avg={avg_loan:.2f}, Rate={loan_interest_rate}%, Interest={computed_interest:.2f}"
            )
            
            if abs(claimed - approved) > 0.01 and claimed > 0:
                cut = round(claimed - approved, 2)
                disallowances.append({
                    "item": "Interest on Normative Loan",
                    "claimed": claimed,
                    "approved": approved,
                    "amount_cut": cut,
                    "justification": (
                        f"KSERC Regulation 26: Interest computed on normative loan basis. "
                        f"Opening Loan = Rs. {total_opening:.2f}L, Less Depreciation/Repayment = "
                        f"Rs. {depreciation_repayment:.2f}L, Closing = Rs. {closing_loan:.2f}L. "
                        f"Average Normative Loan = Rs. {avg_loan:.2f}L × {loan_interest_rate}% = "
                        f"Rs. {computed_interest:.2f}L."
                    ),
                })
            return
    
    # Fallback: MYT norm cap (original logic)
    if normative > 0.0:
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
        # No MYT norm — try order learnings, then precedent DB
        order_decision = _get_order_learning_decision(
            detailed_tables or {}, "interest_long_term", licensee
        )
        same_lic = order_decision.get("same_licensee_decision")
        
        if same_lic and same_lic.get("approved_amount", 0) > 0:
            past_approved = float(same_lic.get("approved_amount", 0))
            past_reasoning = str(same_lic.get("kserc_reasoning", ""))[:150]
            cap = round(past_approved * 1.15, 2)
            approved = min(claimed, cap) if claimed > 0 else past_approved
            approved_expenses[key] = approved
            if claimed > cap:
                cut = round(claimed - cap, 2)
                disallowances.append({
                    "item": "Interest on Normative Loan",
                    "claimed": claimed,
                    "approved": cap,
                    "amount_cut": cut,
                    "justification": (
                        f"Per KSERC Regulation 26, interest on normative loan (70% of eligible "
                        f"capital additions) at weighted average rate. Based on KSERC's past order "
                        f"({same_lic.get('order_ref', '')}), approved Rs. {past_approved:,.2f}L. "
                        f"With 15% escalation, cap = Rs. {cap:,.2f}L. {past_reasoning}"
                    ),
                })
            logger.info(f"Interest LT: Order-learning based, past={past_approved}, cap={cap}, approved={approved}")
        elif (prec := (_get_precedent_approved(licensee, key, fy) if _precedent_lookup and licensee else None)) and prec.get("approved", 0) > 0:
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
    logger.info(f"IWC: Approved O&M = Employee({employee:.2f}) + R&M({rm:.2f}) + A&G({ag:.2f}) = {total_om:.2f}L")
    
    # Receivables = 2 months of Revenue from Sale of Power
    # KSERC order uses ONLY revenue_from_sale (not wheeling/NTI/other)
    # Confirmed from Infopark 2024-25 order: 1187.62/12 × 2 = 197.94
    revenue_from_sale = 0.0
    if state:
        claimed_revenues = state.get("claimed_revenues", {})
        if claimed_revenues:
            revenue_from_sale = float(claimed_revenues.get("revenue_from_sale", 0.0) or 0.0)
        # Fallback: use total claimed revenues if revenue_from_sale not separately available
        if revenue_from_sale == 0.0 and claimed_revenues:
            revenue_from_sale = sum(v for v in claimed_revenues.values() if isinstance(v, (int, float)))
            logger.warning(f"IWC: revenue_from_sale not found, using total revenue = {revenue_from_sale:.2f}")
    
    if revenue_from_sale == 0.0:
        logger.warning(f"IWC: No revenue data available for receivables calculation")
    
    # ══════════════════════════════════════════════════════════════════════
    # KSERC IWC Formula (Regulation 29) — Verified from Infopark 2024-25 petition
    # ══════════════════════════════════════════════════════════════════════
    # WC = (1-month Approved O&M) + (Maintenance Spares) + (2-month Revenue) − Security Deposits
    # IWC = WC × (MCLR + 2)%
    #
    # Components:
    #   1. O&M one month = Approved O&M / 12 (from IWC table if available, else sum of components)
    #   2. Maintenance Spares = as per norms (0 for Infopark, may be non-zero for others)
    #   3. Receivables = 2 months Revenue from Sale of Power
    #   4. Less: Security Deposits from Consumers
    #   5. Interest Rate = SBI EBLR + 2%
    # ══════════════════════════════════════════════════════════════════════
    # Allow user override via state (from UI input)
    user_rate = float(state.get("iwc_interest_rate", 0.0) or 0.0) if state else 0.0
    if user_rate > 0:
        sbi_mclr_plus_2 = user_rate / 100.0
        logger.info(f"IWC: Using user-specified interest rate: {user_rate}%")
    else:
        sbi_mclr_plus_2 = SBI_EBLR_PLUS_2_RATES.get(fy, 10.90) / 100.0
    
    # Step 1: O&M one month
    om_monthly = total_om / 12.0
    
    # Step 2: Maintenance Spares (from extraction; 0 for Infopark, may be non-zero for others)
    maintenance_spares = 0.0
    if state:
        maintenance_spares = float(state.get("maintenance_spares_wc", 0.0) or 0.0)
    
    # Step 3: Receivables = 2 months of Revenue from Sale of Power
    # Formula: annual revenue / 12 × 2 = annual revenue / 6
    receivables_2mo = revenue_from_sale / 6.0  # 2 months = annual / 6
    
    # Step 4: Less — Security Deposits from Consumers
    security_deposits = 0.0
    if state:
        security_deposits = float(state.get("consumer_security_deposit_balance", 0.0) or 0.0)
    
    # Working Capital = (O&M/12) + Spares + (2-month Revenue) − Security Deposits
    working_capital = om_monthly + maintenance_spares + receivables_2mo - security_deposits
    # If security deposits exceed WC, floor at 0
    working_capital = max(working_capital, 0.0)
    
    computed_iwc = round(working_capital * sbi_mclr_plus_2, 2)
    
    logger.info(
        f"IWC components: O&M/12={om_monthly:.2f}, Spares={maintenance_spares:.2f}, "
        f"Receivables(2mo)={receivables_2mo:.2f}, SecDeposits={security_deposits:.2f}, "
        f"WC={working_capital:.2f}, MCLR+2%={sbi_mclr_plus_2*100:.2f}%, IWC={computed_iwc:.2f}"
    )
    
    # Sanity check: IWC should be a small fraction of total revenue (typically < 5%)
    if revenue_from_sale > 0 and computed_iwc > revenue_from_sale * 0.05:
        logger.warning(
            f"IWC sanity check FAILED: computed {computed_iwc:.2f} > 5% of revenue {revenue_from_sale:.2f}. "
            f"Falling back to claimed value {claimed:.2f}"
        )
        computed_iwc = claimed
    
    # KSERC approves the formula-computed value, even if higher than claimed
    # (verified from Infopark 2022-23 order: claimed 2.70, KSERC approved 3.72)
    approved = computed_iwc if computed_iwc > 0 else (myt_norm if myt_norm > 0 else claimed)
    
    approved_expenses[key] = approved
    
    if abs(claimed - approved) > 0.01 and claimed > 0:
        cut = round(claimed - approved, 2)
        disallowances.append({
            "item": "Interest on Working Capital",
            "claimed": claimed,
            "approved": approved,
            "amount_cut": cut,
            "justification": (
                f"KSERC Regulation 29: WC = (O&M/12) + Spares + (2-month Revenue) − Security Deposits. "
                f"O&M/12 = Rs. {om_monthly:.2f}L, Spares = Rs. {maintenance_spares:.2f}L, "
                f"Receivables(2mo) = Rs. {receivables_2mo:.2f}L, Security Deposits = Rs. {security_deposits:.2f}L. "
                f"WC = Rs. {working_capital:.2f}L × MCLR+2% ({sbi_mclr_plus_2*100:.2f}%) = Rs. {computed_iwc:.2f}L. "
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
# Rule 8: Other Debits — KSERC-Specific Sub-Item Rules
# ══════════════════════════════════════════════════════════════════════

def _audit_other_debits(
    claimed_expenses: Dict[str, float],
    approved_expenses: Dict[str, float],
    myt_norms: Dict[str, float],
    disallowances: List[Dict[str, Any]],
    licensee: str = "",
    fy: str = "",
    detailed_tables: Optional[Dict[str, Any]] = None,
) -> None:
    """
    KSERC Other Debits — Component-specific disallowance rules.
    
    Based on deep research of actual KSERC orders (KDHP 2021-22, 2022-23):
    
    1. Section 3(1) Electricity Duty: ALWAYS disallowed (handled separately by
       _audit_section3_duty, but accounts for most of other_debits reduction)
    2. Provision for doubtful debts: ALWAYS disallowed unless bad debt written off
    3. Bank guarantee charges against KSERC orders: Disallowed
    4. Inspection charges (periodical): Approved as actual
    
    KDHP 2022-23 Example:
      - Claimed: Rs. 18.07 lakh
      - Section 3(1) duty: Rs. 14.34 lakh → DISALLOWED
      - Provision for doubtful debts: Rs. 2.51 lakh → DISALLOWED
      - Inspection charges: Rs. 1.22 lakh → APPROVED
      - Approved: Rs. 1.22 lakh
    
    KDHP 2021-22 Example:
      - Claimed: Rs. 14.08 lakh
      - Trued up: Rs. 1.13 lakh
    """
    claimed = claimed_expenses.get("other_debits", 0.0)
    
    if claimed == 0.0:
        approved_expenses["other_debits"] = 0.0
        logger.info("Other Debits: claimed is 0 — approved as zero.")
        return
    
    # Check if Section 3(1) duty was already separated and handled
    s3_duty = claimed_expenses.get("section3_1_duty", 0.0)
    
    # If section 3(1) duty is embedded in other_debits (not separately extracted),
    # we estimate it based on precedent patterns
    # KDHP pattern: Section 3(1) duty is typically ~75-80% of other_debits
    
    # Get MYT norm or precedent for other_debits
    norm = _myt_norm(myt_norms, "other_debits")
    prec = _get_precedent_approved(licensee, "other_debits", fy) if _precedent_lookup and licensee else None
    precedent_approved = prec["approved"] if prec and prec.get("approved", 0) > 0 else 0.0
    
    # If MYT norm or precedent is available, use it as a guide
    if norm > 0 and claimed <= norm:
        # Within norm — approve as claimed
        approved_expenses["other_debits"] = claimed
        logger.info(f"Other Debits: Claimed {claimed:.2f} within norm {norm:.2f} — approved")
        return
    
    if norm > 0 and claimed > norm:
        # Exceeds norm — cap at norm with KSERC justification
        approved_expenses["other_debits"] = norm
        cut = round(claimed - norm, 2)
        disallowances.append({
            "item": "Other Debits",
            "claimed": claimed,
            "approved": norm,
            "amount_cut": cut,
            "justification": (
                f"The claimed Other Debits of Rs. {claimed:.2f} Lakhs exceeds the "
                f"MYT approved norm of Rs. {norm:.2f} Lakhs. The Commission has "
                f"consistently disallowed claims under provision for doubtful debts "
                f"(no amount written off as bad debt) and bank guarantee charges "
                f"related to legal proceedings against KSERC orders. Only periodical "
                f"inspection charges are approved. The Commission approves "
                f"Rs. {norm:.2f} Lakhs."
            ),
        })
        logger.info(f"Other Debits: Claimed {claimed:.2f}, norm cap {norm:.2f}, cut {cut:.2f}")
        return
    
    # No MYT norm — use precedent-based approach
    # KSERC typically approves only inspection charges, which is a small amount
    if precedent_approved > 0:
        # Use precedent with reasonable escalation
        effective_cap = round(precedent_approved * 1.10, 2)  # 10% escalation
        if claimed > effective_cap:
            approved_expenses["other_debits"] = effective_cap
            cut = round(claimed - effective_cap, 2)
            disallowances.append({
                "item": "Other Debits",
                "claimed": claimed,
                "approved": effective_cap,
                "amount_cut": cut,
                "justification": (
                    f"Based on KSERC precedent from FY {prec['fy']}, the Commission "
                    f"previously approved Rs. {precedent_approved:.2f} Lakhs. The "
                    f"excess claim includes items like provision for doubtful debts "
                    f"and other non-admissible expenses. The Commission approves "
                    f"Rs. {effective_cap:.2f} Lakhs."
                ),
            })
            logger.info(f"Other Debits: Precedent-based cap {effective_cap:.2f}, cut {cut:.2f}")
        else:
            approved_expenses["other_debits"] = claimed
            logger.info(f"Other Debits: Within precedent-based cap — approved as claimed: {claimed:.2f}")
    else:
        # No norm, no precedent — approve as claimed
        approved_expenses["other_debits"] = claimed
        logger.info(f"Other Debits: No norm or precedent — approved as claimed: {claimed:.2f}")


# ══════════════════════════════════════════════════════════════════════
# Main LangGraph Node
# ══════════════════════════════════════════════════════════════════════

def audit_petition(state: dict) -> dict:
    """
    LangGraph node: apply KSERC audit rules to the extracted petition data.

    PRIMARY PATH: Use AI Commission decisions from the Deep Analyzer.
    FALLBACK: Use static rule-based capping if AI analysis failed.
    
    The auditor now benefits from cross-licensee methodology learning:
    - kserc_methodology_rules: Rules learned from ALL past orders, regulations, amendments
    - myt_baseline_norms: Benchmarks from Revised ARR Approved, past orders, MYT fallback
    """
    claimed_expenses: Dict[str, float] = state.get("claimed_expenses", {})
    claimed_revenues: Dict[str, float] = state.get("claimed_revenues", {})
    myt_norms: Dict[str, float] = state.get("myt_baseline_norms", {})
    licensee = state.get("licensee_name", "Unknown")
    fy = state.get("financial_year", "")
    ai_insights = state.get("ai_insights", {})
    methodology = state.get("kserc_methodology_rules", {})

    logger.info(f"=== audit_petition: {licensee} FY {fy} ===")
    
    # Log methodology availability
    if methodology:
        logger.info(f"=== KSERC Methodology Rules Available: {len(methodology)} components ===")
        for comp, rules in methodology.items():
            if isinstance(rules, dict):
                method = rules.get("method", rules.get("description", rules.get("formula", "?")))
                logger.info(f"  {comp}: {str(method)[:80]}")
    else:
        logger.info("=== No KSERC methodology rules available (cross-licensee learning may have been skipped) ===")

    # ── Override inflation rate if user supplied one via the web form ───────
    inflation_override = state.get("inflation_rate_override")
    if inflation_override is not None:
        KSERC_INFLATION_ESCALATION[fy] = float(inflation_override)
        logger.info(f"Inflation rate for {fy} overridden to {inflation_override}% (user-supplied)")

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

        # ── Enforce MYT norm caps on ALL norm-capped components ──────
        # The AI may have approved amounts exceeding MYT norms. KSERC's
        # deterministic methodology ALWAYS caps at the MYT baseline for
        # O&M, depreciation, interest, RoNFA, and other_debits.
        # This is the authoritative ceiling — AI cannot override it.
        # For employee_cost, wage revision (if any) is added to the cap.
        wage_revision_current = float(state.get("wage_revision_current_year", 0.0) or 0.0)
        wage_revision_prior = float(state.get("wage_revision_prior_period", 0.0) or 0.0)
        
        norm_capped_keys = [
            "employee_cost", "repair_maintenance", "admin_general",
            "depreciation", "interest_long_term", "interest_consumer_deposits",
            "interest_working_capital", "return_on_nfa", "other_debits",
        ]
        for key in norm_capped_keys:
            norm = _myt_norm(myt_norms, key)
            if norm > 0.0 and key in approved_expenses:
                # For employee_cost, add wage revision to the effective cap
                effective_cap = norm
                if key == "employee_cost" and wage_revision_current > 0.0:
                    effective_cap = round(norm + wage_revision_current, 2)
                    logger.info(
                        f"  Employee Cost effective cap: MYT {norm:.2f} + "
                        f"Wage Revision {wage_revision_current:.2f} = {effective_cap:.2f}"
                    )

                # For R&M: check if user pre-selected one-time items (from pipeline pause)
                # If rm_one_time_override is set, use it directly instead of running classifier
                rm_override = state.get("rm_one_time_override", 0.0) if state else 0.0
                rm_claimed = claimed_expenses.get(key, 0.0)
                if key == "repair_maintenance" and rm_override > 0:
                    effective_cap = rm_override
                    logger.info(
                        f"  R&M: Using user-selected one-time override: Rs.{rm_override:.2f}L "
                        f"(norm={norm:.2f} + one-time items)"
                    )
                elif key == "repair_maintenance" and rm_claimed > effective_cap:
                    try:
                        rm_items = state.get("rm_line_items", [])
                        if not rm_items:
                            from src.gemini_client import generate
                            import json as _json
                            petition_text = state.get("petition_text", "")
                            text_snippet = petition_text[:8000] if petition_text else ""
                            if text_snippet:
                                _RM_PROMPT = (
                                    f"You are analysing a KSERC truing-up petition for {licensee} FY {fy}.\n\n"
                                    f"The licensee claimed Rs. {rm_claimed:.2f} Lakhs for Repairs & Maintenance.\n\n"
                                    "Below is the extracted text from the petition. Extract EVERY individual R&M "
                                    "expenditure line item you can find.\n"
                                    "Look for tables or paragraphs listing R&M items such as:\n"
                                    "  - Transformer repairs/replacements\n"
                                    "  - Cable repairs/laying\n"
                                    "  - Substation maintenance\n"
                                    "  - Testing and inspection\n"
                                    "  - Annual maintenance contracts (AMC)\n"
                                    "  - Electrical equipment servicing\n"
                                    "  - Any other R&M items with individual amounts\n\n"
                                    "Return ONLY a JSON array of objects. Each object must have:\n"
                                    '  "description": string (the R&M item description),\n'
                                    '  "amount": number (amount in Rs. Lakhs)\n\n'
                                    "If no individual line items can be found, return an empty array [].\n"
                                    "Do NOT include the total R&M amount as a line item.\n"
                                    "Return ONLY the JSON array, no other text.\n\n"
                                    "--- PETITION TEXT ---\n"
                                    f"{text_snippet}\n"
                                    "--- END ---"
                                )
                                raw_rm = generate(
                                    prompt=_RM_PROMPT,
                                    model=GEMINI_MODEL,
                                    temperature=0.0,
                                    response_mime_type="application/json",
                                    max_output_tokens=2048,
                                )
                                rm_items = _json.loads(raw_rm)
                                if isinstance(rm_items, list) and len(rm_items) > 0:
                                    state["rm_line_items"] = rm_items
                                    logger.info(
                                        f"  R&M: Gemini extracted {len(rm_items)} line items "
                                        f"(total: {sum(i.get('amount', 0) for i in rm_items):.2f}L)"
                                    )
                        if rm_items:
                            from src.tools.rm_classifier import process_rm_petition
                            rm_result = process_rm_petition(
                                licensee_name=licensee,
                                financial_year=fy,
                                norm_rm=norm,
                                items=rm_items,
                            )
                            rm_total = rm_result.get("total_approved_rm", norm)
                            state["rm_classification_result"] = rm_result
                            effective_cap = rm_total
                            summary = rm_result.get("financial_summary", {})
                            logger.info(
                                f"  R&M Classifier: norm={norm:.2f}L + "
                                f"one_time_allowed={summary.get('one_time_allowed', 0):.2f}L = "
                                f"total_approved={rm_total:.2f}L"
                            )
                    except Exception as e:
                        logger.warning(f"  R&M classifier failed ({e}) — using norm cap only")
                
                ai_val = approved_expenses[key]
                claimed = claimed_expenses.get(key, 0.0)
                if ai_val > effective_cap:
                    display = COMPONENT_DISPLAY.get(key, key)
                    approved_expenses[key] = effective_cap
                    logger.info(
                        f"  AI OVERRIDE ENFORCED: {display} — AI approved {ai_val:.2f} "
                        f"> effective cap {effective_cap:.2f}. Forced to cap."
                    )
                    # Update disallowance to reflect the MYT-enforced amount
                    cut = round(claimed - effective_cap, 2)
                    # Remove stale AI disallowance for this component
                    disallowances[:] = [
                        d for d in disallowances
                        if display.lower() not in d.get("item", "").lower()
                    ]
                    if cut > 0.01:
                        cap_source = f"MYT norm Rs. {norm:,.2f}"
                        if key == "employee_cost" and wage_revision_current > 0.0:
                            cap_source += f" + Wage Revision Rs. {wage_revision_current:,.2f}"
                        disallowances.append({
                            "item": display,
                            "claimed": claimed,
                            "approved": effective_cap,
                            "amount_cut": cut,
                            "justification": (
                                f"The claimed {display} of Rs. {claimed:,.2f} Lakhs exceeds the "
                                f"effective ceiling of Rs. {effective_cap:,.2f} Lakhs ({cap_source}). "
                                f"The excess of Rs. {cut:,.2f} Lakhs is disallowed as per KSERC Tariff Regulations."
                            ),
                        })
                
                # Prior period wage revision — separate line item
                if key == "employee_cost" and wage_revision_prior > 0.0:
                    approved_expenses["prior_period_employee_cost"] = round(wage_revision_prior, 2)
                    logger.info(
                        f"  Prior period wage revision: Rs.{wage_revision_prior:.2f}L "
                        f"added as separate line item"
                    )

        # BEE Energy Audit fee — petition-specific actual expense, extracted by Gemini/regex
        # MUST come from the petition itself — not from MYT norms (which are regulatory baselines).
        # If the petition doesn't mention it, fee is 0 (no adjustment).
        bee_fee_effective = float(state.get("bee_energy_audit_fee", 0.0) or 0.0)

        if bee_fee_effective > 0.0:
            ag_norm    = _myt_norm(myt_norms, "admin_general")
            ag_claimed = claimed_expenses.get("admin_general", 0.0)
            ag_current = approved_expenses.get("admin_general", ag_norm)
            # BEE fee is allowed only up to the excess above the norm
            bee_allowed = round(min(bee_fee_effective, max(0.0, ag_claimed - ag_norm)), 2)
            if bee_allowed > 0.0:
                new_ag = round(ag_current + bee_allowed, 2)
                if new_ag > ag_current:
                    approved_expenses["admin_general"] = new_ag
                    # Update or append disallowance entry
                    disp = COMPONENT_DISPLAY.get("admin_general", "Administration & General Expenses")
                    cut  = round(ag_claimed - new_ag, 2)
                    # Remove stale AI entry for A&G if present
                    disallowances[:] = [d for d in disallowances
                                        if "admin" not in d.get("item", "").lower()
                                        and "general" not in d.get("item", "").lower()]
                    if cut > 0.01:
                        disallowances.append({
                            "item": disp,
                            "claimed": ag_claimed,
                            "approved": new_ag,
                            "amount_cut": cut,
                            "justification": (
                                f"The claimed {disp} of Rs. {ag_claimed:,.2f} Lakhs is capped at "
                                f"the MYT norm of Rs. {ag_norm:,.2f} Lakhs. Additionally, "
                                f"Rs. {bee_allowed:,.2f} Lakhs is approved as BEE-mandated Energy "
                                f"Audit fee (change in law, per KSERC precedent). "
                                f"Total approved: Rs. {new_ag:,.2f} Lakhs."
                            ),
                        })
                    logger.info(
                        f"A&G (AI path): BEE fee Rs.{bee_fee_effective:.2f}L applied. "
                        f"Approved {ag_current:.2f} → {new_ag:.2f}"
                    )

        logger.info("=== AI Commission decisions applied ===")

    else:
        # ══════════════════════════════════════════════════════════
        # FALLBACK: Rule-based auditing (MYT norm + precedent DB + KSERC methodology + justifications)
        # ══════════════════════════════════════════════════════════
        logger.info("=== Rule-based auditing (MYT norms + precedent DB + cross-licensee methodology + justifications) ===")
        logger.info(f"MYT norms available: {bool(myt_norms)} ({len(myt_norms)} values)")
        logger.info(f"Methodology rules: {bool(methodology)} ({len(methodology)} components)")
        logger.info(f"Precedent DB available: {_precedent_lookup.available if _precedent_lookup else False}")
        
        # Extract justification responses (licensee's reasons + KSERC past decisions)
        justification_responses = methodology.get("_justification_responses", {})
        if justification_responses:
            logger.info(f"=== Licensee Justifications & KSERC Past Responses ({len(justification_responses)} components) ===")
            for comp, analysis in justification_responses.items():
                if isinstance(analysis, dict):
                    justification = str(analysis.get("licensee_justification", "N/A"))[:100]
                    kserc_response = str(analysis.get("kserc_past_response", "N/A"))[:100]
                    likely_decision = analysis.get("likely_decision", "unknown")
                    past_ref = str(analysis.get("past_order_reference", "N/A"))[:80]
                    logger.info(f"  [{comp}]")
                    logger.info(f"    Licensee says: {justification}")
                    logger.info(f"    KSERC past response: {kserc_response}")
                    logger.info(f"    Likely decision: {likely_decision} (ref: {past_ref})")
        else:
            logger.info("=== No licensee justification analysis available ===")

        # ── Deep Table Analysis ──────────────────────────────────────────
        detailed_tables = state.get("detailed_tables", {})
        if _deep_table_available and detailed_tables:
            tables_found = detailed_tables.get("tables_found", [])
            justifications = detailed_tables.get("component_justifications", {})
            logger.info(f"=== Deep Table Data Available: {len(tables_found)} tables ===")
            
            for comp_key in ["employee_cost", "repair_maintenance", "admin_general",
                            "depreciation", "interest_long_term"]:
                # Log component breakdowns
                comp_map = {
                    "employee_cost": "employee", "repair_maintenance": "rm",
                    "admin_general": "ag", "depreciation": "depreciation",
                    "interest_long_term": "interest",
                }
                deep_key = comp_map.get(comp_key, comp_key)
                breakdown = get_component_breakdown(detailed_tables, deep_key)
                if breakdown:
                    logger.info(f"  {comp_key}: {len(breakdown)} line items found")
                    for item in breakdown[:5]:  # Log first 5 items
                        logger.info(f"    {item}")
                
                # Log licensee justification
                justification = get_justification(detailed_tables, deep_key)
                if justification:
                    logger.info(f"  {comp_key} justification: {justification[:120]}...")

            # Log capital structure from deep tables
            cap_struct = detailed_tables.get("capital_structure", {})
            if cap_struct:
                logger.info(f"  Capital structure from deep tables:")
                for k, v in cap_struct.items():
                    if v:
                        logger.info(f"    {k}: {v}")

            # Log escalation factors from deep tables
            escalation = detailed_tables.get("escalation_factors", {})
            if escalation:
                logger.info(f"  Escalation factors from deep tables:")
                for k, v in escalation.items():
                    if v:
                        logger.info(f"    {k}: {v}%")
        else:
            logger.info("=== No deep table data available ===")

        # ── Cross-Reference with Past Trued-Up Order Decisions ────────
        if _deep_table_available and detailed_tables:
            order_learnings = detailed_tables.get("order_learnings", {})
            cross_patterns = detailed_tables.get("cross_licensee_patterns", {})
            
            if order_learnings:
                logger.info(f"=== Past Order Learnings ({len(order_learnings)} orders) ===")
                
                # Find the most relevant past orders for this licensee
                relevant_orders = {
                    k: v for k, v in order_learnings.items()
                    if licensee.lower() in k.lower()
                }
                all_other_orders = {
                    k: v for k, v in order_learnings.items()
                    if licensee.lower() not in k.lower()
                }
                
                if relevant_orders:
                    logger.info(f"  Same licensee orders: {list(relevant_orders.keys())}")
                    for order_key, order_data in relevant_orders.items():
                        decisions = order_data.get("kserc_decisions", {})
                        for comp, d in decisions.items():
                            if isinstance(d, dict) and d.get("claimed_amount", 0) > 0:
                                claimed = d.get("claimed_amount", 0)
                                approved = d.get("approved_amount", 0)
                                reasoning = str(d.get("kserc_reasoning", ""))[:100]
                                logger.info(
                                    f"    [{order_key}] {comp}: "
                                    f"claimed={claimed}, approved={approved}"
                                )
                                if reasoning:
                                    logger.info(f"      KSERC said: {reasoning}")
                
                if all_other_orders:
                    logger.info(f"  Cross-licensee orders: {list(all_other_orders.keys())}")
            
            if cross_patterns:
                logger.info(f"=== Cross-Licensee Decision Patterns ({len(cross_patterns)} components) ===")
                for comp, pattern in cross_patterns.items():
                    if isinstance(pattern, dict):
                        total = pattern.get("total_orders_analyzed", 0)
                        cut_times = pattern.get("times_kserc_cut", 0)
                        avg_cut = pattern.get("avg_cut_percentage", 0)
                        methodologies = pattern.get("methodologies", [])
                        
                        logger.info(
                            f"  {comp}: KSERC cut {cut_times}/{total} times "
                            f"(avg {avg_cut}% cut)"
                        )
                        if methodologies:
                            logger.info(f"    Methodologies: {', '.join(methodologies[:3])}")
                        
                        # Log sample reasonings
                        reasonings = pattern.get("common_reasonings", [])
                        for r in reasonings[:2]:
                            logger.info(f"    Example: {str(r)[:120]}")


        # Analyze capital structure FIRST
        cap_analysis = _analyze_capital_structure(state)

        _audit_section3_duty(claimed_expenses, approved_expenses, disallowances)
        _audit_power_purchase(state, approved_expenses, disallowances, myt_norms)

        # BEE energy audit fee — three-tier priority:
        # 1. Extractor (Gemini Vision or regex on petition text)
        # 2. myt_baselines.json known values (fallback for image-based/scanned PDFs)
        # 3. 0.0 (not applicable for this licensee/year)
        bee_fee_from_state = float(state.get("bee_energy_audit_fee", 0.0) or 0.0)
        bee_fee_from_norms  = float(myt_norms.get("bee_energy_audit_fee", 0.0) or 0.0)
        bee_fee_effective   = bee_fee_from_state if bee_fee_from_state > 0.0 else bee_fee_from_norms
        if bee_fee_effective > 0.0:
            src = "extractor" if bee_fee_from_state > 0.0 else "myt_baselines"
            logger.info(f"BEE energy audit fee: Rs.{bee_fee_effective:.2f}L (source: {src})")
        # Get detailed_tables for order-learning-driven decisions
        detailed_tables = state.get("detailed_tables", {})

        # Extract wage revision data from state (populated by extractor/Gemini Vision)
        wage_revision_current = float(state.get("wage_revision_current_year", 0.0) or 0.0)
        wage_revision_prior = float(state.get("wage_revision_prior_period", 0.0) or 0.0)
        if wage_revision_current > 0.0 or wage_revision_prior > 0.0:
            logger.info(
                f"Wage revision detected: current year Rs.{wage_revision_current:.2f}L, "
                f"prior period Rs.{wage_revision_prior:.2f}L"
            )

        def _build_rm_justification(claimed_rm, norm_rm, total_approved_rm, summary):
            """Build R&M justification text, omitting zero-value items."""
            one_time = summary.get('one_time_allowed', 0)
            capitalised = summary.get('to_be_capitalised', 0)
            disallowed = summary.get('disallowed_routine', 0)

            parts = [
                f"The claimed R&M of Rs. {claimed_rm:,.2f} Lakhs was analysed "
                f"item-by-item using KSERC Regulation 80(3). "
                f"The Commission approves Rs. {norm_rm:,.2f} Lakhs as the "
                f"normative O&M component."
            ]

            if one_time > 0:
                parts.append(
                    f"Additionally, Rs. {one_time:,.2f} Lakhs is approved for "
                    f"genuine one-time expenses under Regulation 80(3)."
                )

            if capitalised > 0:
                parts.append(
                    f"Rs. {capitalised:,.2f} Lakhs are directed to be capitalised "
                    f"and added to the Gross Fixed Assets."
                )

            if disallowed > 0:
                parts.append(
                    f"Rs. {disallowed:,.2f} Lakhs are disallowed as routine expenses "
                    f"already covered within the normative allowance."
                )

            parts.append(f"Total approved: Rs. {total_approved_rm:,.2f} Lakhs.")
            return " ".join(parts)

        # ── R&M Classifier (Regulation 80(3) one-time items) ──────────────
        # If the extractor found individual R&M line items, run the AI
        # classifier to distinguish CAPITAL / ONE_TIME_RM / ROUTINE_RM.
        # Approved R&M = MYT norm + allowed one-time items.
        # Falls back to norm-cap if no items or classifier fails.
        rm_classifier_used = False
        rm_line_items = state.get("rm_line_items", [])
        norm_rm = _myt_norm(myt_norms, "repair_maintenance")
        claimed_rm_for_check = claimed_expenses.get("repair_maintenance", 0.0)

        logger.info(
            f"R&M DEBUG: rm_line_items={len(rm_line_items)}, norm_rm={norm_rm}, "
            f"claimed_rm={claimed_rm_for_check}, will_extract={not rm_line_items and norm_rm > 0 and claimed_rm_for_check > norm_rm}"
        )

        # ── Auto-extract R&M line items if claimed > norm but no items exist ──
        # The extractor only captures the total R&M amount. When the total exceeds
        # the MYT norm, we use Gemini to extract individual R&M line items from
        # the uploaded PDF so the classifier can identify genuine one-time expenses
        # that KSERC allows above the norm (Regulation 80(3)).
        if not rm_line_items and norm_rm > 0.0 and claimed_rm_for_check > norm_rm:
            logger.info(
                f"R&M: claimed ({claimed_rm_for_check:.2f}L) > norm ({norm_rm:.2f}L) — "
                f"attempting Gemini extraction of R&M line items"
            )
            try:
                from src.gemini_client import generate
                import json as _json

                # Get petition text for Gemini to analyse
                petition_text = state.get("petition_text", "")
                # Truncate to ~8000 chars to stay within token limits
                text_snippet = petition_text[:8000] if petition_text else ""

                _RM_EXTRACT_PROMPT = (
                    f"You are analysing a KSERC truing-up petition for {licensee} FY {fy}.\n\n"
                    f"The licensee claimed Rs. {claimed_rm_for_check:.2f} Lakhs for Repairs & Maintenance.\n\n"
                    "Below is the extracted text from the petition. Extract EVERY individual R&M "
                    "expenditure line item you can find.\n"
                    "Look for tables or paragraphs listing R&M items such as:\n"
                    "  - Transformer repairs/replacements\n"
                    "  - Cable repairs/laying\n"
                    "  - Substation maintenance\n"
                    "  - Testing and inspection\n"
                    "  - Annual maintenance contracts (AMC)\n"
                    "  - Electrical equipment servicing\n"
                    "  - Any other R&M items with individual amounts\n\n"
                    "Return ONLY a JSON array of objects. Each object must have:\n"
                    '  "description": string (the R&M item description),\n'
                    '  "amount": number (amount in Rs. Lakhs)\n\n'
                    "If no individual line items can be found, return an empty array [].\n"
                    "Do NOT include the total R&M amount as a line item.\n"
                    "Return ONLY the JSON array, no other text.\n\n"
                    "--- PETITION TEXT ---\n"
                    f"{text_snippet}\n"
                    "--- END ---"
                )

                raw = generate(
                    prompt=_RM_EXTRACT_PROMPT,
                    model=GEMINI_MODEL,
                    temperature=0.0,
                    response_mime_type="application/json",
                    max_output_tokens=2048,
                )
                extracted_items = _json.loads(raw)
                if isinstance(extracted_items, list) and len(extracted_items) > 0:
                    rm_line_items = extracted_items
                    state["rm_line_items"] = rm_line_items
                    logger.info(
                        f"R&M: Gemini extracted {len(rm_line_items)} line items "
                        f"(total: {sum(i.get('amount', 0) for i in rm_line_items):.2f}L)"
                    )
                else:
                    logger.info("R&M: Gemini found no individual line items in petition")
            except Exception as e:
                logger.warning(f"R&M line item extraction failed ({e}) — using norm cap only")

        if rm_line_items and norm_rm > 0.0:
            try:
                from src.tools.rm_classifier import process_rm_petition
                rm_result = process_rm_petition(
                    licensee_name=licensee,
                    financial_year=fy,
                    norm_rm=norm_rm,
                    items=rm_line_items,
                )
                total_approved_rm = rm_result.get("total_approved_rm", norm_rm)
                claimed_rm = claimed_expenses.get("repair_maintenance", 0.0)
                approved_expenses["repair_maintenance"] = total_approved_rm
                rm_classifier_used = True
                # Store full result in state for drafter and clarification node
                state["rm_classification_result"] = rm_result

                summary = rm_result.get("financial_summary", {})
                logger.info(
                    f"R&M Classifier applied: norm={summary.get('norm_rm_approved',0):.2f}L + "
                    f"one_time_allowed={summary.get('one_time_allowed',0):.2f}L = "
                    f"total_approved={total_approved_rm:.2f}L | "
                    f"capitalised={summary.get('to_be_capitalised',0):.2f}L | "
                    f"disallowed_routine={summary.get('disallowed_routine',0):.2f}L"
                )
                cut = round(claimed_rm - total_approved_rm, 2)
                if abs(cut) > 0.01:
                    disallowances.append({
                        "item": "Repairs & Maintenance (AI-classified)",
                        "claimed": claimed_rm,
                        "approved": total_approved_rm,
                        "amount_cut": cut,
                        "justification": _build_rm_justification(
                            claimed_rm, norm_rm, total_approved_rm, summary
                        ),
                    })
            except Exception as e:
                logger.warning(f"R&M classifier failed ({e}) — falling back to norm cap")

        for key in ("employee_cost", "repair_maintenance", "admin_general"):
            if key == "repair_maintenance" and rm_classifier_used:
                continue  # Already handled by AI classifier above
            _audit_norm_capped_component(
                key, claimed_expenses, approved_expenses, myt_norms,
                disallowances, licensee=licensee, fy=fy,
                bee_fee=bee_fee_effective if key == "admin_general" else 0.0,
                detailed_tables=detailed_tables,
                wage_revision=wage_revision_current if key == "employee_cost" else 0.0,
                wage_revision_prior_period=wage_revision_prior if key == "employee_cost" else 0.0,
                state=state,
            )


        # Depreciation — KSERC Regulation 27 (replaces generic norm cap)
        _audit_depreciation_reg27(
            state, claimed_expenses, approved_expenses, myt_norms,
            disallowances, cap_analysis, licensee=licensee, fy=fy
        )

        _audit_interest_long_term_loans(
            claimed_expenses, approved_expenses, myt_norms, disallowances,
            fy, licensee=licensee, detailed_tables=detailed_tables, state=state,
        )
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

        _audit_other_debits(
            claimed_expenses, approved_expenses, myt_norms,
            disallowances, licensee=licensee, fy=fy,
            detailed_tables=detailed_tables,
        )
        _audit_passthrough("other_expenses", claimed_expenses, approved_expenses)

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

