"""
KSERC Order Builder — JSON Builder
====================================

Transforms the rule engine output state (results_*.json) into the
structured order JSON data contract consumed by the Jinja2 renderer.

The output JSON has this shape:
{
  "meta": { ... },
  "cover": { ... },
  "introduction": { "paragraphs": [ ... ] },
  "hearing": { "paragraphs": [ ... ] },
  "sections": [
    {
      "id": "ppc",
      "title": "Power Purchase Cost",
      "paragraphs": [ { "seq": N, "text": "..." } ],
      "tables": [ { "number": T, "caption": "...", "columns": [...], "rows": [...] } ],
      "decision": "The Commission approves Rs. X Lakhs..."
    },
    ...
  ],
  "orders": { "paragraphs": [ ... ] },
  "values": { flat key-value store },
  "signature": { ... }
}
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Component key → human-readable name mapping
# ═══════════════════════════════════════════════════════════════════════

COMPONENT_DISPLAY_NAMES = {
    "power_purchase_cost": "Power Purchase Cost",
    "employee_cost": "Employee Cost",
    "repair_maintenance": "Repairs & Maintenance",
    "admin_general": "Administration & General Expenses",
    "depreciation": "Depreciation",
    "interest_long_term": "Interest on Long-Term Loans",
    "interest_consumer_deposits": "Interest on Consumer Security Deposits",
    "interest_working_capital": "Interest on Working Capital",
    "carrying_cost": "Carrying Cost on Revenue Gaps",
    "return_on_nfa": "Return on Net Fixed Assets",
    "other_debits": "Other Debits",
    "section3_1_duty": "Section 3(1) Electricity Duty",
    "other_expenses": "Other Expenses",
    "interest_finance": "Interest & Finance Charges (Total)",
}

# Component key → section ID mapping for building sections
COMPONENT_TO_SECTION_ID = {
    "power_purchase_cost": "ppc",
    "employee_cost": "employee_cost",
    "repair_maintenance": "rm_expense",
    "admin_general": "ag_expense",
    "depreciation": "depreciation",
    "interest_long_term": "interest_lt",
    "interest_working_capital": "interest_wc",
    "interest_consumer_deposits": "interest_csd",
    "carrying_cost": "carrying_cost",
    "return_on_nfa": "ronfa",
    "other_debits": "other_debits",
    "section3_1_duty": "elec_duty",
    "other_expenses": "other_expenses",
}

# Order of sections in the final document
SECTION_ORDER = [
    "energy_sales",
    "distribution_loss",
    "ppc",
    "employee_cost",
    "rm_expense",
    "ag_expense",
    "depreciation",
    "interest_lt",
    "interest_wc",
    "interest_csd",
    "carrying_cost",
    "ronfa",
    "other_debits",
    "elec_duty",
    "other_expenses",
    "revenue_from_sale",
    "wheeling_charges",
    "non_tariff_income",
    "arr_gap",
]


def fmt(value: float, decimals: int = 2) -> str:
    """Format a number to string with fixed decimal places."""
    if value is None:
        return "—"
    return f"{value:,.{decimals}f}"


def _number_table(table: dict, table_seq: list[int]) -> dict:
    """Assign a sequential table number to a table dict."""
    table["number"] = _next_seq(table_seq)
    return table


# ═══════════════════════════════════════════════════════════════════════
# Main Builder Function
# ═══════════════════════════════════════════════════════════════════════

def build_order_json(state: dict) -> dict:
    """
    Transform the rule engine output state into the structured
    order JSON data contract for the Jinja2 renderer.

    Parameters
    ----------
    state : dict
        The full rule engine output state (same schema as results_*.json).

    Returns
    -------
    dict
        The order JSON ready for Jinja2 rendering.
    """
    licensee = state.get("licensee_name", "Unknown")
    fy = state.get("financial_year", "Unknown")
    components = state.get("components", [])
    disallowances = state.get("disallowances", [])
    claimed_revenues = state.get("claimed_revenues", {})
    interest_finance = state.get("interest_finance", {})
    approved_expenses = state.get("approved_expenses", {})

    # Build the values flat store first — everything else references it
    values = _build_values_store(state)

    # Build sections from components
    para_seq = [1]  # mutable counter for paragraph sequencing
    table_seq = [1]  # mutable counter for sequential table numbering
    sections = []

    # Prefix sections: Energy Sales and Distribution Loss
    sections.append(_build_energy_sales_section(state, para_seq, table_seq))
    sections.append(_build_distribution_loss_section(state, para_seq, table_seq))

    # Expense sections from components
    for comp in components:
        key = comp.get("key", "")
        section_id = COMPONENT_TO_SECTION_ID.get(key)
        if section_id is None:
            # Skip prior_period_* or unknown components — they go into ARR table
            continue
        sections.append(_build_component_section(comp, section_id, state, para_seq, table_seq))

    # Revenue sections
    sections.append(_build_revenue_from_sale_section(state, para_seq))
    sections.append(_build_wheeling_section(state, para_seq))
    sections.append(_build_nti_section(state, para_seq))

    # ARR Summary section
    sections.append(_build_arr_gap_section(state, para_seq, table_seq))

    # Orders of the Commission
    orders = _build_orders(state, para_seq)

    order_json = {
        "meta": {
            "licensee_name": licensee,
            "financial_year": fy,
            "analysis_id": state.get("analysis_id", ""),
            "timestamp": state.get("timestamp", datetime.now().isoformat()),
            "original_filenames": state.get("original_filename", ""),
        },
        "cover": _build_cover(state),
        "introduction": _build_introduction(state, para_seq=[1]),  # Re-uses seq 1..N for intro
        "hearing": _build_hearing_section(state, para_seq),
        "sections": sections,
        "orders": orders,
        "values": values,
        "signature": _build_signature(),
    }

    # Re-number all paragraphs sequentially across the entire document
    _renumber_paragraphs(order_json)

    # Auto-assign table numbers
    _assign_table_numbers(order_json)

    logger.info(
        f"Built order JSON: {len(sections)} sections, "
        f"{len(values)} values, "
        f"licensee={licensee}, FY={fy}"
    )
    return order_json


# ═══════════════════════════════════════════════════════════════════════
# Values Store Builder
# ═══════════════════════════════════════════════════════════════════════

def _build_values_store(state: dict) -> dict:
    """Build the flat key-value store for template substitution."""
    components = {c["key"]: c for c in state.get("components", [])}
    claimed_rev = state.get("claimed_revenues", {})
    interest = state.get("interest_finance", {})
    approved = state.get("approved_expenses", {})

    v = {}

    # Basic metadata
    v["fy"] = state.get("financial_year", "")
    v["licensee_name"] = state.get("licensee_name", "")
    v["analysis_id"] = state.get("analysis_id", "")

    # Expenditure totals
    v["total_claimed_expenditure"] = state.get("total_claimed_expenditure", 0)
    v["total_approved_expenditure"] = state.get("total_approved_expenditure", 0)

    # Revenue
    v["total_claimed_revenue"] = state.get("total_claimed_revenue", 0)
    v["total_approved_revenue"] = state.get("total_approved_revenue", 0)
    v["revenue_gap"] = state.get("final_revenue_gap_surplus", 0)

    # Distribution loss
    v["actual_loss_pct"] = state.get("claimed_distribution_loss_pct", 0)
    v["target_loss_pct"] = state.get("target_distribution_loss_pct", 0)

    # Revenue components
    v["revenue_from_sale_claimed"] = claimed_rev.get("revenue_from_sale", 0)
    v["revenue_from_sale_approved"] = claimed_rev.get("revenue_from_sale", 0)
    v["wheeling_charges_claimed"] = claimed_rev.get("wheeling_charges", 0)
    v["wheeling_charges_approved"] = claimed_rev.get("wheeling_charges", 0)
    v["non_tariff_income_claimed"] = claimed_rev.get("non_tariff_income", 0)
    v["non_tariff_income_approved"] = claimed_rev.get("non_tariff_income", 0)
    v["other_revenue_claimed"] = claimed_rev.get("other_revenue", 0)
    v["other_revenue_approved"] = claimed_rev.get("other_revenue", 0)

    # Per-component values: claimed, approved, myt_norm
    for comp in state.get("components", []):
        key = comp["key"]
        v[f"claimed_{key}"] = comp.get("claimed", 0)
        v[f"approved_{key}"] = comp.get("approved", 0)
        # Source MYT norm: try proposed_myt first, fall back to myt_baseline_norms
        myt_val = comp.get("proposed_myt", 0)
        if not myt_val:
            myt_norms = state.get("myt_baseline_norms", {})
            myt_val = myt_norms.get(key, 0)
        v[f"myt_{key}"] = myt_val
        v[f"variance_{key}"] = comp.get("variance", 0)

    # Interest & finance components
    if interest:
        comp_b = interest.get("component_b", {})
        v["norm_loan_opening"] = comp_b.get("opening_balance", 0)
        v["norm_loan_closing"] = comp_b.get("closing_balance", 0)
        v["norm_loan_average"] = comp_b.get("average_balance", 0)
        v["eblr_rate"] = comp_b.get("eblr_rate", 0)
        v["norm_loan_interest"] = comp_b.get("interest_rs_lakhs", 0)

        comp_c = interest.get("component_c", {})
        v["wc_om_one_month"] = comp_c.get("om_one_month", 0)
        v["wc_receivables"] = comp_c.get("receivables_two_months", 0)
        v["wc_maintenance_spares"] = comp_c.get("maintenance_spares", 0)
        v["wc_security_deposit"] = comp_c.get("cash_security_deposit", 0)
        v["wc_net"] = comp_c.get("net_working_capital", 0)
        v["wc_rate"] = comp_c.get("rate", 0)
        v["wc_interest"] = comp_c.get("interest_rs_lakhs", 0)

        comp_d = interest.get("component_d", {})
        v["sd_balance"] = comp_d.get("opening_balance", 0)
        v["sd_rate"] = comp_d.get("supply_code_rate", 0)
        v["sd_interest"] = comp_d.get("interest_rs_lakhs", 0)

        v["total_interest_expense"] = interest.get("total_approved_interest_expense", 0)

    # Approved expenses (flat dict)
    for key, amount in approved.items():
        v[f"approved_exp_{key}"] = amount

    return v


# ═══════════════════════════════════════════════════════════════════════
# Section Builders
# ═══════════════════════════════════════════════════════════════════════

def _build_cover(state: dict) -> dict:
    """Build cover page data with full KSERC format."""
    licensee = state.get("licensee_name", "")
    fy = state.get("financial_year", "")
    court = state.get("court_hearing", {})

    licensee_full_names = {
        "Infopark": "Infopark Kerala",
        "Technopark": "Technopark",
        "CSEZA": "Cochin Special Economic Zone Authority",
        "KDHP": "Kannan Devan Hills Plantations Company Private Limited",
    }
    full_name = licensee_full_names.get(licensee, licensee)

    # Petitioner representatives
    petitioner_reps = {
        "Infopark": ("Shri. Hrishikesh Nair", "CEO, Infopark Kerala"),
        "Technopark": ("Shri. John M. Thomas", "CEO, Technopark"),
        "CSEZA": ("Shri. Development Commissioner", "CSEZA, Cochin"),
        "KDHP": ("Shri. C. P. George", "Manager (Electrical), KDHP Co. Pvt. Ltd."),
    }
    pet_name, pet_desig = petitioner_reps.get(licensee, (full_name, "Representative"))

    return {
        "licensee_name": licensee,
        "licensee_full_name": full_name,
        "financial_year": fy,
        "order_type": "Truing Up",
        "petition_number": state.get("petition_number", f"OP No. XX/20{fy[-2:]}"),
        "order_date": state.get("order_date", "DD.MM.YYYY"),
        "hearing_date": court.get("hearing_date", state.get("hearing_date", "")),
        "in_the_matter_of": (
            f"Petition for Truing Up of Accounts of M/s {full_name} "
            f"for the financial year {fy} under the KSERC (Terms and Conditions "
            f"for Determination of Tariff) Regulations, 2021."
        ),
        "petitioner_name": pet_name,
        "petitioner_designation": pet_desig,
        "respondent_name": "Kerala State Electricity Board Limited (KSEB Ltd)",
        "respondent_designation": "Represented by Standing Counsel",
        "petition_details": (
            f"Truing Up of Accounts of {full_name} for FY {fy}"
        ),
    }


def _build_introduction(state: dict, para_seq: list[int]) -> dict:
    """Build introduction with 5–6 paragraphs matching KSERC standard."""
    licensee = state.get("licensee_name", "")
    fy = state.get("financial_year", "")
    total_claimed_exp = state.get("total_claimed_expenditure", 0)
    total_claimed_rev = state.get("total_claimed_revenue", 0)

    licensee_full_names = {
        "Infopark": "Infopark Kerala",
        "Technopark": "Technopark",
        "CSEZA": "Cochin Special Economic Zone Authority",
        "KDHP": "Kannan Devan Hills Plantations Company Private Limited",
    }
    full_name = licensee_full_names.get(licensee, licensee)

    # Compute claimed gap/surplus
    claimed_gap = round(total_claimed_rev - total_claimed_exp, 2)

    paragraphs = [
        # Para 1: Licensee background
        {
            "seq": _next_seq(para_seq),
            "text": (
                f"M/s {full_name} is a deemed distribution licensee under Section 14 "
                f"of the Electricity Act, 2003, engaged in the distribution and supply "
                f"of electricity in the area notified by the Government of Kerala. "
                f"The licensee filed a petition for Truing Up of accounts for the "
                f"financial year {fy} before the Kerala State Electricity Regulatory "
                f"Commission under the provisions of the KSERC (Terms and Conditions "
                f"for Determination of Tariff) Regulations, 2021."
            ),
        },
        # Para 2: 2021 Tariff Regulations and control period
        {
            "seq": _next_seq(para_seq),
            "text": (
                f"The Commission has notified the KSERC (Terms and Conditions for "
                f"Determination of Tariff) Regulations, 2021, which came into effect "
                f"from 01.04.2022. The fourth control period under these Regulations is "
                f"from 2022-23 to 2026-27 (5 years). The Commission has approved the "
                f"Multi Year Tariff (MYT) framework for the licensee for this control "
                f"period, specifying the Aggregate Revenue Requirement (ARR) for each "
                f"year of the control period."
            ),
        },
        # Para 3: Definition of truing up — Regulation 3(67)
        {
            "seq": _next_seq(para_seq),
            "text": (
                f"As per Regulation 3(67) of the KSERC Tariff Regulations, 2021, "
                f"\"Truing Up\" means an exercise to assess the actual prudent costs "
                f"incurred by the distribution licensee vis-a-vis the approved ARR "
                f"and ascertain the actual gap or surplus for the year under consideration. "
                f"The licensee is required to file the truing up petition within six months "
                f"of the close of the financial year along with the audited annual accounts."
            ),
        },
        # Para 4: Claimed financial position
        {
            "seq": _next_seq(para_seq),
            "text": (
                f"The licensee has claimed a total expenditure of Rs. {fmt(total_claimed_exp)} "
                f"Lakhs and total revenue of Rs. {fmt(total_claimed_rev)} Lakhs for FY {fy}, "
                f"resulting in a claimed revenue {'surplus' if claimed_gap >= 0 else 'gap'} "
                f"of Rs. {fmt(abs(claimed_gap))} Lakhs. The petition was filed along with "
                f"the audited annual accounts, ARR schedules, and supporting annexures "
                f"as required under the Regulations."
            ),
        },
        # Para 5: Admission and public hearing
        {
            "seq": _next_seq(para_seq),
            "text": (
                f"The petition was admitted by the Commission and a public notice was "
                f"issued inviting comments and objections from the public. The petition "
                f"was heard in the presence of the representatives of the petitioner "
                f"and the respondent KSEB Ltd. The following table provides a summary "
                f"comparison of the ARR components."
            ),
        },
    ]

    # Introduction table: 3-column ARR summary
    table = _build_arr_summary_table(state)

    return {
        "paragraphs": paragraphs,
        "tables": [table] if table else [],
    }


def _build_arr_summary_table(state: dict) -> dict | None:
    """Build the 3-column ARR Summary table (MYT Approved | Claimed | Trued Up Approved)."""
    components = state.get("components", [])
    myt_norms = state.get("myt_baseline_norms", {})
    if not components:
        return None

    rows = []
    sl = 1

    # Expenditure header
    rows.append({
        "sl": "",
        "particular": "EXPENDITURE",
        "myt_approved": "",
        "claimed": "",
        "approved": "",
        "is_header": True,
    })

    total_myt = 0
    for comp in components:
        key = comp.get("key", "")
        if key.startswith("prior_period_"):
            continue  # handled separately below
        myt_val = comp.get("proposed_myt", 0) or myt_norms.get(key, 0)
        total_myt += myt_val
        rows.append({
            "sl": sl,
            "particular": comp.get("name", key),
            "myt_approved": myt_val,
            "claimed": comp.get("claimed", 0),
            "approved": comp.get("approved", 0),
        })
        sl += 1

    # Prior period items (e.g., wage revision)
    for comp in components:
        key = comp.get("key", "")
        if key.startswith("prior_period_"):
            claimed_val = comp.get("claimed", 0)
            approved_val = comp.get("approved", 0)
            if claimed_val > 0 or approved_val > 0:
                rows.append({
                    "sl": sl,
                    "particular": comp.get("name", key),
                    "myt_approved": 0,
                    "claimed": claimed_val,
                    "approved": approved_val,
                })
                sl += 1

    # Total expenditure row
    rows.append({
        "sl": "",
        "particular": "A. TOTAL EXPENDITURE",
        "myt_approved": total_myt,
        "claimed": state.get("total_claimed_expenditure", 0),
        "approved": state.get("total_approved_expenditure", 0),
        "is_total": True,
    })

    # Revenue header
    rows.append({
        "sl": "",
        "particular": "REVENUE",
        "myt_approved": "",
        "claimed": "",
        "approved": "",
        "is_header": True,
    })

    claimed_rev = state.get("claimed_revenues", {})
    approved_rev = state.get("approved_revenues", {})
    rev_items = [
        ("Revenue from Sale of Power", "revenue_from_sale"),
        ("Wheeling Charges", "wheeling_charges"),
        ("Non-Tariff Income", "non_tariff_income"),
        ("Other Revenue", "other_revenue"),
    ]
    total_myt_rev = 0
    for name, key in rev_items:
        claimed_val = claimed_rev.get(key, 0)
        approved_val = approved_rev.get(key, claimed_val)
        myt_rev_val = myt_norms.get(key, 0)
        total_myt_rev += myt_rev_val
        if claimed_val > 0 or approved_val > 0 or key == "revenue_from_sale":
            rows.append({
                "sl": sl,
                "particular": name,
                "myt_approved": myt_rev_val,
                "claimed": claimed_val,
                "approved": approved_val,
            })
            sl += 1

    rows.append({
        "sl": "",
        "particular": "B. TOTAL REVENUE",
        "myt_approved": total_myt_rev,
        "claimed": state.get("total_claimed_revenue", 0),
        "approved": state.get("total_approved_revenue", 0),
        "is_total": True,
    })

    # Gap / Surplus row — show BOTH claimed and approved
    approved_gap = state.get("final_revenue_gap_surplus", 0)
    total_claimed_exp = state.get("total_claimed_expenditure", 0)
    total_claimed_rev = state.get("total_claimed_revenue", 0)
    claimed_gap = round(total_claimed_rev - total_claimed_exp, 2)
    myt_gap = round(total_myt_rev - total_myt, 2)

    rows.append({
        "sl": "",
        "particular": "C. REVENUE GAP(-) / SURPLUS(+)  (B - A)",
        "myt_approved": myt_gap,
        "claimed": claimed_gap,
        "approved": approved_gap,
        "is_total": True,
        "is_gap": True,
    })

    return {
        "caption": "Summary of ARR for Truing Up",
        "unit": "(Rs. in Lakhs)",
        "columns": [
            "Sl. No.", "Particulars",
            "Approved in ARR Order", "Claimed in Truing Up Petition", "Trued Up by Commission",
        ],
        "rows": rows,
    }


def _build_hearing_section(state: dict, para_seq: list[int]) -> dict:
    """Build the Hearing on the Petition section.

    Uses court_hearing data from the state if available (user-supplied via UI),
    otherwise generates default hearing paragraphs from the analysis state.
    """
    licensee = state.get("licensee_name", "")
    fy = state.get("financial_year", "")
    court = state.get("court_hearing", {})

    licensee_full_names = {
        "Infopark": "Infopark Kerala",
        "Technopark": "Technopark",
        "CSEZA": "Cochin Special Economic Zone Authority",
        "KDHP": "Kannan Devan Hills Plantations Company Private Limited",
    }
    full_name = licensee_full_names.get(licensee, licensee)

    paragraphs = []

    hearing_date = court.get("hearing_date", "DD.MM.YYYY")

    # Opening paragraph — hearing date and venue
    paragraphs.append({
        "seq": _next_seq(para_seq),
        "text": (
            f"The petition was posted for hearing on {hearing_date}. "
            f"The representatives of the petitioner M/s {full_name} and the "
            f"respondent M/s Kerala State Electricity Board Limited (KSEB Ltd) "
            f"were present during the hearing."
        ),
    })

    # Licensee submission points
    submissions = court.get("licensee_submissions", [])
    if submissions:
        for sub in submissions:
            paragraphs.append({
                "seq": _next_seq(para_seq),
                "text": sub,
            })
    else:
        # Auto-generate default submission paragraphs from analysis data
        total_claimed = state.get("total_claimed_expenditure", 0)
        total_revenue = state.get("total_claimed_revenue", 0)
        actual_loss = state.get("claimed_distribution_loss_pct", 0)

        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": (
                f"The representatives of the licensee submitted that the total "
                f"expenditure incurred during FY {fy} was Rs. {fmt(total_claimed)} Lakhs "
                f"and the total revenue realized was Rs. {fmt(total_revenue)} Lakhs. "
                f"The licensee requested the Commission to approve the truing up of "
                f"accounts for FY {fy} as per the audited annual accounts."
            ),
        })

        if actual_loss > 0:
            paragraphs.append({
                "seq": _next_seq(para_seq),
                "text": (
                    f"The licensee further submitted that the actual distribution loss "
                    f"during FY {fy} was {actual_loss:.2f}%, which was within the target "
                    f"set by the Commission in the MYT Order. The licensee claimed the "
                    f"benefit of efficiency gain on account of reduction in distribution loss."
                ),
            })

        # Employee cost and O&M submissions
        components = {c["key"]: c for c in state.get("components", [])}
        emp = components.get("employee_cost", {})
        if emp.get("claimed", 0) > 0:
            paragraphs.append({
                "seq": _next_seq(para_seq),
                "text": (
                    f"Regarding employee cost, the licensee submitted that the total "
                    f"employee cost for FY {fy} was Rs. {fmt(emp['claimed'])} Lakhs, "
                    f"which includes basic pay, dearness allowance, provident fund "
                    f"contribution, gratuity, leave encashment and other allowances as "
                    f"per the applicable pay scales and service conditions."
                ),
            })

    # Respondent's (KSEB) position
    respondent_text = court.get("respondent_position", "")
    if respondent_text:
        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": respondent_text,
        })
    else:
        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": (
                f"The respondent KSEB Ltd submitted its verification report on the "
                f"petition filed by {full_name}. The respondent verified the energy "
                f"input, energy sales, and distribution loss figures reported by the "
                f"licensee and confirmed that the figures are in agreement with the "
                f"data available with KSEB Ltd."
            ),
        })

    # Commission's observations
    observations = court.get("commission_observations", "")
    if observations:
        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": observations,
        })
    else:
        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": (
                f"The Commission has heard both the parties and examined the petition "
                f"in detail along with the audited annual accounts, ARR schedules and "
                f"supporting annexures. The Commission has also considered the verification "
                f"report submitted by KSEB Ltd. The Commission now proceeds to examine each "
                f"component of the ARR and revenue on a prudence check basis."
            ),
        })

    return {"paragraphs": paragraphs}


def _build_energy_sales_section(state: dict, para_seq: list[int], table_seq: list[int] = None) -> dict:
    """Build the Energy Sales section with consumer mix table."""
    if table_seq is None:
        table_seq = [0]
    licensee = state.get("licensee_name", "")
    fy = state.get("financial_year", "")

    paragraphs = [
        {
            "seq": _next_seq(para_seq),
            "text": (
                f"The Commission has examined the energy sales data submitted by "
                f"{licensee} for FY {fy}. The licensee has reported category-wise "
                f"energy sales and the corresponding revenue realized. The details "
                f"are given in the table below."
            ),
        },
    ]

    # Consumer mix table
    tables = []
    consumer_mix = state.get("consumer_mix", [])
    energy_sales_mu = state.get("energy_sales_mu", 0)
    total_consumers = 0
    total_sales = 0

    if consumer_mix:
        table_rows = []
        sl = 1
        for cat in consumer_mix:
            cat_name = cat.get("category", "")
            count = cat.get("consumer_count", 0)
            sales = cat.get("sales_mu", 0)
            total_consumers += count
            total_sales += sales
            table_rows.append({
                "sl": sl,
                "particular": cat_name,
                "cells": [count, f"{sales:.2f}"],
            })
            sl += 1

        table_rows.append({
            "sl": "",
            "particular": "Total",
            "cells": [total_consumers, f"{total_sales:.2f}"],
            "is_total": True,
        })

        tables.append(_number_table({
            "caption": "Category-wise Consumer Count and Energy Sales",
            "unit": "",
            "columns": ["Sl. No.", "Category", "No. of Consumers", "Sales (MU)"],
            "rows": table_rows,
        }, table_seq))
    elif energy_sales_mu > 0:
        # Fallback: single-row summary if no category breakdown available
        tables.append(_number_table({
            "caption": "Energy Sales Summary",
            "unit": "",
            "columns": ["Particulars", "Amount"],
            "rows": [
                {"particular": "Total Energy Sales (MU)", "amount": energy_sales_mu},
            ],
        }, table_seq))

    return {
        "id": "energy_sales",
        "title": "Energy Sales and Revenue",
        "paragraphs": paragraphs,
        "tables": tables,
        "decision": None,
    }


def _build_distribution_loss_section(state: dict, para_seq: list[int], table_seq: list[int] = None) -> dict:
    """Build the Distribution Loss section with detailed loss calculation table."""
    if table_seq is None:
        table_seq = [0]
    actual_loss = state.get("claimed_distribution_loss_pct", 0)
    target_loss = state.get("target_distribution_loss_pct", 0)
    fy = state.get("financial_year", "")
    licensee = state.get("licensee_name", "")

    # Get loss computation details from state
    energy_input = state.get("energy_input_mu", 0)
    energy_sales = state.get("energy_sales_mu", 0)
    wheeled_output = state.get("wheeled_output_mu", 0)
    total_output = energy_sales + wheeled_output
    loss_mu = round(energy_input - total_output, 2) if energy_input > 0 else 0
    appc = state.get("appc_rs_per_kwh", 0)  # Average PPC Rs/kWh

    paragraphs = [
        {
            "seq": _next_seq(para_seq),
            "text": (
                f"The licensee has reported an actual distribution loss of {actual_loss:.2f}% "
                f"for FY {fy}. The target distribution loss approved in the MYT Order "
                f"is {target_loss:.2f}%. The details of the distribution loss computation "
                f"are given in the table below."
            ),
        },
    ]

    # Build distribution loss calculation table
    table_rows = [
        {"particular": "Energy Sales (MU)", "cells": [energy_sales]},
        {"particular": "Wheeled Output (MU)", "cells": [wheeled_output]},
        {"particular": "Total Output (MU)", "cells": [total_output], "is_total": True},
        {"particular": "Energy Input (MU)", "cells": [energy_input]},
        {"particular": "Distribution Loss (MU)", "cells": [loss_mu]},
        {"particular": "Distribution Loss (%)", "cells": [f"{actual_loss:.2f}%"]},
        {"particular": "Target Loss (%)", "cells": [f"{target_loss:.2f}%"]},
    ]

    if actual_loss > target_loss and energy_input > 0:
        excess_loss_pct = round(actual_loss - target_loss, 2)
        excess_loss_mu = round(energy_input * excess_loss_pct / 100, 2)
        penalty = round(excess_loss_mu * appc * 10, 2)  # MU × Rs/kWh × 10 = Rs Lakhs

        table_rows.extend([
            {"particular": "Excess Loss (%)", "cells": [f"{excess_loss_pct:.2f}%"]},
            {"particular": "Excess Loss (MU)", "cells": [excess_loss_mu]},
            {"particular": "APPC (Rs/kWh)", "cells": [f"{appc:.2f}" if appc else "—"]},
            {"particular": "Penalty for Excess Loss (Rs. Lakhs)", "cells": [penalty], "is_total": True},
        ])

        decision_text = (
            f"The actual distribution loss of {actual_loss:.2f}% exceeds the target of "
            f"{target_loss:.2f}% approved in the MYT Order. The excess loss of "
            f"{excess_loss_pct:.2f}% translates to {excess_loss_mu:.2f} MU. The Commission "
            f"shall apply a penalty of Rs. {fmt(penalty)} Lakhs (computed at the APPC of "
            f"Rs. {appc:.2f}/kWh) on the approved Power Purchase Cost as per Regulation 73(3)."
        )
    else:
        decision_text = (
            f"The actual distribution loss of {actual_loss:.2f}% is within the target of "
            f"{target_loss:.2f}% approved in the MYT Order. No penalty for excess "
            f"distribution loss is applicable."
        )

    paragraphs.append({
        "seq": _next_seq(para_seq),
        "text": decision_text,
        "is_decision": True,
    })

    loss_table = _number_table({
        "caption": "Distribution Loss Computation",
        "unit": "",
        "columns": ["Particulars", "Amount"],
        "rows": table_rows,
    }, table_seq)

    return {
        "id": "distribution_loss",
        "title": "Distribution Loss",
        "paragraphs": paragraphs,
        "tables": [loss_table],
        "decision": decision_text,
    }



def _build_component_section(
    comp: dict, section_id: str, state: dict, para_seq: list[int],
    table_seq: list[int] = None,
) -> dict:
    """Build an expense component section. Handles special cases for PPC,
    Employee Cost, Interest on Consumer Deposits, and Interest on Working Capital."""
    key = comp.get("key", "")
    name = comp.get("name", "")
    claimed = comp.get("claimed", 0)
    approved = comp.get("approved", 0)
    # Source MYT norm: try proposed_myt first, fall back to myt_baseline_norms
    myt_norm = comp.get("proposed_myt", 0)
    if not myt_norm:
        myt_norms_dict = state.get("myt_baseline_norms", {})
        myt_norm = myt_norms_dict.get(key, 0)
    variance = comp.get("variance", 0)
    justification = comp.get("justification", "")
    status = comp.get("status", "approved")
    fy = state.get("financial_year", "")
    if table_seq is None:
        table_seq = [0]

    # ── Zero-claim handling: no table, text only ──────────────────────
    if claimed == 0 and approved == 0:
        paragraphs = [{
            "seq": _next_seq(para_seq),
            "text": (
                f"The licensee has not claimed any amount towards {name} "
                f"for FY {fy}. The Commission has not approved any amount "
                f"for the same."
            ),
        }]
        return {
            "id": section_id,
            "title": name,
            "paragraphs": paragraphs,
            "tables": [],
            "decision": paragraphs[0]["text"],
        }

    paragraphs = []
    tables = []

    # ── Special case: PPC ─────────────────────────────────────────────
    if key == "power_purchase_cost":
        return _build_ppc_section(comp, section_id, state, para_seq, table_seq)

    # ── Special case: Employee Cost ───────────────────────────────────
    if key == "employee_cost":
        return _build_employee_cost_section(comp, section_id, state, para_seq, table_seq)

    # ── Special case: Interest on Consumer Security Deposits ──────────
    if key == "interest_consumer_deposits":
        return _build_interest_deposits_section(comp, section_id, state, para_seq, table_seq)

    # ── Special case: Interest on Working Capital ─────────────────────
    if key == "interest_working_capital":
        return _build_interest_wc_section(comp, section_id, state, para_seq, table_seq)

    # ── Generic component ─────────────────────────────────────────────
    # Paragraph 1: What was claimed
    paragraphs.append({
        "seq": _next_seq(para_seq),
        "text": (
            f"The licensee has claimed Rs. {fmt(claimed)} Lakhs towards {name} "
            f"for FY {fy}. The MYT approved norm for this component is "
            f"Rs. {fmt(myt_norm)} Lakhs."
        ),
    })

    # Paragraph 2: Regulation & analysis (from justification)
    if justification:
        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": justification,
        })

    # Decision sentence
    if status == "reduced":
        decision = (
            f"The Commission approves Rs. {fmt(approved)} Lakhs towards {name} "
            f"for FY {fy}, disallowing Rs. {fmt(abs(variance))} Lakhs."
        )
    elif status == "increased":
        decision = (
            f"The Commission approves Rs. {fmt(approved)} Lakhs towards {name} "
            f"for FY {fy}."
        )
    else:
        decision = (
            f"The Commission approves the claimed amount of Rs. {fmt(approved)} Lakhs "
            f"towards {name} for FY {fy}."
        )

    paragraphs.append({
        "seq": _next_seq(para_seq),
        "text": decision,
        "is_decision": True,
    })

    # 3-column comparison table with KSERC standard headers
    table = _number_table({
        "caption": f"{name}",
        "unit": "(Rs. in Lakhs)",
        "columns": ["Particulars", "Approved in ARR Order", "Claimed in Truing Up Petition", "Trued Up by Commission"],
        "rows": [
            {"particular": name, "myt_approved": myt_norm, "claimed": claimed, "approved": approved, "is_total": True},
        ],
    }, table_seq)
    tables.append(table)

    return {
        "id": section_id,
        "title": name,
        "paragraphs": paragraphs,
        "tables": tables,
        "decision": decision,
    }


def _build_ppc_section(comp: dict, section_id: str, state: dict, para_seq: list[int], table_seq: list[int] = None) -> dict:
    """Build PPC section with correct KSERC table format."""
    if table_seq is None:
        table_seq = [0]
    name = comp.get("name", "Power Purchase Cost")
    claimed = comp.get("claimed", 0)
    approved = comp.get("approved", 0)
    justification = comp.get("justification", "")
    fy = state.get("financial_year", "")

    # Get penalty info from state
    actual_loss = state.get("claimed_distribution_loss_pct", 0)
    target_loss = state.get("target_distribution_loss_pct", 0)
    energy_input = state.get("energy_input_mu", 0)
    appc = state.get("appc_rs_per_kwh", 0)

    penalty = 0
    if actual_loss > target_loss and energy_input > 0:
        excess_loss_pct = round(actual_loss - target_loss, 2)
        excess_loss_mu = round(energy_input * excess_loss_pct / 100, 2)
        penalty = round(excess_loss_mu * appc * 10, 2)

    paragraphs = [
        {
            "seq": _next_seq(para_seq),
            "text": (
                f"The licensee has claimed Rs. {fmt(claimed)} Lakhs towards "
                f"Power Purchase Cost for FY {fy}."
            ),
        },
    ]

    if justification:
        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": justification,
        })

    if penalty > 0:
        ppc_approved = round(claimed - penalty, 2)
        decision = (
            f"After deducting the penalty of Rs. {fmt(penalty)} Lakhs for excess "
            f"distribution loss, the Commission approves Rs. {fmt(approved)} Lakhs "
            f"towards Power Purchase Cost for FY {fy}."
        )
    else:
        decision = (
            f"The Commission approves Rs. {fmt(approved)} Lakhs towards "
            f"Power Purchase Cost for FY {fy}."
        )

    paragraphs.append({
        "seq": _next_seq(para_seq),
        "text": decision,
        "is_decision": True,
    })

    # PPC Table in correct KSERC format
    table_rows = [
        {"particular": "Cost of Power Purchase (Claimed)", "amount": claimed},
    ]
    if penalty > 0:
        table_rows.append(
            {"particular": "Less: Penalty for Excess Distribution Loss", "amount": -penalty},
        )
    table_rows.append(
        {"particular": "Total Approved Power Purchase Cost", "amount": approved, "is_total": True},
    )

    table = _number_table({
        "caption": "Power Purchase Cost",
        "unit": "(Rs. in Lakhs)",
        "columns": ["Particulars", "Amount"],
        "rows": table_rows,
    }, table_seq)

    return {
        "id": section_id,
        "title": "Power Purchase Cost",
        "paragraphs": paragraphs,
        "tables": [table],
        "decision": decision,
    }


def _build_employee_cost_section(comp: dict, section_id: str, state: dict, para_seq: list[int], table_seq: list[int] = None) -> dict:
    """Build Employee Cost section with sub-component breakdown."""
    if table_seq is None:
        table_seq = [0]
    name = comp.get("name", "Employee Cost")
    claimed = comp.get("claimed", 0)
    approved = comp.get("approved", 0)
    myt_norm = comp.get("proposed_myt", 0)
    if not myt_norm:
        myt_norm = state.get("myt_baseline_norms", {}).get("employee_cost", 0)
    justification = comp.get("justification", "")
    status = comp.get("status", "approved")
    fy = state.get("financial_year", "")
    variance = comp.get("variance", 0)

    # Sub-components from state
    emp_details = state.get("employee_cost_details", {})
    basic_pay = emp_details.get("basic_pay_allowances", claimed)
    terminal_benefits = emp_details.get("terminal_benefits", 0)
    wage_revision = state.get("wage_revision_amount", 0)  # canonical figure
    base_employee = round(claimed - wage_revision, 2) if wage_revision else claimed

    paragraphs = [
        {
            "seq": _next_seq(para_seq),
            "text": (
                f"The licensee has claimed Rs. {fmt(claimed)} Lakhs towards {name} "
                f"for FY {fy}. The MYT approved norm for Employee Cost is "
                f"Rs. {fmt(myt_norm)} Lakhs."
            ),
        },
    ]

    if justification:
        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": justification,
        })

    if status == "reduced":
        decision = (
            f"The Commission approves Rs. {fmt(approved)} Lakhs towards {name} "
            f"for FY {fy}, disallowing Rs. {fmt(abs(variance))} Lakhs."
        )
    else:
        decision = (
            f"The Commission approves Rs. {fmt(approved)} Lakhs towards "
            f"{name} for FY {fy}."
        )

    paragraphs.append({
        "seq": _next_seq(para_seq),
        "text": decision,
        "is_decision": True,
    })

    # Employee cost sub-component table
    table_rows = [
        {"particular": "Basic Pay & Allowances", "myt_approved": "", "claimed": basic_pay, "approved": ""},
        {"particular": "Terminal Benefits", "myt_approved": "", "claimed": terminal_benefits, "approved": ""},
    ]
    if wage_revision > 0:
        table_rows.append(
            {"particular": "Wage Revision (Prior Period)", "myt_approved": "", "claimed": wage_revision, "approved": ""},
        )
    table_rows.append(
        {"particular": "Total Employee Cost", "myt_approved": myt_norm, "claimed": claimed, "approved": approved, "is_total": True},
    )

    table = _number_table({
        "caption": "Employee Cost",
        "unit": "(Rs. in Lakhs)",
        "columns": ["Particulars", "Approved in ARR Order", "Claimed in Truing Up Petition", "Trued Up by Commission"],
        "rows": table_rows,
    }, table_seq)

    return {
        "id": section_id,
        "title": "Employee Cost",
        "paragraphs": paragraphs,
        "tables": [table],
        "decision": decision,
    }


def _build_interest_deposits_section(comp: dict, section_id: str, state: dict, para_seq: list[int], table_seq: list[int] = None) -> dict:
    """Build Interest on Consumer Security Deposits section with regulatory justification."""
    if table_seq is None:
        table_seq = [0]
    name = comp.get("name", "Interest on Consumer Security Deposits")
    claimed = comp.get("claimed", 0)
    approved = comp.get("approved", 0)
    justification = comp.get("justification", "")
    fy = state.get("financial_year", "")

    paragraphs = []

    if claimed == 0 and approved > 0:
        # Explain why Commission approves even when not claimed
        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": (
                f"The licensee has not claimed any amount towards {name} for FY {fy}. "
                f"However, as per Regulation 79 of the KSERC Tariff Regulations, 2021, "
                f"interest on consumer security deposits is an admissible expenditure "
                f"that the licensee is entitled to include in the ARR. The Commission "
                f"computes this normatively based on the security deposit balance and "
                f"the applicable rate prescribed under the Kerala Electricity Supply Code."
            ),
        })
    else:
        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": (
                f"The licensee has claimed Rs. {fmt(claimed)} Lakhs towards "
                f"{name} for FY {fy}."
            ),
        })

    if justification:
        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": justification,
        })

    decision = (
        f"The Commission approves Rs. {fmt(approved)} Lakhs towards "
        f"{name} for FY {fy}."
    )
    paragraphs.append({
        "seq": _next_seq(para_seq),
        "text": decision,
        "is_decision": True,
    })

    # Interest computation table
    interest_data = state.get("interest_computation", {})
    comp_d = interest_data.get("component_d", {})
    sd_balance = comp_d.get("opening_balance", 0)
    sd_rate = comp_d.get("supply_code_rate", 0)

    table_rows = [
        {"particular": "Consumer Security Deposit Balance (Rs. Lakhs)", "amount": sd_balance},
        {"particular": f"Rate of Interest (%)", "amount": f"{sd_rate:.2f}%" if sd_rate else "—"},
        {"particular": "Interest on Consumer Security Deposits", "amount": approved, "is_total": True},
    ]

    table = _number_table({
        "caption": "Interest on Consumer Security Deposits",
        "unit": "(Rs. in Lakhs)",
        "columns": ["Particulars", "Amount"],
        "rows": table_rows,
    }, table_seq)

    return {
        "id": section_id,
        "title": name,
        "paragraphs": paragraphs,
        "tables": [table],
        "decision": decision,
    }


def _build_interest_wc_section(comp: dict, section_id: str, state: dict, para_seq: list[int], table_seq: list[int] = None) -> dict:
    """Build Interest on Working Capital section with detailed WC computation table."""
    if table_seq is None:
        table_seq = [0]
    name = comp.get("name", "Interest on Working Capital")
    claimed = comp.get("claimed", 0)
    approved = comp.get("approved", 0)
    justification = comp.get("justification", "")
    fy = state.get("financial_year", "")

    paragraphs = []

    if claimed == 0 and approved > 0:
        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": (
                f"The licensee has not claimed any amount towards {name} for FY {fy}. "
                f"However, as per Regulation 78 of the KSERC Tariff Regulations, 2021, "
                f"interest on normative working capital is an admissible expense. The "
                f"Commission computes the normative working capital requirement and the "
                f"applicable interest thereon, as the licensee is entitled to this "
                f"allowance under the Regulations."
            ),
        })
    else:
        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": (
                f"The licensee has claimed Rs. {fmt(claimed)} Lakhs towards "
                f"{name} for FY {fy}."
            ),
        })

    if justification:
        paragraphs.append({
            "seq": _next_seq(para_seq),
            "text": justification,
        })

    decision = (
        f"The Commission approves Rs. {fmt(approved)} Lakhs towards "
        f"{name} for FY {fy}."
    )
    paragraphs.append({
        "seq": _next_seq(para_seq),
        "text": decision,
        "is_decision": True,
    })

    # Working Capital Computation Table
    interest_data = state.get("interest_computation", {})
    comp_c = interest_data.get("component_c", {})
    om_one_month = comp_c.get("om_one_month", 0)
    maint_spares = comp_c.get("maintenance_spares", 0)
    receivables = comp_c.get("receivables_two_months", 0)
    security_deposit = comp_c.get("cash_security_deposit", 0)
    net_wc = comp_c.get("net_working_capital", 0)
    wc_rate = comp_c.get("rate", 0)

    table_rows = [
        {"particular": "O&M Expenses — One Month", "amount": om_one_month},
        {"particular": "Maintenance Spares (15% of R&M)", "amount": maint_spares},
        {"particular": "Receivables — Two Months", "amount": receivables},
        {"particular": "Less: Consumer Security Deposits", "amount": -security_deposit if security_deposit else 0},
        {"particular": "Normative Working Capital", "amount": net_wc, "is_total": True},
        {"particular": f"Interest Rate (%)", "amount": f"{wc_rate:.2f}%" if wc_rate else "—"},
        {"particular": "Interest on Working Capital", "amount": approved, "is_total": True},
    ]

    table = _number_table({
        "caption": "Working Capital Computation",
        "unit": "(Rs. in Lakhs)",
        "columns": ["Particulars", "Amount"],
        "rows": table_rows,
    }, table_seq)

    return {
        "id": section_id,
        "title": name,
        "paragraphs": paragraphs,
        "tables": [table],
        "decision": decision,
    }



def _build_revenue_from_sale_section(state: dict, para_seq: list[int]) -> dict:
    """Build Revenue from Sale of Power section."""
    claimed_rev = state.get("claimed_revenues", {})
    revenue = claimed_rev.get("revenue_from_sale", 0)
    fy = state.get("financial_year", "")

    paragraphs = [
        {
            "seq": _next_seq(para_seq),
            "text": (
                f"The licensee has reported revenue from sale of power of "
                f"Rs. {fmt(revenue)} Lakhs for FY {fy}. The Commission has examined "
                f"the category-wise energy sales and the corresponding tariff revenue."
            ),
        },
        {
            "seq": _next_seq(para_seq),
            "text": (
                f"The Commission approves the revenue from sale of power at "
                f"Rs. {fmt(revenue)} Lakhs for FY {fy} as reported by the licensee."
            ),
            "is_decision": True,
        },
    ]

    return {
        "id": "revenue_from_sale",
        "title": "Revenue from Sale of Power",
        "paragraphs": paragraphs,
        "tables": [],
        "decision": paragraphs[-1]["text"],
    }


def _build_wheeling_section(state: dict, para_seq: list[int]) -> dict:
    """Build Wheeling Charges section."""
    claimed_rev = state.get("claimed_revenues", {})
    wheeling = claimed_rev.get("wheeling_charges", 0)
    fy = state.get("financial_year", "")

    if wheeling > 0:
        text = (
            f"The licensee has reported wheeling charge income of Rs. {fmt(wheeling)} Lakhs "
            f"for FY {fy}. The Commission approves the same."
        )
    else:
        text = (
            f"The licensee has not reported any wheeling charge income for FY {fy}."
        )

    paragraphs = [{"seq": _next_seq(para_seq), "text": text}]

    return {
        "id": "wheeling_charges",
        "title": "Wheeling Charges",
        "paragraphs": paragraphs,
        "tables": [],
        "decision": text if wheeling > 0 else None,
    }


def _build_nti_section(state: dict, para_seq: list[int]) -> dict:
    """Build Non-Tariff Income section."""
    claimed_rev = state.get("claimed_revenues", {})
    nti = claimed_rev.get("non_tariff_income", 0)
    fy = state.get("financial_year", "")

    if nti > 0:
        text = (
            f"The licensee has reported non-tariff income of Rs. {fmt(nti)} Lakhs "
            f"for FY {fy}, comprising delayed payment surcharge, meter rent, "
            f"miscellaneous receipts and other income. The Commission approves the same."
        )
    else:
        text = (
            f"The licensee has not reported any non-tariff income for FY {fy}."
        )

    paragraphs = [{"seq": _next_seq(para_seq), "text": text}]

    return {
        "id": "non_tariff_income",
        "title": "Non-Tariff Income",
        "paragraphs": paragraphs,
        "tables": [],
        "decision": text if nti > 0 else None,
    }


def _build_arr_gap_section(state: dict, para_seq: list[int], table_seq: list[int] = None) -> dict:
    """Build the ARR & Revenue Gap/Surplus summary section."""
    if table_seq is None:
        table_seq = [0]
    total_exp = state.get("total_approved_expenditure", 0)
    total_rev = state.get("total_approved_revenue", 0)
    gap = state.get("final_revenue_gap_surplus", 0)
    fy = state.get("financial_year", "")
    licensee = state.get("licensee_name", "")

    is_surplus = gap >= 0

    paragraphs = [
        {
            "seq": _next_seq(para_seq),
            "text": (
                f"After examination of all expense heads and revenue items, "
                f"the Commission approves a total expenditure of Rs. {fmt(total_exp)} Lakhs "
                f"and total revenue of Rs. {fmt(total_rev)} Lakhs for {licensee} "
                f"for FY {fy}."
            ),
        },
        {
            "seq": _next_seq(para_seq),
            "text": (
                f"The Commission determines a revenue {'surplus' if is_surplus else 'gap'} "
                f"of Rs. {fmt(abs(gap))} Lakhs for FY {fy}. "
                f"This {'surplus' if is_surplus else 'gap'} shall be carried forward "
                f"and adjusted in the next tariff revision."
            ),
            "is_decision": True,
        },
    ]

    # Full ARR table
    arr_table = _number_table(_build_full_arr_table(state), table_seq)

    return {
        "id": "arr_gap",
        "title": "Approved ARR and Revenue Gap",
        "paragraphs": paragraphs,
        "tables": [arr_table],
        "decision": paragraphs[-1]["text"],
    }


def _build_full_arr_table(state: dict) -> dict:
    """Build the 3-column comprehensive ARR & Revenue Summary table (Table 15)."""
    components = state.get("components", [])
    myt_norms = state.get("myt_baseline_norms", {})
    claimed_rev = state.get("claimed_revenues", {})
    approved_rev = state.get("approved_revenues", {})
    approved = state.get("approved_expenses", {})

    rows = []
    sl = 1

    # Expenditure section header
    rows.append({
        "sl": "",
        "particular": "EXPENDITURE",
        "myt_approved": "",
        "claimed": "",
        "approved": "",
        "is_header": True,
    })

    total_myt = 0
    # Standard components
    for comp in components:
        key = comp.get("key", "")
        if key.startswith("prior_period_"):
            continue
        myt_val = comp.get("proposed_myt", 0) or myt_norms.get(key, 0)
        total_myt += myt_val
        rows.append({
            "sl": sl,
            "particular": comp.get("name", key),
            "myt_approved": myt_val,
            "claimed": comp.get("claimed", 0),
            "approved": comp.get("approved", 0),
        })
        sl += 1

    # Prior period items
    prior_items = [c for c in components if c.get("key", "").startswith("prior_period_")]
    if not prior_items:
        for key, amount in approved.items():
            if key.startswith("prior_period_") and amount > 0:
                display_name = key.replace("prior_period_", "").replace("_", " ").title()
                rows.append({
                    "sl": sl,
                    "particular": f"Prior Period: {display_name}",
                    "myt_approved": 0,
                    "claimed": amount,
                    "approved": amount,
                })
                sl += 1
    else:
        for comp in prior_items:
            claimed_val = comp.get("claimed", 0)
            approved_val = comp.get("approved", 0)
            if claimed_val > 0 or approved_val > 0:
                rows.append({
                    "sl": sl,
                    "particular": comp.get("name", comp.get("key", "")),
                    "myt_approved": 0,
                    "claimed": claimed_val,
                    "approved": approved_val,
                })
                sl += 1

    # Total Expenditure
    rows.append({
        "sl": "",
        "particular": "A. TOTAL APPROVED EXPENDITURE",
        "myt_approved": total_myt,
        "claimed": state.get("total_claimed_expenditure", 0),
        "approved": state.get("total_approved_expenditure", 0),
        "is_total": True,
    })

    # Revenue section
    rows.append({
        "sl": "",
        "particular": "REVENUE",
        "myt_approved": "",
        "claimed": "",
        "approved": "",
        "is_header": True,
    })

    rev_items = [
        ("Revenue from Sale of Power", "revenue_from_sale"),
        ("Wheeling Charges", "wheeling_charges"),
        ("Non-Tariff Income", "non_tariff_income"),
        ("Other Revenue", "other_revenue"),
    ]
    total_myt_rev = 0
    for name, key in rev_items:
        claimed_val = claimed_rev.get(key, 0)
        approved_val = approved_rev.get(key, claimed_val)
        myt_rev_val = myt_norms.get(key, 0)
        total_myt_rev += myt_rev_val
        if claimed_val > 0 or approved_val > 0 or key == "revenue_from_sale":
            rows.append({
                "sl": sl,
                "particular": name,
                "myt_approved": myt_rev_val,
                "claimed": claimed_val,
                "approved": approved_val,
            })
            sl += 1

    rows.append({
        "sl": "",
        "particular": "B. TOTAL REVENUE",
        "myt_approved": total_myt_rev,
        "claimed": state.get("total_claimed_revenue", 0),
        "approved": state.get("total_approved_revenue", 0),
        "is_total": True,
    })

    # Gap / Surplus — show both claimed and approved
    approved_gap = state.get("final_revenue_gap_surplus", 0)
    total_claimed_exp = state.get("total_claimed_expenditure", 0)
    total_claimed_rev = state.get("total_claimed_revenue", 0)
    claimed_gap = round(total_claimed_rev - total_claimed_exp, 2)
    myt_gap = round(total_myt_rev - total_myt, 2)

    rows.append({
        "sl": "",
        "particular": "C. REVENUE GAP(-) / SURPLUS(+)  (B - A)",
        "myt_approved": myt_gap,
        "claimed": claimed_gap,
        "approved": approved_gap,
        "is_total": True,
        "is_gap": True,
    })

    return {
        "caption": "Approved ARR and Revenue Summary",
        "unit": "(Rs. in Lakhs)",
        "columns": [
            "Sl. No.", "Particulars",
            "Approved in ARR Order", "Claimed in Truing Up Petition", "Trued Up by Commission",
        ],
        "rows": rows,
    }


def _build_orders(state: dict, para_seq: list[int]) -> dict:
    """Build the Orders of the Commission section with lettered sub-items."""
    total_exp = state.get("total_approved_expenditure", 0)
    total_rev = state.get("total_approved_revenue", 0)
    gap = state.get("final_revenue_gap_surplus", 0)
    licensee = state.get("licensee_name", "")
    fy = state.get("financial_year", "")
    is_surplus = gap >= 0

    intro_para = {
        "seq": _next_seq(para_seq),
        "text": (
            f"Having considered the petition, the audited accounts, the submissions "
            f"of the licensee, and the provisions of the KSERC (Terms and Conditions "
            f"for Determination of Tariff) Regulations, 2021, the Commission hereby "
            f"orders as follows:"
        ),
    }

    items = [
        {
            "letter": "a",
            "text": (
                f"The total approved expenditure for {licensee} for FY {fy} "
                f"is Rs. {fmt(total_exp)} Lakhs."
            ),
        },
        {
            "letter": "b",
            "text": (
                f"The total approved revenue for {licensee} for FY {fy} "
                f"is Rs. {fmt(total_rev)} Lakhs."
            ),
        },
        {
            "letter": "c",
            "text": (
                f"The revenue {'surplus' if is_surplus else 'gap'} of "
                f"Rs. {fmt(abs(gap))} Lakhs is determined for FY {fy}. "
                f"This {'surplus' if is_surplus else 'gap'} shall be carried forward "
                f"and adjusted in the next tariff determination."
            ),
        },
        {
            "letter": "d",
            "text": (
                f"The licensee is directed to submit the compliance report "
                f"along with the updated asset register within 30 days "
                f"of this order."
            ),
        },
    ]

    return {
        "intro_para": intro_para,
        "order_items": items,
        "paragraphs": [],  # empty fallback
    }


def _build_signature() -> dict:
    """Build the signature block."""
    return {
        "members": [
            {"name": "Sri. T.K Jose", "designation": "Chairman"},
            {"name": "Adv. A. J. Wilson", "designation": "Member"},
            {"name": "Sri. B. Pradeep", "designation": "Member"},
        ],
        "secretary": {
            "name": "C.R.Satheesh Chandran",
            "designation": "Secretary",
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# Utility Functions
# ═══════════════════════════════════════════════════════════════════════

def _next_seq(para_seq: list[int]) -> int:
    """Get next paragraph sequence number and increment."""
    val = para_seq[0]
    para_seq[0] += 1
    return val


def _renumber_paragraphs(order_json: dict) -> None:
    """
    Re-number ALL paragraphs across the entire document sequentially.
    Ensures strictly increasing seq with no gaps.
    """
    seq = 1

    # Introduction
    intro = order_json.get("introduction", {})
    for p in intro.get("paragraphs", []):
        p["seq"] = seq
        seq += 1

    # Hearing
    hearing = order_json.get("hearing", {})
    for p in hearing.get("paragraphs", []):
        p["seq"] = seq
        seq += 1

    # All sections
    for section in order_json.get("sections", []):
        for p in section.get("paragraphs", []):
            p["seq"] = seq
            seq += 1

    # Orders
    orders = order_json.get("orders", {})
    for p in orders.get("paragraphs", []):
        p["seq"] = seq
        seq += 1


def _assign_table_numbers(order_json: dict) -> None:
    """Auto-assign sequential table numbers across the document."""
    num = 1

    # Introduction tables
    intro = order_json.get("introduction", {})
    for table in intro.get("tables", []):
        table["number"] = num
        num += 1

    # Section tables
    for section in order_json.get("sections", []):
        for table in section.get("tables", []):
            table["number"] = num
            num += 1
