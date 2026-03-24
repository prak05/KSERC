"""
KSERC SDL Truing Up — LangGraph State Schema
=============================================

TypedDict schema that flows through all agents in the graph.
Uses Annotated + operator.add for the disallowance_log so that
each agent node *appends* rather than overwrites.
"""

from typing import TypedDict, List, Dict, Any, Annotated, Optional, Tuple
import operator


class TruingUpState(TypedDict):
    """Shared state for the KSERC SDL Truing-Up multi-agent pipeline."""

    # ── Petition Metadata ──────────────────────────────────────────────
    licensee_name: str          # Technopark | Infopark | CSEZA | KDHP
    financial_year: str         # e.g. "2022-23"
    petition_pdf_path: str      # Absolute path to the MAIN petition PDF
    petition_input_path: str    # Original input (can be file OR folder)
    annexure_pdf_paths: List[str]  # Paths to supporting annexure PDFs
    petition_number: str        # e.g. "OP 84/2023"
    petition_text: str          # Full extracted text from petition + annexures

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

    # ── Energy Balance and Loss Data (from Extractor, for PPC Audit) ────
    actual_loss_lakh_units: float       # Actual distribution loss from petition Energy Balance table (LU)
    approved_loss_lakh_units: float     # Computed by auditor: energy_input × target% / 100 (LU)
    energy_input_lakh_units: float      # Total energy into system (ALL sources) from Energy Balance table (LU)
    energy_purchased_lakh_units: float  # Energy purchased from KSEB — from Power Purchase table (LU)
    appc_rs_per_unit: float             # Average Power Purchase Cost from petition (Rs/unit)
    bee_energy_audit_fee: float         # BEE Energy Audit Fee (Rs Lakhs) — from petition or MYT norms
    wage_revision_current_year: float   # Current FY wage/pay revision impact (Rs Lakhs) — from petition
    wage_revision_prior_period: float   # Prior period wage revision arrears (Rs Lakhs) — from petition

    # ── MYT Baseline Data (loaded from JSONs) ─────────────────────────
    myt_baseline_norms: Dict[str, float]
    # Keys mirror claimed_expenses for side-by-side comparison

    # ── KSERC Cross-Licensee Methodology (from ALL past orders) ────────
    kserc_methodology_rules: Dict[str, Any]
    # Learned from ALL past orders, regulations, and amendments

    # ── AI Deep Analysis Results ───────────────────────────────────────
    ai_insights: Dict[str, Any]
    # Output from AI Commission (deep analyzer), if used

    # ── Deep Table Extraction (ALL tables from petition) ───────────────
    detailed_tables: Dict[str, Any]
    # Contains: tables_found, component_justifications, energy_data,
    # capital_structure, escalation_factors, loan_details, etc.

    # ── R&M Line Items (from Extractor, for AI classifier) ────────────
    rm_line_items: List[Dict[str, Any]]
    # Each dict: {"description": str, "amount": float}
    # Extracted from the R&M breakdown table in the petition

    rm_classification_result: Dict[str, Any]
    # Output from rm_classifier.process_rm_petition()
    # Keys: line_items, financial_summary, clarifications_to_send, total_approved_rm

    # ── Anomaly Detection (Gemini flags after extraction) ─────────────
    anomaly_flags: List[Dict[str, Any]]
    # Each dict: {"component": str, "severity": HIGH/MEDIUM/LOW,
    #             "flag": str, "suggested_action": str}

    # ── Clarification Items (for auto-generated query letter) ─────────
    clarification_items: List[Dict[str, Any]]
    # Merged from R&M classifier + anomaly detector
    # Each dict: {"source": str, "item": str, "amount": float, "query": str}

    # ── Order Quality Validation ───────────────────────────────────────
    order_validation_result: Dict[str, Any]
    # Output from order_validator.validate_drafted_order()
    # Keys: passed, issues, suggestions, confidence_score

    # ── Extra energy fields used in PPC audit ─────────────────────────
    energy_sales_lakh_units: float  # Energy sold (lakh units) from energy balance table

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

    # ── Interest & Finance Charges ────────────────────────────────────
    interest_finance_result: Dict[str, Any]
    # Full engine output: per-component results, totals, cross-verification
    interest_prior_year_data: Dict[str, Any]
    # 10 values loaded from Firestore for prior-year balances
    interest_cross_verification: List[Dict[str, Any]]
    # 6 cross-check results, each with: check_name, passed, detail

    # Rates — must be provided for the financial year being trued up
    sbi_eblr_rate: float              # SBI EBLR on April 1 (e.g. 0.0915)
    sbi_retail_td_rate: float         # SBI retail TD 1-year rate on April 1
    supply_code_sd_rate: float        # Kerala Electricity Supply Code SD rate

    # Cross-component routing
    notional_surplus_for_nti: float   # Component G output → feeds NTI calc
    ag_adjustment_for_bank_charges: float  # Reclassified bank charges → reduce A&G

    # File handling
    file_classifications: Dict[str, List[str]]
    # Maps PDF filename → list of classifications (multi-class)
    # e.g. {"annexure_b.pdf": ["KSERC_FORMATS", "AUDITED_ACCOUNTS"]}

    # Provisional tracking
    interest_is_provisional: bool     # True if ANY component is provisional
    interest_provisional_components: List[str]  # e.g. ["normative_loan", "working_capital"]

    # ── Final Output ───────────────────────────────────────────────────
    output_pdf_path: str
    clarification_pdf_path: Optional[str]  # Path to generated clarification letter PDF
