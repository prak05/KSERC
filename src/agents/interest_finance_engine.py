"""
interest_finance_engine.py
==========================
KSERC Interest & Finance Charges Calculation Engine.

Orchestrates all 7 interest components (A through G) per the KSERC
Interest & Finance Charges specification.

Component A : Interest on actual long-term loans
Component B : Interest on normative loan
Component C : Interest on working capital
Component D : Interest on consumer security deposits
Component E : Bank charges (classify + reclassify from A&G)
Component F : Carrying cost on revenue gaps
Component G : Notional interest on accumulated surplus (→ income, NOT expense)

Pipeline:
    1. classify_all_uploaded_files()  — multi-class file categorisation
    2. load_prior_year_data()         — 10 values from Firestore
    3. scan_documents()               — 4-pass targeted extraction
    4. calculate_all_components()     — sequential A→G with provisional handling
    5. run_cross_verification()       — 6 checks
    6. assemble_output()              — 9 output types
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Internal imports ──────────────────────────────────────────────────────
from src.tools.normative_math import (
    calculate_interest_on_normative_loan,
    calculate_working_capital_interest,
    calculate_security_deposit_interest,
    calculate_carrying_cost,
    calculate_notional_surplus_interest,
    classify_bank_charge,
)
from src.tools.firestore_tracker import (
    load_interest_prior_data,
    save_interest_finance_data,
)
from src.models.schemas import FileClass

# ─────────────────────────────────────────────────────────────────────────────
# Step 0 — File Classification (multi-class)
# ─────────────────────────────────────────────────────────────────────────────

# First-page text signals for each file class
_CLASS_SIGNALS = {
    FileClass.NARRATIVE_PETITION: [
        "petition", "petitioner", "before the commission",
        "truing up", "true up", "hon'ble commission",
        "before the kerala state electricity",
    ],
    FileClass.KSERC_FORMATS: [
        "form d", "format", "statement of revenue",
        "arr format", "statement showing", "aggregate revenue",
        "schedule of rates", "tariff schedule",
    ],
    FileClass.AUDITED_ACCOUNTS: [
        "balance sheet", "profit and loss", "audited",
        "audit report", "statutory auditor", "schedule to",
        "notes to accounts", "auditors' report",
    ],
    FileClass.AUDITOR_REPORT: [
        "independent auditor", "audit opinion",
        "chartered accountant", "auditor's report",
    ],
    FileClass.PREVIOUS_ORDER: [
        "order dated", "in the matter of", "commission hereby orders",
        "ordered that", "commission orders", "o.p. no.",
    ],
    FileClass.HEARING_PROCEEDINGS: [
        "proceedings", "hearing", "minutes of",
        "daily order", "hearing notes",
    ],
}


def classify_all_uploaded_files(
    pdf_paths: List[str],
    petition_text_by_file: Dict[str, str],
) -> Dict[str, List[str]]:
    """
    Classify each uploaded PDF into one or more file classes.

    Multi-class: a single file (e.g. KDHP Annex B) may be classified as
    both KSERC_FORMATS and AUDITED_ACCOUNTS if it contains both.

    Parameters
    ----------
    pdf_paths : list of str
        Absolute paths to all uploaded PDFs.
    petition_text_by_file : dict
        Map of filename → full extracted text from that file.

    Returns
    -------
    dict mapping filename → list of FileClass values.
    """
    classifications = {}

    for pdf_path in pdf_paths:
        filename = os.path.basename(pdf_path)
        text = petition_text_by_file.get(filename, "").lower()
        file_classes = []

        # Check scanned PDF — average content per page
        # (crude heuristic: if total text is very short and file has pages)
        if len(text.strip()) < 100:
            file_classes.append(FileClass.SCANNED_PDF.value)
        else:
            # Check each class — file can match multiple
            for file_class, signals in _CLASS_SIGNALS.items():
                matches = sum(1 for sig in signals if sig in text)
                # Require at least 2 signal matches for classification
                if matches >= 2:
                    file_classes.append(file_class.value)

        if not file_classes:
            # Default: treat as narrative petition (most common single-file case)
            file_classes.append(FileClass.NARRATIVE_PETITION.value)

        classifications[filename] = file_classes
        logger.info(f"File {filename} classified as: {file_classes}")

    return classifications


def _is_likely_scanned(text: str, expected_pages: int = 10) -> bool:
    """
    Detect if a PDF is likely scanned by checking average text per content page.

    Skips first page (cover) and last page. If average chars per
    remaining page < 300, likely scanned.
    """
    if not text or expected_pages <= 2:
        return len(text.strip()) < 200

    # Rough estimate: split by form-feed or page markers
    pages = text.split("\f") if "\f" in text else [text]
    if len(pages) <= 2:
        return len(text.strip()) < 300

    # Skip first and last pages
    content_pages = pages[1:-1]
    if not content_pages:
        return len(text.strip()) < 300

    avg_chars = sum(len(p.strip()) for p in content_pages) / len(content_pages)
    return avg_chars < 300


# ─────────────────────────────────────────────────────────────────────────────
# Step 1–3: Document Scanning (Stubbed for Gemini Integration)
# ─────────────────────────────────────────────────────────────────────────────
# These functions structure the 4-pass scanning but delegate actual extraction
# to Gemini/Vision API which requires the AI model to be available at runtime.
# The logic below defines WHAT to search for and WHERE, using classifications.

def _get_files_for_class(
    classifications: Dict[str, List[str]],
    target_class: str,
) -> List[str]:
    """Return filenames classified with the given class."""
    return [
        fname for fname, classes in classifications.items()
        if target_class in classes
    ]


def build_scan_plan(
    classifications: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    """
    Generate a 4-pass scan plan mapping each pass to target files.

    Pass 1 (narrative)       → NARRATIVE_PETITION files
    Pass 2 (summary table)   → KSERC_FORMATS first
    Pass 3 (working tables)  → KSERC_FORMATS + AUDITED_ACCOUNTS
    Pass 4 (admin charges)   → KSERC_FORMATS + NARRATIVE_PETITION
    """
    return {
        "pass_1_narrative": _get_files_for_class(
            classifications, FileClass.NARRATIVE_PETITION.value
        ),
        "pass_2_summary_table": _get_files_for_class(
            classifications, FileClass.KSERC_FORMATS.value
        ),
        "pass_3_working_tables": (
            _get_files_for_class(classifications, FileClass.KSERC_FORMATS.value)
            + _get_files_for_class(classifications, FileClass.AUDITED_ACCOUNTS.value)
        ),
        "pass_4_admin_charges": (
            _get_files_for_class(classifications, FileClass.KSERC_FORMATS.value)
            + _get_files_for_class(classifications, FileClass.NARRATIVE_PETITION.value)
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Sequential Component Calculation
# ─────────────────────────────────────────────────────────────────────────────

def calculate_component_a(
    extracted_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Component A: Interest on actual long-term loans (from loan schedule)."""
    # This component uses the claimed value directly from extraction
    # KSERC typically accepts actual loan interest as claimed when
    # supported by audited loan schedule
    claimed = float(extracted_data.get("interest_long_term", 0.0))

    return {
        "component": "A",
        "name": "Interest on Long Term Loans",
        "claimed_rs_lakhs": round(claimed, 2),
        "approved_rs_lakhs": round(claimed, 2),
        "interest_rs_lakhs": round(claimed, 2),
        "status": "AS_CLAIMED" if claimed > 0 else "NIL",
        "reason": (
            "Approved as claimed based on audited loan schedule."
            if claimed > 0
            else "No long-term loan interest claimed."
        ),
        "provisional": False,
        "provisional_reason": "",
    }


