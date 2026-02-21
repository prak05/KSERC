# [Purpose] Pydantic data models for API request/response validation
# [Source] Based on KSERC regulatory orders (4oCC...pdf, 4tJU...pdf)
# [Why] Ensures type safety and automatic validation for all API interactions

# [Library] Pydantic - Data validation library using Python type hints
# [Source] https://docs.pydantic.dev/
# [Why] Provides automatic data validation, serialization, and documentation
from pydantic import BaseModel, Field, validator

# [Library] typing - Support for type hints
# [Why] Enables type checking and better IDE support
from typing import List, Optional, Dict, Any

# [Library] datetime - Date and time handling
# [Why] Used for timestamp fields in API responses
from datetime import datetime


# [User Defined] Model representing a single row in the 'Truing Up' financial table
# [Source] Based on Table 30 in KSERC Order '4oCC...pdf' (Infopark Truing Up)
# [Why] Represents individual line items in the financial statement
class FinancialRow(BaseModel):
    """
    [Purpose] Represents a single financial line item in a regulatory order
    [Source] Structure derived from KSERC Truing Up tables
    """
    
    # [Field] particulars - The name/description of the cost or revenue head
    # [Example] "Employee Expenses", "Power Purchase Cost", "Administrative Expenses"
    # [Why] Identifies what the financial row represents
    particulars: str = Field(
        ...,  # [Comment] ... means this field is required
        description="Name of the expense/revenue category",
        example="Power Purchase Cost"
    )
    
    # [Field] arr_approved - The value approved in the Annual Revenue Requirement (ARR)
    # [Source] ARR column from KSERC Truing Up tables
    # [Why] Baseline value for comparison against actual expenditure
    arr_approved: float = Field(
        ...,
        description="Amount approved in ARR (in Lakhs of Rupees)",
        example=3103.55
    )
    
    # [Field] trued_up_value - The actual value claimed/spent during the year
    # [Source] Trued Up/Actual column from KSERC tables
    # [Why] Represents the real expenditure to compare against ARR
    trued_up_value: float = Field(
        ...,
        description="Actual amount trued up (in Lakhs of Rupees)",
        example=3370.52
    )
    
    # [Field] deviation - Calculated difference between ARR and actual
    # [Why] Key metric for regulatory scrutiny (over/under spending)
    deviation: float = Field(
        ...,
        description="Deviation from ARR (Trued Up - ARR)",
        example=266.97
    )
    
    # [Pydantic Validator] Ensure deviation is correctly calculated
    # [Source] Pydantic validation feature
    # [Why] Data integrity - ensures deviation matches the formula
    @validator('deviation', always=True)
    def validate_deviation(cls, v, values):
        """
        [User Defined] Validates that deviation equals trued_up_value - arr_approved
        [Why] Prevents data inconsistency
        """
        # [Comment] Check if required fields exist in values dictionary
        if 'arr_approved' in values and 'trued_up_value' in values:
            # [Comment] Calculate expected deviation
            expected = values['trued_up_value'] - values['arr_approved']
            # [Comment] Allow small floating-point tolerance (0.01)
            if abs(v - expected) > 0.01:
                # [Library] Pydantic raises ValueError for validation failures
                raise ValueError(f"Deviation must equal trued_up_value - arr_approved")
        return v


