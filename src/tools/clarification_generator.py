"""
KSERC Truing-Up — Clarification Letter Generator
==================================================
Module  : clarification_generator.py
Purpose : Automatically drafts KSERC-style query letters to licensees
          when items need clarification. Merges inputs from:
          - R&M classifier (items needing clarification)
          - Anomaly detector (HIGH severity flags)

OUTPUT:  A formatted clarification letter as plain text (to be converted
         to PDF by drafter.py or output as a standalone document).

KSERC STYLE:
  Formal, numbered queries. Clear reference to petition details.
  Specifies the regulatory basis for each query.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.config import GEMINI_MODEL

logger = logging.getLogger("kserc.clarification_generator")

# ─────────────────────────────────────────────────────────────────────
# PROMPT
# ─────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are a drafting officer at the Kerala State Electricity Regulatory
Commission (KSERC). You write formal query letters to electricity licensees
asking them to clarify or justify specific items in their truing-up petitions.

STYLE REQUIREMENTS:
- Formal, professional KSERC letter style
- Numbered queries, each clearly stating what information is required
- Reference the specific petition and financial year
- Cite the relevant KSERC regulation where applicable
- Neutral tone — do not pre-judge the licensee
- Each query should be self-contained and unambiguous

Output a professional letter in plain text format (not JSON).
Include placeholders like [DATE], [PETITION NUMBER], [LETTER NUMBER] 
that will be filled in later.
"""

_USER_PROMPT = """
Draft a clarification query letter for:

Licensee          : {licensee}
Financial Year    : {financial_year}
Petition Number   : {petition_number}

THE FOLLOWING ITEMS REQUIRE CLARIFICATION:
{items_text}

Write a complete, formal KSERC query letter requesting clarification
on the above items. Number each query. Be specific about what 
documentation or justification is required for each item.
"""


# ─────────────────────────────────────────────────────────────────────
# MAIN GENERATION FUNCTION
# ─────────────────────────────────────────────────────────────────────

def generate_clarification_letter(
    licensee_name: str,
    financial_year: str,
    petition_number: str,
    clarification_items: List[Dict[str, Any]],
) -> Optional[str]:
    """
    Generate a KSERC-style clarification letter using Gemini.

    Parameters
    ----------
    licensee_name       : str  - Name of the licensee
    financial_year      : str  - e.g. "2024-25"
    petition_number     : str  - e.g. "OP 84/2023"
    clarification_items : list - Each dict: {"source", "item", "amount", "query"}

    Returns
    -------
    str : The complete letter text, or None if generation failed
    """
    if not clarification_items:
        logger.info("Clarification Generator: no items — skipping letter generation")
        return None

    # Format items as numbered list for the prompt
    items_text_parts = []
    for i, item in enumerate(clarification_items, 1):
        source = item.get("source", "unknown")
        comp   = item.get("item", "Unknown item")
        amount = item.get("amount", 0.0)
        query  = item.get("query", "Please clarify this item.")

        if amount > 0:
            items_text_parts.append(
                f"{i}. [{source.upper()}] Component: {comp} (Rs. {amount:.2f} Lakhs)\n"
                f"   Issue: {query}"
            )
        else:
            items_text_parts.append(
                f"{i}. [{source.upper()}] Component: {comp}\n"
                f"   Issue: {query}"
            )

    items_text = "\n\n".join(items_text_parts)

    logger.info(
        f"Clarification Generator: drafting letter for {licensee_name} FY {financial_year} "
        f"with {len(clarification_items)} queries"
    )

    try:
        from src.gemini_client import generate

        prompt = _USER_PROMPT.format(
            licensee=licensee_name,
            financial_year=financial_year,
            petition_number=petition_number or "Petition under reference",
            items_text=items_text,
        )

        letter_text = generate(
            prompt=prompt,
            model=GEMINI_MODEL,
            temperature=0.3,  # slight creativity for natural letter writing
            response_mime_type="text/plain",
            system_instruction=_SYSTEM_PROMPT,
            max_output_tokens=4096,
        )

        # Replace date placeholder with actual date
        letter_text = letter_text.replace(
            "[DATE]", date.today().strftime("%d %B %Y")
        )

        logger.info(
            f"Clarification letter generated: {len(letter_text)} characters, "
            f"{len(clarification_items)} queries"
        )
        return letter_text

    except Exception as e:
        logger.error(f"Clarification letter generation error: {e}")
        return _fallback_letter(
            licensee_name, financial_year, petition_number, clarification_items
        )


