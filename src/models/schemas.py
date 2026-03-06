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
