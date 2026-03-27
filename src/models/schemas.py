"""
KSERC Truing-Up — Pydantic Schemas for Structured Gemini Output.

These schemas enforce correct JSON output from Gemini by using
the `response_schema` parameter in google-genai's generate_content.
This eliminates manual JSON parsing failures and ensures type safety.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ═══════════════════════════════════════════════════════════════════
# Extraction Schemas (used by extractor.py / Gemini Vision)
# ═══════════════════════════════════════════════════════════════════

class ClaimedExpenses(BaseModel):
    """ARR expense line items — all values in Rs. Lakhs."""
    power_purchase_cost: float = Field(0.0, description="Cost of Power Purchase")
    employee_cost: float = Field(0.0, description="Employee Cost / Expenses")
    repair_maintenance: float = Field(0.0, description="Repairs & Maintenance")
    admin_general: float = Field(0.0, description="Administration & General (gross, excl. elec duty)")
    depreciation: float = Field(0.0, description="Depreciation")
    interest_long_term: float = Field(0.0, description="Interest on Long Term Loans / Finance Charges")
    interest_consumer_deposits: float = Field(0.0, description="Interest on Consumer Security Deposits")
    interest_working_capital: float = Field(0.0, description="Interest on Working Capital")
    carrying_cost: float = Field(0.0, description="Carrying cost for past revenue gaps")
    return_on_nfa: float = Field(0.0, description="Return on Net Fixed Assets / Equity")
    other_debits: float = Field(0.0, description="Other Debits / Duty-III")
    section3_1_duty: float = Field(0.0, description="Section 3(1) Kerala Electricity Duty")
    other_expenses: float = Field(0.0, description="Other miscellaneous expenses")


class ClaimedRevenues(BaseModel):
    """ARR revenue line items — all values in Rs. Lakhs."""
    revenue_from_sale: float = Field(0.0, description="Revenue from sale of power")
    wheeling_charges: float = Field(0.0, description="Wheeling charges received")
    non_tariff_income: float = Field(0.0, description="Non-tariff income")
    other_revenue: float = Field(0.0, description="Other income / revenue")


class ExtractionResult(BaseModel):
    """Complete extraction result from Gemini Vision or Document AI."""
    claimed_expenses: ClaimedExpenses
    claimed_revenues: ClaimedRevenues
    total_expenditure: float = Field(0.0, description="Sum of all expenses")
    total_revenue: float = Field(0.0, description="Sum of all revenues")
    distribution_loss_pct: float = Field(0.0, description="Distribution loss percentage")
    bee_energy_audit_fee: float = Field(0.0, description="BEE energy audit fee (A&G sub-item)")
    # Distribution loss unit values (in Lakh units = lakh kWh) — used for PPC Reg 73(3) calc
    actual_loss_lakh_units: float = Field(0.0, description="Actual distribution loss in Lakh units (lakh kWh) from petition energy balance table")
    approved_loss_lakh_units: float = Field(0.0, description="Approved/target distribution loss in Lakh units (lakh kWh) from petition table (ignore — re-computed from MYT norms)")
    energy_input_lakh_units: float = Field(0.0, description="Energy Input to Distribution System in Lakh units (lakh kWh). Look for row labeled 'Energy Received at State boundary (MU)' in PPC table (Form D 3.1) or 'Energy Input to Distribution System' in Annexure B / energy balance table. If value is in MU (Million Units), multiply by 10 to get Lakh units. This is the energy entering the distribution network, NOT 'Total Energy Purchased'.")
    energy_sales_lakh_units: float = Field(0.0, description="Total energy output / energy sold / energy delivered to consumers in Lakh units (lakh kWh). Look for rows labeled 'Total Energy Output', 'Energy Sold', 'Energy Delivered to Consumers', 'Energy Sales', 'Total Output'. This equals Energy Input minus Distribution Loss.")
    appc_rs_per_unit: float = Field(0.0, description="Average Power Purchase Cost in Rs/unit (Rs/kWh) from petition table")
    ppc_net_charges_rs_lakhs: float = Field(0.0, description="KDHP-specific: Net Charges (Rs/Lakhs) from the detailed Power Purchase Cost sub-table — this is the BOLD 'Net Charges-Rs/Lakhs' row after deducting excess line loss adjustment. Use this for power_purchase_cost for KDHP. If no adjustment, equals Total Charges.")
    # IWC sub-components
    consumer_security_deposit_balance: float = Field(0.0, description="Consumer security deposit balance (Rs Lakhs) from IWC table")
    maintenance_spares_wc: float = Field(0.0, description="Maintenance spares as per norms (Rs Lakhs)")
    # RoNFA computation fields
    ronfa_gross_fixed_assets: float = Field(0.0, description="Gross Fixed Assets at start of year (Rs Lakhs)")
    ronfa_accumulated_depreciation: float = Field(0.0, description="Total accumulated depreciation (Rs Lakhs)")
    ronfa_consumer_contribution: float = Field(0.0, description="Consumer contribution to assets (Rs Lakhs)")
    ronfa_nfa_for_normative_loan: float = Field(0.0, description="NFA for which interest is allowed / normative loan NFA (Rs Lakhs)")
    ronfa_prior_year_additions: float = Field(0.0, description="Asset additions from prior year excluded from NFA base (Rs Lakhs)")
    ronfa_balance_nfa: float = Field(0.0, description="Balance/eligible NFA after all deductions (Rs Lakhs)")
    ronfa_rate_pct: float = Field(0.0, description="Rate of return as percentage (e.g. 5.50 for 5.5%)")
    ronfa_eligible_return: float = Field(0.0, description="Computed eligible return / RoNFA claimed (Rs Lakhs)")



# ═══════════════════════════════════════════════════════════════════
# Auditor Schemas (used by chief_auditor.py)
# ═══════════════════════════════════════════════════════════════════

class AuditorDecision(BaseModel):
    """Chief Auditor's decision for a single component."""
    approved_amount: float = Field(description="Approved amount in Rs. Lakhs")
    justification: str = Field(description="Legal justification with regulation citations")


