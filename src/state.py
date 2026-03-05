"""
KSERC SDL Truing Up — LangGraph State Schema
=============================================

TypedDict schema that flows through all agents in the graph.
Uses Annotated + operator.add for the disallowance_log so that
each agent node *appends* rather than overwrites.
"""

from typing import TypedDict, List, Dict, Any, Annotated, Optional
import operator


class TruingUpState(TypedDict):
    """Shared state for the KSERC SDL Truing-Up multi-agent pipeline."""

    # ── Petition Metadata ──────────────────────────────────────────────
    licensee_name: str          # Technopark | Infopark | CSEZA | KDHP
    financial_year: str         # e.g. "2022-23"
    petition_pdf_path: str      # Absolute path to the input PDF
    petition_number: str        # e.g. "OP 84/2023"

    # ── Extracted Data (from Extractor Agent) ──────────────────────────
    claimed_expenses: Dict[str, float]
    # Keys: power_purchase_cost, employee_cost, repair_maintenance,
    #        admin_general, depreciation, interest_finance, return_on_nfa,
    #        section3_1_duty, other_expenses

    claimed_revenues: Dict[str, float]
    # Keys: energy_charges, non_tariff_income, other_revenue

    asset_register: List[Dict[str, Any]]
    # Each dict: {asset_name, gross_value, accumulated_depreciation,
    #             net_value, funding_source}

    claimed_distribution_loss_pct: float
    target_distribution_loss_pct: float
    energy_units_purchased_mu: float

    # ── MYT Baseline Data (loaded from JSONs) ─────────────────────────
    myt_baseline_norms: Dict[str, float]
    # Keys mirror claimed_expenses for side-by-side comparison

    # ── Processed Data (from Auditor Agent) ────────────────────────────
    approved_expenses: Dict[str, float]
    approved_revenues: Dict[str, float]

    disallowance_log: Annotated[List[Dict[str, Any]], operator.add]
    # Each entry: {"item": str, "claimed": float, "approved": float,
    #              "amount_cut": float, "justification": str}

    prior_approval_status: Dict[str, bool]
    precedent_warnings: List[str]

    # ── Financial Summary ──────────────────────────────────────────────
    total_claimed_expenditure: float
    total_approved_expenditure: float
    total_claimed_revenue: float
    total_approved_revenue: float
    final_revenue_gap_surplus: float   # Positive = surplus, Negative = gap

    # ── Imputed Income ─────────────────────────────────────────────────
    accumulated_surplus: float
    imputed_interest_on_surplus: float

    # ── Human-in-the-Loop ──────────────────────────────────────────────
    human_override_notes: Optional[str]  # Free-text from reviewer

    # ── Final Output ───────────────────────────────────────────────────
    output_pdf_path: str