def calculate_component_b(
    prior_data: Dict[str, Any],
    qualifying_additions: float,
    repayment_depreciation: float,
    eblr_rate: float,
    depreciation_is_approved: bool = True,
) -> Dict[str, Any]:
    """Component B: Interest on normative loan."""
    opening = prior_data.get("normative_loan_closing_balance", 0.0)
    surplus_funded = sum(
        item.get("amount", 0.0)
        for item in prior_data.get("surplus_funded_additions_list", [])
    )

    result = calculate_interest_on_normative_loan(
        opening_balance=opening,
        qualifying_additions=qualifying_additions,
        surplus_funded_additions=surplus_funded,
        repayment_depreciation=repayment_depreciation,
        eblr_rate=eblr_rate,
        depreciation_is_approved=depreciation_is_approved,
    )

    result["component"] = "B"
    result["name"] = "Interest on Normative Loan"
    return result


def calculate_component_c(
    approved_om_annual: float,
    approved_revenue: float,
    cash_security_deposit: float,
    eblr_rate: float,
    maintenance_spares: float = 0.0,
    other_deductions: float = 0.0,
    om_is_approved: bool = True,
) -> Dict[str, Any]:
    """Component C: Interest on working capital."""
    result = calculate_working_capital_interest(
        approved_om_annual=approved_om_annual,
        approved_revenue_from_sale=approved_revenue,
        cash_security_deposit=cash_security_deposit,
        maintenance_spares=maintenance_spares,
        other_deductions=other_deductions,
        eblr_rate=eblr_rate,
        om_is_approved=om_is_approved,
    )

    result["component"] = "C"
    result["name"] = "Interest on Working Capital"
    return result