# ═══════════════════════════════════════════════════════════════════
# Analyzer Schemas (used by analyzer.py)
# ═══════════════════════════════════════════════════════════════════

class AnalysisResult(BaseModel):
    """Analysis result for a component comparison."""
    component: str = Field(description="Name of the financial component")
    claimed: float = Field(description="Claimed amount in Rs. Lakhs")
    approved: float = Field(description="Approved/calculated amount in Rs. Lakhs")
    variance: float = Field(description="Difference (approved - claimed)")
    variance_pct: float = Field(0.0, description="Variance as percentage")
    reasoning: str = Field("", description="Explanation of the variance")
    status: str = Field("", description="APPROVED / PARTIALLY_APPROVED / REJECTED")


# ═══════════════════════════════════════════════════════════════════
# Interest & Finance Extraction Schemas (flexible row-based)
# ═══════════════════════════════════════════════════════════════════

from typing import List
from enum import Enum


class FileClass(str, Enum):
    """Document classification types for uploaded petition files."""
    NARRATIVE_PETITION = "NARRATIVE_PETITION"
    KSERC_FORMATS = "KSERC_FORMATS"
    AUDITED_ACCOUNTS = "AUDITED_ACCOUNTS"
    AUDITOR_REPORT = "AUDITOR_REPORT"
    PREVIOUS_ORDER = "PREVIOUS_ORDER"
    HEARING_PROCEEDINGS = "HEARING_PROCEEDINGS"
    SCANNED_PDF = "SCANNED_PDF"


class InterestTableRow(BaseModel):
    """A single row from an interest-related table in a petition.

    Role-based identification: we detect rows by their CONTENT
    (e.g. label contains 'opening' or 'addition'), not by position.
    This handles different licensee table formats.
    """
    role: str = Field(
        description="Semantic role: opening, addition, repayment, closing, "
        "interest_rate, interest_amount, total, subtotal, or raw"
    )
    label: str = Field(description="Original text label from table")
    value: Optional[float] = Field(None, description="Numeric value in Rs Lakhs")
    note: Optional[str] = Field(None, description="Any footnote or qualification")


class InterestTableExtraction(BaseModel):
    """Flexible extraction of a single interest component table.

    Component can be: normative_loan, working_capital, security_deposit,
    bank_charges, carrying_cost, actual_loan, or interest_summary.
    """
    component: str = Field(description="Which interest component this table relates to")
    source_file: str = Field(description="Filename this was extracted from")
    source_page: int = Field(0, description="Page number within the file")
    rows_found: List[InterestTableRow] = Field(default_factory=list)
    total_claimed: Optional[float] = Field(None, description="Total claimed for this component")
    extraction_method: str = Field(
        "gemini", description="gemini | vision_api — how the table was read"
    )
    confidence: float = Field(1.0, description="0.0–1.0 extraction confidence")


class InterestSummaryExtraction(BaseModel):
    """Extraction result from the interest summary table (Pass 2).

    This is the high-level table showing all interest components in one view.
    """
    interest_on_long_term_loans: Optional[float] = None
    interest_on_normative_loan: Optional[float] = None
    interest_on_working_capital: Optional[float] = None
    interest_on_security_deposits: Optional[float] = None
    bank_charges: Optional[float] = None
    carrying_cost: Optional[float] = None
    total_interest_and_finance: Optional[float] = None
    source_file: str = ""
    source_page: int = 0
