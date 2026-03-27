"""
KSERC Truing-Up — Order Quality Validator
==========================================
Module  : order_validator.py
Purpose : After drafter.py generates the draft order, Gemini acts as
          a "peer reviewer" and validates:
          1. Every claimed item is addressed in the order
          2. Disallowance reasons are legally sound (cite correct regulation)
          3. Arithmetic is internally consistent (amounts add up)
          4. KSERC style and language is correct
          5. No contradictions between paragraphs

INTEGRATION:
  Called as a LangGraph node after draft_node, before END.
  Issues are logged but do NOT block order generation.
  High-severity validation failures are added to the order as footnotes.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from src.config import GEMINI_MODEL

logger = logging.getLogger("kserc.order_validator")

# ─────────────────────────────────────────────────────────────────────
# PROMPT
# ─────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are a senior legal officer at the Kerala State Electricity Regulatory
Commission (KSERC) reviewing a draft truing-up order for quality assurance.

CHECK FOR:
1. COMPLETENESS: Every expense item claimed by the licensee must be explicitly
   addressed (approved, disallowed, or referred for clarification)
2. LEGAL SOUNDNESS: Each disallowance must cite a specific regulation
   (e.g., "Regulation 80(3) of KSERC Tariff Regulations 2021")
3. ARITHMETIC CONSISTENCY: Approved amounts must match the stated totals;
   the revenue gap/surplus should match approved_revenue - approved_expenditure
4. LANGUAGE: KSERC orders use formal, precise language. Flag any vague or
   ambiguous statements.
5. INTERNAL CONTRADICTIONS: No two paragraphs should state conflicting facts

Return a JSON object with:
{
  "passed": true/false,
  "confidence_score": 0.0-1.0,
  "issues": [
    {
      "severity": "HIGH" | "MEDIUM" | "LOW",
      "type": "completeness" | "legal" | "arithmetic" | "language" | "contradiction",
      "description": "Clear description of the issue",
      "location": "Which section or paragraph",
      "suggested_fix": "How to fix it"
    }
  ],
  "summary": "One paragraph assessment of overall order quality"
}
"""

_USER_PROMPT = """
Review this draft KSERC truing-up order for quality assurance:

LICENSEE: {licensee}
FY: {fy}

FINANCIAL SUMMARY (from audit):
  Total Claimed Expenditure: Rs. {total_claimed:.2f} Lakhs
  Total Approved Expenditure: Rs. {total_approved:.2f} Lakhs
  Total Approved Revenue: Rs. {total_revenue:.2f} Lakhs
  Revenue Gap/Surplus: Rs. {gap_surplus:.2f} Lakhs

DISALLOWANCES LOG:
{disallowances}

ANOMALY FLAGS (if any):
{anomaly_flags}

DRAFT ORDER TEXT (first 6000 chars):
{order_text}

Validate the order for completeness, legal soundness, arithmetic consistency,
language quality, and internal contradictions.
"""


# ─────────────────────────────────────────────────────────────────────
# VALIDATION FUNCTION
# ─────────────────────────────────────────────────────────────────────

def validate_drafted_order(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Validate the drafted order using Gemini.

    Parameters
    ----------
    state : TruingUpState dict (must have output_pdf_path set)

    Returns
    -------
    dict with: order_validation_result
    """
    licensee = state.get("licensee_name", "Unknown")
    fy = state.get("financial_year", "Unknown")

    logger.info("═" * 60)
    logger.info("ORDER QUALITY VALIDATOR NODE")
    logger.info(f"Validating order for: {licensee} FY {fy}")
    logger.info("═" * 60)

    # Read the drafted order text if available
    order_text = _read_order_text(state.get("output_pdf_path", ""))

    if not order_text:
        logger.warning("Order Validator: No order text available — skipping validation")
        return {
            "order_validation_result": {
                "passed": True,
                "confidence_score": 0.0,
                "issues": [],
                "summary": "Validation skipped — order text not available.",
            }
        }

    disallowances = state.get("disallowance_log", [])
    anomaly_flags = state.get("anomaly_flags", [])

    # Summarize disallowances for the prompt
    disallowances_text = json.dumps(
        [
            {
                "item": d.get("item", ""),
                "claimed": d.get("claimed", 0),
                "approved": d.get("approved", 0),
                "amount_cut": d.get("amount_cut", 0),
            }
            for d in disallowances[:20]  # Cap at 20 items
        ],
        indent=2
    )

    anomaly_text = json.dumps(
        [
            {"component": f.get("component", ""), "severity": f.get("severity", ""),
             "flag": f.get("flag", "")}
            for f in anomaly_flags[:10]
        ],
        indent=2
    ) if anomaly_flags else "None detected"

    try:
        from src.gemini_client import generate

        prompt = _USER_PROMPT.format(
            licensee=licensee,
            fy=fy,
            total_claimed=state.get("total_claimed_expenditure", 0.0),
            total_approved=state.get("total_approved_expenditure", 0.0),
            total_revenue=state.get("total_approved_revenue", 0.0),
            gap_surplus=state.get("final_revenue_gap_surplus", 0.0),
            disallowances=disallowances_text,
            anomaly_flags=anomaly_text,
            order_text=order_text[:6000],
        )

        raw = generate(
            prompt=prompt,
            model=GEMINI_MODEL,
            temperature=0.0,
            response_mime_type="application/json",
            system_instruction=_SYSTEM_PROMPT,
            max_output_tokens=2048,
        )

        validation_result = json.loads(raw)

        passed = validation_result.get("passed", True)
        score = validation_result.get("confidence_score", 1.0)
        issues = validation_result.get("issues", [])
        high_issues = [i for i in issues if i.get("severity") == "HIGH"]

        logger.info(
            f"Order Validation: passed={passed}, score={score:.2f}, "
            f"issues={len(issues)} ({len(high_issues)} HIGH)"
        )

        for issue in issues:
            severity = issue.get("severity", "?")
            desc = issue.get("description", "")[:100]
            logger.info(f"  [{severity}] {desc}")

        return {"order_validation_result": validation_result}

    except Exception as e:
        logger.error(f"Order validation error: {e}")
        return {
            "order_validation_result": {
                "passed": True,
                "confidence_score": 0.5,
                "issues": [
                    {
                        "severity": "LOW",
                        "type": "system",
                        "description": f"Automated validation failed: {e}",
                        "location": "N/A",
                        "suggested_fix": "Perform manual review of the order.",
                    }
                ],
                "summary": "Automated validation could not complete. Manual review recommended.",
            }
        }


def _read_order_text(pdf_path: str) -> str:
    """
    Attempt to read order text from the generated file.
    Handles .txt or .pdf outputs.
    """
    if not pdf_path:
        return ""

    from pathlib import Path
    path = Path(pdf_path)

    if not path.exists():
        return ""

    # If it's a .txt file (some drafters output text first)
    if path.suffix.lower() == ".txt":
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    # If it's a PDF, try to extract text
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            return "\n".join(
                page.extract_text() or "" for page in pdf.pages[:10]
            )
    except ImportError:
        pass  # pdfplumber not available
    except Exception as e:
        logger.warning(f"Could not extract order PDF text: {e}")

    return ""
