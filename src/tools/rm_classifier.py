"""
KSERC Truing-Up — R&M One-Time Expenditure Classification Engine
================================================================
Module  : rm_classifier.py
Basis   : KSERC Tariff Regulations 2021, Regulation 80(3)
Model   : Gemini via gemini_client.py (same pattern as rest of project)

WHY AI:
  Keyword matching fails on unknown descriptions.
  Gemini applies the ONE universal KSERC principle:
    "Does this expenditure CREATE a long-life asset (CAPITAL)?
     OR RESTORE existing functionality non-routinely (ONE_TIME_RM)?
     OR is it recurring/already in norm (ROUTINE_RM)?"

INTEGRATION POINTS:
  - Called by auditor._audit_repair_maintenance()
  - rm_line_items extracted by extractor.py into state
  - Results stored in state["rm_classification_result"]
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("kserc.rm_classifier")

# ─────────────────────────────────────────────────────────────────────
# SECTION 1: CLASSIFICATION PROMPT
# ─────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are a regulatory expert for Kerala State Electricity Regulatory
Commission (KSERC) in India. Your job is to classify Repair and
Maintenance (R&M) expenditure items claimed by electricity distribution
licensees in their truing-up petitions.

KSERC REGULATORY PRINCIPLE (Regulation 80, Tariff Regulations 2021):
Every R&M item must be classified into exactly ONE of these categories:

1. CAPITAL_EXPENDITURE
   - Physically replaces or creates a component with a long useful life
   - Becomes part of the fixed asset register
   - Should be recovered through depreciation, NOT a single year charge
   PRINCIPLE: After this work, a NEW physical component exists.

2. ONE_TIME_RM
   - A genuine one-time activity (not recurring)
   - Does not create any new long-life physical component
   - Restores or verifies existing assets to working condition
   - Could NOT have been anticipated when setting the annual norm
   PRINCIPLE: After this work, NOTHING NEW exists — existing asset works better.

3. ROUTINE_RM
   - Recurring maintenance activity that happens predictably
   - Already factored into the annual O&M norm
   - Normal upkeep of the distribution system
   PRINCIPLE: KSERC already accounts for this in the normative O&M cost.

4. NEEDS_CLARIFICATION
   - Description too vague to classify confidently
   - Licensee must provide more details before a decision can be made.

IMPORTANT RULES:
- Do NOT rely on specific component names
- Focus ONLY on the NATURE of the activity
- A "replacement" of a major component → almost always CAPITAL
- A "test", "service", "inspection", "charge", "cleaning" → almost always ONE_TIME_RM
- When in doubt between CAPITAL and ONE_TIME_RM, choose CAPITAL
  (safer to capitalise than allow as revenue expense)

Respond ONLY with a valid JSON object. No preamble. No explanation outside JSON.
"""

_USER_PROMPT = """
Classify this R&M expenditure item from a KSERC truing-up petition:

Description : {description}
Amount      : Rs. {amount} lakh
Licensee    : {licensee}

Return ONLY this JSON structure with no extra text:
{{
    "classification": "CAPITAL_EXPENDITURE" | "ONE_TIME_RM" | "ROUTINE_RM" | "NEEDS_CLARIFICATION",
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "reason": "One sentence explaining why this classification was chosen",
    "regulatory_treatment": "What KSERC should do with this item",
    "clarification_query": "Question to ask licensee if needed, else null"
}}
"""

# Human-readable flags for each classification
_FLAGS = {
    "CAPITAL_EXPENDITURE":   "⚠️  CAPITALISE — Verify asset addition with licensee",
    "ONE_TIME_RM":           "✅  ALLOW — Genuine one-time, verify invoice",
    "ROUTINE_RM":            "🔴  DISALLOW — Already covered in annual norm",
    "NEEDS_CLARIFICATION":   "🔴  SEND CLARIFICATION TO LICENSEE",
}


# ─────────────────────────────────────────────────────────────────────
# SECTION 2: CORE CLASSIFICATION FUNCTION
# ─────────────────────────────────────────────────────────────────────

def classify_rm_item(
    description: str,
    amount: float,
    licensee: str = "",
) -> Dict[str, Any]:
    """
    Classify a single R&M line item using Gemini.

    Works for ANY description from ANY licensee.
    No hardcoded components. No keywords. Pure AI reasoning.

    Parameters
    ----------
    description : str   - R&M item description from petition
    amount      : float - Amount in Rs. Lakh
    licensee    : str   - Licensee name (for context)

    Returns
    -------
    dict with: classification, confidence, reason, regulatory_treatment,
               clarification_query, flag, item, amount_claimed
    """
    import json
    try:
        from src.gemini_client import generate
    except ImportError:
        logger.error("gemini_client not available — using fallback")
        return _fallback_result(description, amount, "gemini_client import error")

    try:
        prompt = _USER_PROMPT.format(
            description=description,
            amount=round(amount, 2),
            licensee=licensee or "unknown",
        )

        raw = generate(
            prompt=prompt,
            model="gemini-2.5-pro",
            temperature=0.0,
            response_mime_type="application/json",
            system_instruction=_SYSTEM_PROMPT,
            max_output_tokens=512,
        )

        result = json.loads(raw)

        # Enrich with metadata
        result["item"] = description
        result["amount_claimed"] = amount
        result["flag"] = _FLAGS.get(result.get("classification", ""), "🔴 REVIEW REQUIRED")

        logger.info(
            f"R&M item classified: '{description[:50]}' → "
            f"{result['classification']} ({result['confidence']})"
        )
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error for item '{description}': {e}")
        return _fallback_result(description, amount, f"JSON parse error: {e}")
    except Exception as e:
        logger.error(f"Gemini error for item '{description}': {e}")
        return _fallback_result(description, amount, str(e))


