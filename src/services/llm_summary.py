# [Purpose] AI summary generation service using a free-tier API
# [Source] User defined integration with Hugging Face Inference API
# [Why] Provides optional natural-language summaries without paid APIs

# [Library] typing - Type hints for clarity
# [Why] Enables IDE support and explicit return types
from typing import Dict, Any, Optional

# [Library] httpx - HTTP client for API calls
# [Why] Lightweight async-capable HTTP client
import httpx

# [User Defined] Import configuration settings
# [Source] src/config.py
# [Why] Access API token, model, and timeout
from src.config import settings

# [User Defined] Import logger
# [Source] src/utils/logger.py
# [Why] Logs summary generation status
from src.utils.logger import get_logger

# [User Defined] Get logger instance
logger = get_logger(__name__)


# [User Defined] Build a prompt from analysis data
# [Source] User defined prompt template
# [Why] Keeps LLM input consistent and focused
def build_summary_prompt(
    analysis: Dict[str, Any],
    compliance_report: Optional[Dict[str, Any]] = None
) -> str:
    """
    [Purpose] Builds a summary prompt for the LLM
    [Why] Ensures the LLM receives concise, structured input
    """
    licensee = analysis.get("licensee_name", "Unknown")
    financial_year = analysis.get("financial_year", "Unknown")
    net = analysis.get("net_surplus_deficit", 0.0)
    total_arr = analysis.get("total_arr_approved", 0.0)
    total_trued = analysis.get("total_trued_up", 0.0)
    items = analysis.get("financial_summary", [])
    item_count = len(items) if isinstance(items, list) else 0

    compliance_status = "UNKNOWN"
    warnings_count = 0
    if isinstance(compliance_report, dict):
        compliance_status = compliance_report.get("overall_status", "UNKNOWN")
        warnings = compliance_report.get("warnings", [])
        warnings_count = len(warnings) if isinstance(warnings, list) else 0

    prompt = (
        "You are an energy regulatory analyst. "
        "Write a concise executive summary (5-7 sentences) for a truing-up analysis. "
        "Be precise, avoid fluff, and highlight key deviations and compliance risks.\n\n"
        f"Licensee: {licensee}\n"
        f"Financial Year: {financial_year}\n"
        f"Total ARR Approved (Lakhs): {total_arr}\n"
        f"Total Trued Up (Lakhs): {total_trued}\n"
        f"Net Surplus/Deficit (Lakhs): {net}\n"
        f"Total Line Items: {item_count}\n"
        f"Compliance Status: {compliance_status}\n"
        f"Warnings Count: {warnings_count}\n"
        "Return only the summary text."
    )
    return prompt


# [User Defined] Local fallback summary when LLM is unavailable
# [Source] User defined rule-based summary
# [Why] Guarantees response even without API access
def build_local_summary(
    analysis: Dict[str, Any],
    compliance_report: Optional[Dict[str, Any]] = None
) -> str:
    """
    [Purpose] Creates a deterministic summary without external APIs
    [Why] Ensures the endpoint always returns a usable response
    """
    licensee = analysis.get("licensee_name", "Unknown")
    financial_year = analysis.get("financial_year", "Unknown")
    net = analysis.get("net_surplus_deficit", 0.0)
    total_arr = analysis.get("total_arr_approved", 0.0)
    total_trued = analysis.get("total_trued_up", 0.0)
    items = analysis.get("financial_summary", [])
    item_count = len(items) if isinstance(items, list) else 0

    compliance_status = "UNKNOWN"
    warnings_count = 0
    if isinstance(compliance_report, dict):
        compliance_status = compliance_report.get("overall_status", "UNKNOWN")
        warnings = compliance_report.get("warnings", [])
        warnings_count = len(warnings) if isinstance(warnings, list) else 0

    return (
        f"Analysis for {licensee} ({financial_year}) processed {item_count} line items. "
        f"Total ARR approved is ₹{total_arr:.2f} Lakhs and total trued-up is ₹{total_trued:.2f} Lakhs. "
        f"The net surplus/deficit is ₹{net:.2f} Lakhs. "
        f"Compliance status is {compliance_status} with {warnings_count} warning(s). "
        "Review significant deviations for regulatory follow-up."
    )


# [User Defined] Generate summary via Hugging Face Inference API (free tier)
# [Source] User defined integration
# [Why] Provides AI-enhanced executive summary
def generate_summary(
    analysis: Dict[str, Any],
    compliance_report: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    [Purpose] Generates a summary using Hugging Face Inference API
    [Why] Free-tier API provides LLM output with minimal setup
    """
    prompt = build_summary_prompt(analysis, compliance_report)

    if not settings.HF_API_TOKEN or not settings.HF_API_MODEL:
        logger.warning("HF_API_TOKEN or HF_API_MODEL not set. Falling back to local summary.")
        return {
            "summary": build_local_summary(analysis, compliance_report),
            "provider": "local",
            "model": "rule-based",
            "warning": "HF_API_TOKEN or HF_API_MODEL not set; using local summary."
        }

    headers = {
        "Authorization": f"Bearer {settings.HF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": settings.HF_API_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 220
    }

    try:
        logger.info("Requesting summary from Hugging Face Inference API")
        response = httpx.post(
            settings.HF_API_URL,
            headers=headers,
            json=payload,
            timeout=settings.LLM_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()

        summary_text = ""
        if isinstance(data, dict):
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                summary_text = message.get("content", "")

        if not summary_text:
            logger.warning("Empty LLM response. Using local summary.")
            return {
                "summary": build_local_summary(analysis, compliance_report),
                "provider": "local",
                "model": "rule-based",
                "warning": "LLM returned empty output; using local summary."
            }

        return {
            "summary": summary_text.strip(),
            "provider": "huggingface",
            "model": settings.HF_API_MODEL
        }

    except Exception as e:
        logger.error(f"LLM summary failed: {str(e)}", exc_info=True)
        return {
            "summary": build_local_summary(analysis, compliance_report),
            "provider": "local",
            "model": "rule-based",
            "warning": "LLM request failed; using local summary."
        }