# [User Defined] Main response model for the Truing Up analysis API endpoint
# [Source] Corresponds to the output structure needed for ARA Dashboard
# [Why] Provides complete analysis results in a structured format
class TruingUpResponse(BaseModel):
    """
    [Purpose] Complete response for regulatory order analysis
    [Source] Structure based on 'AI_Regulatory_Auditing...pdf' requirements
    """
    
    # [Field] licensee_name - Name of the electricity distribution licensee
    # [Example] "Infopark", "Technopark", "KDHPCL"
    # [Source] Extracted from PDF header (M/s [Name])
    licensee_name: str = Field(
        ...,
        description="Name of the licensee",
        example="Infopark"
    )
    
    # [Field] financial_year - The financial year being audited
    # [Format] "YYYY-YY" format as per KSERC convention
    # [Example] "2023-24"
    financial_year: str = Field(
        ...,
        description="Financial year of the truing up exercise",
        example="2023-24"
    )
    
    # [Field] financial_summary - List of all extracted financial rows
    # [Type] List of FinancialRow objects
    # [Why] Contains the complete financial breakdown
    financial_summary: List[FinancialRow] = Field(
        ...,
        description="List of financial line items with ARR vs Actuals"
    )
    
    # [Field] net_surplus_deficit - Overall surplus or deficit amount
    # [Source] Key metric from KSERC orders (Net Surplus/Deficit calculation)
    # [Why] Critical value for regulatory decision-making
    # [Sign Convention] Positive = Surplus, Negative = Deficit
    net_surplus_deficit: float = Field(
        ...,
        description="Net surplus (+) or deficit (-) in Lakhs of Rupees",
        example=-150.75
    )
    
    # [Field] total_arr_approved - Sum of all ARR approved values
    # [Why] Provides aggregate view of approved budget
    total_arr_approved: Optional[float] = Field(
        None,
        description="Total ARR approved amount"
    )
    
    # [Field] total_trued_up - Sum of all trued up actual values
    # [Why] Provides aggregate view of actual expenditure
    total_trued_up: Optional[float] = Field(
        None,
        description="Total trued up amount"
    )
    
    # [Field] analysis_timestamp - When the analysis was performed
    # [Why] Audit trail for when analysis was done
    analysis_timestamp: Optional[datetime] = Field(
        default_factory=datetime.now,  # [Library] datetime.now() for current time
        description="Timestamp of analysis"
    )
    
    # [Field] compliance_status - Overall compliance assessment
    # [Why] Quick summary of whether licensee is within acceptable limits
    compliance_status: Optional[str] = Field(
        None,
        description="Overall compliance status",
        example="Under Review"
    )


# [User Defined] Model for error responses
# [Source] Standard error response pattern for REST APIs
# [Why] Provides consistent error format for API consumers
class ErrorResponse(BaseModel):
    """
    [Purpose] Standardized error response format
    [Why] Consistent error handling across the API
    """
    
    # [Field] error - Error type or category
    error: str = Field(..., description="Error type", example="ValidationError")
    
    # [Field] message - Human-readable error message
    message: str = Field(..., description="Error description", example="Invalid PDF format")
    
    # [Field] details - Additional error details
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")


# [User Defined] Model for health check response
# [Source] Standard practice for API health monitoring
# [Why] Allows monitoring systems to check API status
class HealthCheckResponse(BaseModel):
    """
    [Purpose] Health check endpoint response
    [Why] Enables monitoring and load balancer health checks
    """
    
    # [Field] status - Service status indicator
    status: str = Field(..., description="Service status", example="active")
    
    # [Field] system - System name
    system: str = Field(..., description="System identifier", example="ARA Backend v1")
    
    # [Field] timestamp - Current server time
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Current server timestamp"
    )
    
    # [Field] version - API version
    version: str = Field(..., description="API version", example="1.0.0")


# [User Defined] Model for AI summary requests
# [Source] User defined for free-tier LLM integration
# [Why] Provides structured input for summary generation
class SummaryRequest(BaseModel):
    """
    [Purpose] Request payload for AI summary generation
    [Why] Combines analysis result with optional compliance report
    """
    analysis: TruingUpResponse = Field(
        ...,
        description="Full analysis result from /analyze-order/"
    )
    compliance_report: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional compliance report from /compliance-check/"
    )


# [User Defined] Model for AI summary responses
# [Source] User defined for LLM output normalization
# [Why] Provides consistent summary response for frontend
class SummaryResponse(BaseModel):
    """
    [Purpose] Response payload for AI summary generation
    [Why] Normalizes summary text and provider details
    """
    summary: str = Field(..., description="Generated summary text")
    provider: str = Field(..., description="Summary provider (local or API)")
    model: str = Field(..., description="Model name used for summary")
    warning: Optional[str] = Field(None, description="Warning if LLM was unavailable")


# [User Defined] RAG indexing response
# [Why] Provides status for indexing operation
class RagIndexResponse(BaseModel):
    status: str = Field(..., description="Indexing status")
    indexed_chunks: int = Field(..., description="Total chunks indexed")
    sources: List[str] = Field(..., description="List of sources indexed")


# [User Defined] Verdict response model
# [Why] Provides verdict summary and PDF link
class VerdictResponse(BaseModel):
    verdict_id: str = Field(..., description="Unique verdict ID")
    verdict_pdf_url: str = Field(..., description="URL to download verdict PDF")
    summary: str = Field(..., description="Executive summary")
    approved_items: List[str] = Field(default_factory=list, description="Approved expenses")
    disallowed_items: List[str] = Field(default_factory=list, description="Disallowed expenses")
    conditions: List[str] = Field(default_factory=list, description="Conditions/notes")
    agent_outputs: Dict[str, Any] = Field(..., description="Outputs from 4 agents")
    rag_snippets: List[Dict[str, Any]] = Field(..., description="RAG context snippets used")