def _fallback_result(description: str, amount: float, error: str) -> Dict[str, Any]:
    """Safe fallback when AI call fails — conservative approach."""
    return {
        "item": description,
        "amount_claimed": amount,
        "classification": "NEEDS_CLARIFICATION",
        "confidence": "LOW",
        "reason": f"AI classification failed: {error}",
        "regulatory_treatment": "Requires manual review by Commission staff.",
        "clarification_query": "Please provide detailed justification for this expense.",
        "flag": "🔴 AI ERROR — MANUAL REVIEW REQUIRED",
    }


# ─────────────────────────────────────────────────────────────────────
# SECTION 3: BATCH PROCESSING FOR FULL PETITION
# ─────────────────────────────────────────────────────────────────────

def process_rm_petition(
    licensee_name: str,
    financial_year: str,
    norm_rm: float,
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Process ALL one-time R&M items from a petition.
    Calls Gemini for each item and produces regulatory analysis.

    Parameters
    ----------
    licensee_name : str   - Name of the licensee
    financial_year : str  - e.g. "2024-25"
    norm_rm       : float - MYT-approved norm for R&M (after inflation escalation)
    items         : list  - [{"description": str, "amount": float}, ...]

    Returns
    -------
    dict with:
        line_items       : list of per-item classification results
        financial_summary: {norm_rm_approved, one_time_claimed, one_time_allowed,
                            to_be_capitalised, disallowed_routine, total_approved_rm}
        clarifications_to_send: list of items needing licensee clarification
        total_approved_rm: float — the number to use in approved_expenses
    """
    if not items:
        logger.info("R&M Classifier: no line items provided — using norm only")
        return _empty_result(licensee_name, financial_year, norm_rm)

    results: List[Dict[str, Any]] = []
    total_claimed    = 0.0
    total_allowed    = 0.0
    total_capitalised = 0.0
    total_disallowed = 0.0
    clarifications: List[Dict[str, Any]] = []

    logger.info(
        f"R&M Classifier: processing {len(items)} items for "
        f"{licensee_name} FY {financial_year}"
    )

    for item in items:
        desc   = item.get("description", "Unknown item")
        amount = float(item.get("amount", 0.0))

        result = classify_rm_item(desc, amount, licensee_name)
        results.append(result)
        total_claimed += amount

        classification = result.get("classification", "NEEDS_CLARIFICATION")

        if classification == "ONE_TIME_RM":
            total_allowed += amount
        elif classification == "CAPITAL_EXPENDITURE":
            total_capitalised += amount
        elif classification == "ROUTINE_RM":
            total_disallowed += amount
        # NEEDS_CLARIFICATION: no amount counted (conservative)

        if result.get("clarification_query"):
            clarifications.append({
                "item": desc,
                "amount": amount,
                "query": result["clarification_query"],
                "classification": classification,
            })

    # Final approved R&M = MYT norm + allowed one-time items
    total_approved_rm = round(norm_rm + total_allowed, 2)

    output = {
        "licensee": licensee_name,
        "financial_year": financial_year,
        "line_items": results,
        "financial_summary": {
            "norm_rm_approved":   round(norm_rm, 2),
            "one_time_claimed":   round(total_claimed, 2),
            "one_time_allowed":   round(total_allowed, 2),
            "to_be_capitalised":  round(total_capitalised, 2),
            "disallowed_routine": round(total_disallowed, 2),
            "total_approved_rm":  total_approved_rm,
        },
        "clarifications_to_send": clarifications,
        "total_approved_rm": total_approved_rm,
    }

    logger.info(
        f"R&M Classifier complete: norm={norm_rm:.2f}L + "
        f"one_time_allowed={total_allowed:.2f}L = "
        f"total_approved={total_approved_rm:.2f}L | "
        f"capitalised={total_capitalised:.2f}L | "
        f"disallowed={total_disallowed:.2f}L"
    )

    return output


def _empty_result(
    licensee_name: str, financial_year: str, norm_rm: float
) -> Dict[str, Any]:
    """Return a no-items result — approved = norm only."""
    return {
        "licensee": licensee_name,
        "financial_year": financial_year,
        "line_items": [],
        "financial_summary": {
            "norm_rm_approved":   round(norm_rm, 2),
            "one_time_claimed":   0.0,
            "one_time_allowed":   0.0,
            "to_be_capitalised":  0.0,
            "disallowed_routine": 0.0,
            "total_approved_rm":  round(norm_rm, 2),
        },
        "clarifications_to_send": [],
        "total_approved_rm": round(norm_rm, 2),
    }