def _fallback_letter(
    licensee_name: str,
    financial_year: str,
    petition_number: str,
    items: List[Dict[str, Any]],
) -> str:
    """Simple template-based fallback when Gemini is unavailable."""
    lines = [
        f"KERALA STATE ELECTRICITY REGULATORY COMMISSION",
        f"",
        f"Letter No: [LETTER NUMBER]",
        f"Date: {date.today().strftime('%d %B %Y')}",
        f"",
        f"To,",
        f"The Engineer / Officer-in-Charge,",
        f"{licensee_name}",
        f"",
        f"Sub: Truing Up Petition for FY {financial_year} — "
        f"Request for Clarification",
        f"Ref: {petition_number or 'Petition under reference'}",
        f"",
        f"Dear Sir/Madam,",
        f"",
        f"With reference to the above truing-up petition, the Commission "
        f"requires the following clarifications / additional information "
        f"before proceeding with the audit:",
        f"",
    ]
    for i, item in enumerate(items, 1):
        comp = item.get("item", "Unknown")
        query = item.get("query", "Please clarify.")
        amount = item.get("amount", 0.0)
        amt_str = f" (Claimed: Rs. {amount:.2f} Lakhs)" if amount > 0 else ""
        lines.append(f"Query {i}: {comp}{amt_str}")
        lines.append(f"  {query}")
        lines.append("")

    lines += [
        "Please provide the above information along with supporting documentation",
        "within 15 days of receipt of this letter.",
        "",
        "Yours faithfully,",
        "",
        "[SECRETARY / DESIGNATED OFFICER]",
        "Kerala State Electricity Regulatory Commission",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# STATE NODE WRAPPER
# ─────────────────────────────────────────────────────────────────────

def clarification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Generate clarification letter if items exist.
    Merges clarification_items from R&M classifier and anomaly detector.

    Returns updated state with clarification_pdf_path set.
    """
    licensee = state.get("licensee_name", "Unknown")
    fy = state.get("financial_year", "Unknown")

    logger.info("═" * 60)
    logger.info("CLARIFICATION LETTER NODE")
    logger.info("═" * 60)

    # Collect from all sources
    clarification_items: List[Dict[str, Any]] = list(
        state.get("clarification_items", [])
    )

    # Also add R&M classifier items
    rm_result = state.get("rm_classification_result", {})
    for item in rm_result.get("clarifications_to_send", []):
        clarification_items.append({
            "source": "rm_classifier",
            "item": item.get("item", ""),
            "amount": item.get("amount", 0.0),
            "query": item.get("query", ""),
        })

    if not clarification_items:
        logger.info("No clarification items — skipping letter generation")
        return {"clarification_items": [], "clarification_pdf_path": None}

    petition_number = state.get("petition_number", "")
    letter_text = generate_clarification_letter(
        licensee_name=licensee,
        financial_year=fy,
        petition_number=petition_number,
        clarification_items=clarification_items,
    )

    # Save letter to file
    clarification_pdf_path: Optional[str] = None
    if letter_text:
        output_dir = Path("output_orders")
        output_dir.mkdir(exist_ok=True)
        letter_filename = output_dir / f"{licensee}_{fy}_clarification_queries.txt"
        letter_filename.write_text(letter_text, encoding="utf-8")
        clarification_pdf_path = str(letter_filename)
        logger.info(f"Clarification letter saved: {clarification_pdf_path}")

    return {
        "clarification_items": clarification_items,
        "clarification_pdf_path": clarification_pdf_path,
    }