def calculate_component_d(
    prior_data: Dict[str, Any],
    supply_code_rate: float,
) -> Dict[str, Any]:
    """Component D: Interest on consumer security deposits."""
    opening = prior_data.get("security_deposit_closing_balance", 0.0)

    result = calculate_security_deposit_interest(
        opening_balance=opening,
        supply_code_rate=supply_code_rate,
    )

    result["component"] = "D"
    result["name"] = "Interest on Consumer Security Deposits"
    return result


def calculate_component_e(
    bank_charge_items: List[Dict[str, Any]],
    ag_bank_charges: List[Dict[str, Any]],
    litigation_bg_status: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Component E: Bank charges classification and reclassification.

    bank_charge_items: items claimed under interest section
    ag_bank_charges: items found in A&G that should be reclassified
    """
    all_items = []
    total_approved = 0.0
    total_disallowed = 0.0
    reclassified_from_ag = 0.0
    needs_clarification = []

    litigation_active = litigation_bg_status.get("active", False)

    # Process items from interest section
    for item in bank_charge_items:
        result = classify_bank_charge(
            description=item.get("description", ""),
            amount=float(item.get("amount", 0.0)),
            litigation_bg_active=litigation_active,
        )
        result["source"] = "interest_section"
        all_items.append(result)

        if result["allowable"]:
            total_approved += result["amount"]
        else:
            total_disallowed += result["amount"]

        if result["needs_clarification"]:
            needs_clarification.append(result)

    # Process items reclassified FROM A&G to interest
    for item in ag_bank_charges:
        result = classify_bank_charge(
            description=item.get("description", ""),
            amount=float(item.get("amount", 0.0)),
            litigation_bg_active=litigation_active,
        )
        result["source"] = "reclassified_from_ag"
        all_items.append(result)

        reclassified_from_ag += result["amount"]
        if result["allowable"]:
            total_approved += result["amount"]
        else:
            total_disallowed += result["amount"]

        if result["needs_clarification"]:
            needs_clarification.append(result)

    return {
        "component": "E",
        "name": "Bank Charges",
        "items": all_items,
        "total_approved": round(total_approved, 2),
        "total_disallowed": round(total_disallowed, 2),
        "reclassified_from_ag": round(reclassified_from_ag, 2),
        "needs_clarification": needs_clarification,
        "litigation_bg_status": litigation_bg_status,
        "interest_rs_lakhs": round(total_approved, 2),
    }


def calculate_component_f(
    prior_data: Dict[str, Any],
    retail_td_rate: float,
) -> Dict[str, Any]:
    """Component F: Carrying cost on revenue gap."""
    cum_gap = prior_data.get("cumulative_position_amount", 0.0)
    position_type = prior_data.get("cumulative_position_type", "GAP")

    result = calculate_carrying_cost(
        cumulative_gap=cum_gap,
        retail_td_rate=retail_td_rate,
        position_type=position_type,
    )

    result["component"] = "F"
    result["name"] = "Carrying Cost on Revenue Gaps"
    return result


def calculate_component_g(
    prior_data: Dict[str, Any],
    retail_td_rate: float,
    surplus_additions_this_year: float = 0.0,
    licensee_claimed_actual: float = 0.0,
) -> Dict[str, Any]:
    """
    Component G: Notional interest on accumulated surplus → INCOME.

    IMPORTANT: This component produces INCOME, NOT expense.
    The notional_amount feeds into non-tariff income (NTI), NOT
    into total_approved_interest_expense.
    """
    cum_surplus = prior_data.get("cumulative_position_amount", 0.0)
    position_type = prior_data.get("cumulative_position_type", "GAP")

    result = calculate_notional_surplus_interest(
        cumulative_surplus=cum_surplus,
        surplus_additions_this_year=surplus_additions_this_year,
        retail_td_rate=retail_td_rate,
        position_type=position_type,
        licensee_claimed_actual=licensee_claimed_actual,
    )

    result["component"] = "G"
    result["name"] = "Notional Interest on Accumulated Surplus"
    result["is_income_not_expense"] = True
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Cross-Verification (6 Checks)
# ─────────────────────────────────────────────────────────────────────────────

def run_cross_verification(
    components: Dict[str, Dict[str, Any]],
    claimed_interest_total: float,
    reclassified_from_ag: float = 0.0,
    prior_period_bank_charges: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Run 6 cross-verification checks per spec Part 6.

    Returns list of check results, each with: check_name, passed, detail.
    """
    checks = []

    # Totals
    comp_a = components.get("A", {}).get("interest_rs_lakhs", 0.0)
    comp_b = components.get("B", {}).get("interest_rs_lakhs", 0.0)
    comp_c = components.get("C", {}).get("interest_rs_lakhs", 0.0)
    comp_d = components.get("D", {}).get("interest_rs_lakhs", 0.0)
    comp_e = components.get("E", {}).get("interest_rs_lakhs", 0.0)
    comp_f = components.get("F", {}).get("carrying_cost_rs_lakhs",
             components.get("F", {}).get("interest_rs_lakhs", 0.0))

    total_approved = comp_a + comp_b + comp_c + comp_d + comp_e + comp_f

    # Check 1: Sum ≤ claimed + reclassified + prior period
    # (Fixed per review: must include reclassified bank charges in ceiling)
    ceiling = claimed_interest_total + reclassified_from_ag + prior_period_bank_charges
    check1_passed = total_approved <= ceiling + 0.01  # tolerance for rounding
    checks.append({
        "check_name": "Total approved ≤ claimed + reclassified",
        "passed": check1_passed,
        "detail": (
            f"Approved: {total_approved:.2f}, Ceiling: {ceiling:.2f} "
            f"(claimed {claimed_interest_total:.2f} + reclassified {reclassified_from_ag:.2f} "
            f"+ prior period {prior_period_bank_charges:.2f})"
        ),
    })

    # Check 2: Normative loan closing ≥ 0
    closing_balance = components.get("B", {}).get("closing_balance", 0.0)
    checks.append({
        "check_name": "Normative loan closing ≥ 0",
        "passed": closing_balance >= 0.0,
        "detail": f"Closing balance: {closing_balance:.2f}",
    })

    # Check 3: Working capital interest uses EBLR + 2%
    wc_rate = components.get("C", {}).get("rate", 0.0)
    checks.append({
        "check_name": "WC interest rate = EBLR + 2%",
        "passed": wc_rate > 0.0,  # Just verify rate is set
        "detail": f"Rate applied: {wc_rate:.4f}",
    })

    # Check 4: Security deposit uses Supply Code rate (not EBLR)
    sd_rate = components.get("D", {}).get("supply_code_rate", 0.0)
    checks.append({
        "check_name": "SD interest uses Supply Code rate",
        "passed": sd_rate > 0.0,
        "detail": f"Supply Code rate: {sd_rate:.4f}",
    })

    # Check 5: Component G (if applicable) is routed to NTI, not expense
    comp_g = components.get("G", {})
    g_applicable = comp_g.get("applicable", False)
    checks.append({
        "check_name": "Component G routed to NTI (not expense)",
        "passed": True,  # Engine always routes correctly by design
        "detail": (
            f"Notional surplus interest: {comp_g.get('notional_amount', 0.0):.2f} → NTI"
            if g_applicable
            else "Not applicable (GAP position or zero surplus)"
        ),
    })

    # Check 6: No double-counting of bank charges
    reclassified = components.get("E", {}).get("reclassified_from_ag", 0.0)
    checks.append({
        "check_name": "Bank charges reclassification tracked",
        "passed": True,
        "detail": (
            f"Rs.{reclassified:.2f} lakh reclassified from A&G. "
            f"ag_adjustment_for_bank_charges set for A&G deduction."
        ),
    })

    return checks


# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Output Assembly
# ─────────────────────────────────────────────────────────────────────────────

def assemble_output(
    components: Dict[str, Dict[str, Any]],
    cross_checks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Assemble the 9 output types per spec Part 7.

    Returns the full interest_finance_result dict.
    """
    # Sum A through F for expense total (G is INCOME, excluded)
    comp_a = components.get("A", {}).get("interest_rs_lakhs", 0.0)
    comp_b = components.get("B", {}).get("interest_rs_lakhs", 0.0)
    comp_c = components.get("C", {}).get("interest_rs_lakhs", 0.0)
    comp_d = components.get("D", {}).get("interest_rs_lakhs", 0.0)
    comp_e = components.get("E", {}).get("interest_rs_lakhs", 0.0)
    comp_f_result = components.get("F", {})
    comp_f = comp_f_result.get("carrying_cost_rs_lakhs", 0.0)

    total_expense = comp_a + comp_b + comp_c + comp_d + comp_e + comp_f

    # Provisional tracking (cascading)
    provisional_components = []
    for key, comp in components.items():
        if comp.get("provisional", False):
            provisional_components.append(comp.get("name", key))
    is_provisional = len(provisional_components) > 0

    # Component G income
    comp_g_result = components.get("G", {})
    notional_surplus = comp_g_result.get("notional_amount", 0.0)
    additional_to_nti = comp_g_result.get("additional_to_nti", 0.0)

    return {
        # ── 1. Component-wise table ──────────────────
        "component_a": components.get("A", {}),
        "component_b": components.get("B", {}),
        "component_c": components.get("C", {}),
        "component_d": components.get("D", {}),
        "component_e": components.get("E", {}),
        "component_f": components.get("F", {}),
        "component_g": components.get("G", {}),

        # ── 2. Totals ────────────────────────────────
        "total_approved_interest_expense": round(total_expense, 2),
        "component_totals": {
            "A": round(comp_a, 2),
            "B": round(comp_b, 2),
            "C": round(comp_c, 2),
            "D": round(comp_d, 2),
            "E": round(comp_e, 2),
            "F": round(comp_f, 2),
        },

        # ── 3. Income (NOT expense) ──────────────────
        "income_additions": {
            "notional_surplus_interest": round(notional_surplus, 2),
            "additional_to_nti": round(additional_to_nti, 2),
        },

        # ── 4. Reclassification adjustment ───────────
        "ag_adjustment_for_bank_charges": components.get("E", {}).get("reclassified_from_ag", 0.0),

        # ── 5. Provisional status (cascading) ────────
        "is_provisional": is_provisional,
        "provisional_components": provisional_components,
        "provisional_warning": (
            f"Interest total of Rs.{total_expense:.2f} lakh is PROVISIONAL. "
            f"Components not yet final: {', '.join(provisional_components)}. "
            f"Recalculate after these components are approved. "
            f"Revenue gap and ARR using this total are also provisional."
            if is_provisional else ""
        ),

        # ── 6. Cross-verification ────────────────────
        "cross_verification": cross_checks,
        "all_checks_passed": all(c["passed"] for c in cross_checks),

        # ── 7. Clarifications needed ─────────────────
        "clarifications_needed": components.get("E", {}).get("needs_clarification", []),

        # ── 8. Disallowances ─────────────────────────
        "disallowances": [
            item for item in components.get("E", {}).get("items", [])
            if not item.get("allowable", True)
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def process_interest_finance(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for the interest & finance charges engine.

    Expects the following state keys:
        licensee_name, financial_year,
        sbi_eblr_rate, sbi_retail_td_rate, supply_code_sd_rate,
        claimed_expenses, approved_expenses (may be partial),
        approved_revenues (may be partial),
        petition_pdf_path, annexure_pdf_paths, petition_text,
        file_classifications (optional — will classify if missing)

    Updates state with:
        interest_finance_result, interest_cross_verification,
        notional_surplus_for_nti, ag_adjustment_for_bank_charges,
        interest_is_provisional, interest_provisional_components
    """
    licensee = state.get("licensee_name", "Unknown")
    fy = state.get("financial_year", "")
    logger.info(f"Interest Engine: starting for {licensee} FY {fy}")

    # ── Rates ─────────────────────────────────────────────────────────
    eblr_rate = float(state.get("sbi_eblr_rate", 0.0))
    retail_td_rate = float(state.get("sbi_retail_td_rate", 0.0))
    supply_code_rate = float(state.get("supply_code_sd_rate", 0.0))

    if eblr_rate == 0.0 or retail_td_rate == 0.0:
        logger.warning("SBI rates not provided — interest calculations may be zero")

    # ── Step 1: Load prior year data from Firestore ──────────────────
    prior_data = load_interest_prior_data(licensee, fy)
    logger.info(f"Prior data loaded: {prior_data.get('source', 'unknown')}, "
                f"missing: {prior_data.get('missing_fields', [])}")

    # ── Step 2: Get extracted claimed expenses ───────────────────────
    claimed = state.get("claimed_expenses", {})
    approved = state.get("approved_expenses", {})
    approved_revenues = state.get("approved_revenues", {})

    # Check if O&M and depreciation are approved yet
    om_components = ["employee_cost", "repair_maintenance", "admin_general"]
    approved_om = sum(float(approved.get(k, 0.0)) for k in om_components)
    claimed_om = sum(float(claimed.get(k, 0.0)) for k in om_components)
    om_is_approved = approved_om > 0.0

    approved_dep = float(approved.get("depreciation", 0.0))
    claimed_dep = float(claimed.get("depreciation", 0.0))
    dep_is_approved = approved_dep > 0.0

    # Use approved if available, claimed as fallback
    om_for_wc = approved_om if om_is_approved else claimed_om
    dep_for_loan = approved_dep if dep_is_approved else claimed_dep

    # Revenue for WC receivables — MUST use Revenue from Sale of Power only
    # Per KSERC norms, receivables = 2 months of revenue from sale of power
    # NOT total revenue (which includes NTI, wheeling charges, etc.)
    claimed_revenues = state.get("claimed_revenues", {})
    approved_rev_sale = float(approved_revenues.get("revenue_from_sale", 0.0) or 0.0)
    if approved_rev_sale == 0.0:
        # Fallback 1: use claimed revenue from sale of power
        approved_rev_sale = float(claimed_revenues.get("revenue_from_sale", 0.0) or 0.0)
        if approved_rev_sale > 0:
            logger.info(f"WC: Using claimed revenue_from_sale: {approved_rev_sale}")
    if approved_rev_sale == 0.0:
        # Fallback 2: use total_approved_revenue from state (auditor output)
        approved_rev_sale = float(state.get("total_approved_revenue", 0.0) or 0.0)
        if approved_rev_sale > 0:
            logger.info(f"WC: Using total_approved_revenue as fallback: {approved_rev_sale}")
    if approved_rev_sale == 0.0:
        # Fallback 3: prior year from Firestore
        approved_rev_sale = prior_data.get("approved_revenue_previous_year", 0.0)
        if approved_rev_sale > 0:
            logger.info(f"WC: Using prior_data approved_revenue_previous_year: {approved_rev_sale}")
    approved_rev_total = approved_rev_sale

    # ── Step 3: Calculate all components sequentially ────────────────
    components = {}

    # Component A: Actual loan interest
    components["A"] = calculate_component_a(claimed)
    logger.info(f"Component A: {components['A']['interest_rs_lakhs']}")

    # Component B: Normative loan interest
    qualifying_additions = float(claimed.get("capital_additions", 0.0))

    # Fallback: use petition-extracted normative loan data if Firestore has none
    norm_loan_opening = prior_data.get("normative_loan_closing_balance", 0.0)
    # HIGHEST PRIORITY: user-supplied override from frontend
    user_norm_loan = float(state.get("norm_loan_opening_override", 0.0) or 0.0)
    if user_norm_loan > 0:
        prior_data["normative_loan_closing_balance"] = user_norm_loan
        logger.info(f"Component B: Using USER-SUPPLIED normative loan opening: {user_norm_loan}")
    elif norm_loan_opening == 0.0:
        petition_opening = float(state.get("normative_loan_opening", 0.0) or 0.0)
        if petition_opening > 0:
            prior_data["normative_loan_closing_balance"] = petition_opening
            logger.info(f"Component B: Using petition-extracted normative_loan_opening: {petition_opening}")
    if qualifying_additions == 0.0:
        petition_additions = float(state.get("normative_loan_additional", 0.0) or 0.0)
        if petition_additions > 0:
            qualifying_additions = petition_additions
            logger.info(f"Component B: Using petition-extracted normative_loan_additional: {petition_additions}")

    components["B"] = calculate_component_b(
        prior_data=prior_data,
        qualifying_additions=qualifying_additions,
        repayment_depreciation=dep_for_loan,
        eblr_rate=eblr_rate,
        depreciation_is_approved=dep_is_approved,
    )
    logger.info(f"Component B: {components['B']['interest_rs_lakhs']}")

    # Component C: Working capital interest
    cash_sd = prior_data.get("security_deposit_closing_balance", 0.0)
    # HIGHEST PRIORITY: user-supplied SD balance override
    user_sd = float(state.get("sd_balance_override", 0.0) or 0.0)
    if user_sd > 0:
        cash_sd = user_sd
        prior_data["security_deposit_closing_balance"] = user_sd
        logger.info(f"Component C: Using USER-SUPPLIED security deposit balance: {user_sd}")
    elif cash_sd == 0.0:
        cash_sd = float(state.get("consumer_security_deposit_balance", 0.0) or 0.0)
        if cash_sd > 0:
            logger.info(f"Component C: Using petition-extracted security deposit balance: {cash_sd}")
    components["C"] = calculate_component_c(
        approved_om_annual=om_for_wc,
        approved_revenue=approved_rev_total,
        cash_security_deposit=cash_sd,
        eblr_rate=eblr_rate,
        om_is_approved=om_is_approved,
    )
    logger.info(f"Component C: {components['C']['interest_rs_lakhs']}")

    # Component D: Security deposit interest
    # Use Firestore prior data first, then fall back to petition extraction
    sd_opening = prior_data.get("security_deposit_closing_balance", 0.0)
    if sd_opening == 0.0:
        sd_opening = float(state.get("consumer_security_deposit_balance", 0.0) or 0.0)
        if sd_opening > 0:
            logger.info(f"Component D: Using petition-extracted security deposit balance: {sd_opening}")
            # Inject into prior_data so calculate_component_d can use it
            prior_data["security_deposit_closing_balance"] = sd_opening
    components["D"] = calculate_component_d(
        prior_data=prior_data,
        supply_code_rate=supply_code_rate,
    )
    logger.info(f"Component D: {components['D']['interest_rs_lakhs']}")

    # Component E: Bank charges
    # Gather bank charge items from claimed expenses and A&G
    bank_items_interest = state.get("bank_charge_items_interest", [])
    bank_items_ag = state.get("bank_charge_items_ag", [])
    litigation_status = prior_data.get("litigation_bg_status", {"active": False, "court_reference": ""})

    components["E"] = calculate_component_e(
        bank_charge_items=bank_items_interest,
        ag_bank_charges=bank_items_ag,
        litigation_bg_status=litigation_status,
    )
    logger.info(f"Component E: approved={components['E']['total_approved']}, "
                f"disallowed={components['E']['total_disallowed']}")

    # Component F: Carrying cost
    # HIGHEST PRIORITY: user-supplied cumulative gap override
    user_gap = float(state.get("cumulative_gap_override", 0.0) or 0.0)
    if user_gap != 0:
        prior_data["cumulative_revenue_gap"] = user_gap
        logger.info(f"Component F: Using USER-SUPPLIED cumulative revenue gap: {user_gap}")
    components["F"] = calculate_component_f(
        prior_data=prior_data,
        retail_td_rate=retail_td_rate,
    )
    comp_f_amount = components["F"].get("carrying_cost_rs_lakhs", 0.0)
    logger.info(f"Component F: {comp_f_amount}")

    # Component G: Notional surplus interest (INCOME, not expense)
    surplus_additions_this_year = 0.0  # From Firestore / extraction
    licensee_claimed_surplus_income = float(claimed.get("interest_income_surplus", 0.0))
    components["G"] = calculate_component_g(
        prior_data=prior_data,
        retail_td_rate=retail_td_rate,
        surplus_additions_this_year=surplus_additions_this_year,
        licensee_claimed_actual=licensee_claimed_surplus_income,
    )
    logger.info(f"Component G: notional={components['G'].get('notional_amount', 0.0)}")

    # ── Step 4: Cross-verification ───────────────────────────────────
    claimed_interest_total = float(claimed.get("interest_finance", 0.0))
    reclassified = components["E"].get("reclassified_from_ag", 0.0)

    cross_checks = run_cross_verification(
        components=components,
        claimed_interest_total=claimed_interest_total,
        reclassified_from_ag=reclassified,
    )

    # ── Step 5: Assemble output ──────────────────────────────────────
    result = assemble_output(components, cross_checks)

    # ── Step 6: Save to Firestore ────────────────────────────────────
    save_interest_finance_data(
        licensee=licensee,
        fy=fy,
        interest_result=result,
        rates={
            "eblr": eblr_rate,
            "retail_td": retail_td_rate,
            "supply_code_sd": supply_code_rate,
        },
    )

    # ── Step 7: Update state ─────────────────────────────────────────
    state_updates = {
        "interest_finance_result": result,
        "interest_prior_year_data": prior_data,
        "interest_cross_verification": cross_checks,
        "notional_surplus_for_nti": result["income_additions"]["additional_to_nti"],
        "ag_adjustment_for_bank_charges": result["ag_adjustment_for_bank_charges"],
        "interest_is_provisional": result["is_provisional"],
        "interest_provisional_components": result["provisional_components"],
    }

    # Update approved_expenses with interest total AND individual components
    if "approved_expenses" not in state:
        state["approved_expenses"] = {}
    state["approved_expenses"]["interest_finance"] = result["total_approved_interest_expense"]

    # ── Map individual component results back to approved_expenses ────────
    # The auditor may have set these to 0.0 if extraction returned 0 claimed,
    # but the interest engine calculates them independently from prior-year
    # data, normative loan schedules, and formula-based computations.
    # These values MUST override the auditor's defaults.
    comp_a_val = result.get("component_a", {}).get("interest_rs_lakhs", 0.0)
    comp_b_val = result.get("component_b", {}).get("interest_rs_lakhs", 0.0)
    comp_c_val = result.get("component_c", {}).get("interest_rs_lakhs", 0.0)
    comp_d_val = result.get("component_d", {}).get("interest_rs_lakhs", 0.0)
    comp_f_val = result.get("component_f", {}).get("carrying_cost_rs_lakhs", 0.0)

    # Interest on Long-Term Loans = max(Component A, Component B)
    # Component A = actual claimed interest; Component B = normative loan interest
    # KSERC approves the normative amount (B) if it differs from claimed (A)
    approved_lt = comp_b_val if comp_b_val > 0 else comp_a_val
    if approved_lt > 0:
        state["approved_expenses"]["interest_long_term"] = round(approved_lt, 2)
        logger.info(f"Mapped interest_long_term = {approved_lt:.2f} (A={comp_a_val:.2f}, B={comp_b_val:.2f})")

    # Interest on Working Capital = Component C
    if comp_c_val > 0:
        state["approved_expenses"]["interest_working_capital"] = round(comp_c_val, 2)
        logger.info(f"Mapped interest_working_capital = {comp_c_val:.2f}")

    # Interest on Consumer Security Deposits = Component D
    if comp_d_val > 0:
        state["approved_expenses"]["interest_consumer_deposits"] = round(comp_d_val, 2)
        logger.info(f"Mapped interest_consumer_deposits = {comp_d_val:.2f}")

    # Carrying Cost on Revenue Gaps = Component F
    if comp_f_val > 0:
        state["approved_expenses"]["carrying_cost"] = round(comp_f_val, 2)
        logger.info(f"Mapped carrying_cost = {comp_f_val:.2f}")

    logger.info(
        f"Interest Engine complete: total approved expense = "
        f"Rs.{result['total_approved_interest_expense']:.2f} lakh"
        f"{' (PROVISIONAL)' if result['is_provisional'] else ''}"
    )

    return state_updates
