"""
Deep AI Analyzer Agent — The AI KSERC Commission
===================================================
Uses Gemini with Google Search Grounding to act as the KSERC Commission.

This agent doesn't just find grants — it makes the ACTUAL auditing decisions
for every expense component, just like the real Commission would:

1. Reads the full petition PDF text
2. Loads KSERC regulations and MYT baselines
3. Searches the web for current WPI/CPI inflation data
4. Searches for grants, subsidies, interim relief orders
5. Makes per-component approve/reduce/disallow decisions
6. Provides KSERC-style justifications for every decision
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List
from src.config import GEMINI_MODEL

logger = logging.getLogger("kserc.analyzer")

# ═══════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parents[2]
REGULATIONS_PATH = BASE_DIR / "data" / "regulations" / "regulation_clauses.json"
MYT_BASELINES_PATH = BASE_DIR / "data" / "myt_baselines" / "myt_baselines.json"


# ═══════════════════════════════════════════════════════════════════════
# Load Local Knowledge Base
# ═══════════════════════════════════════════════════════════════════════

def _load_knowledge_base() -> str:
    """Load all local knowledge base documents into a single text block."""
    sections: List[str] = []

    # 1. KSERC Regulation Clauses
    if REGULATIONS_PATH.exists():
        try:
            data = json.loads(REGULATIONS_PATH.read_text(encoding="utf-8"))
            sections.append("=== KSERC TARIFF REGULATIONS (Key Clauses) ===")
            for clause_id, clause in data.items():
                sections.append(
                    f"Clause {clause.get('clause_number', clause_id)}: "
                    f"{clause.get('title', '')}\n"
                    f"{clause.get('text_snippet', '')}\n"
                )
        except Exception as e:
            logger.warning(f"Could not load regulations: {e}")

    # 2. MYT Baselines (approved norms)
    if MYT_BASELINES_PATH.exists():
        try:
            data = json.loads(MYT_BASELINES_PATH.read_text(encoding="utf-8"))
            sections.append("=== MYT APPROVED BASELINES (All Licensees) ===")
            for licensee, info in data.items():
                sections.append(f"\n--- {licensee} (MYT Order: {info.get('myt_order', 'N/A')}) ---")
                for fy, norms in info.get("baselines", {}).items():
                    sections.append(f"  FY {fy}:")
                    for key, val in norms.items():
                        sections.append(f"    {key}: {val}")
        except Exception as e:
            logger.warning(f"Could not load MYT baselines: {e}")

    return "\n".join(sections)


# ═══════════════════════════════════════════════════════════════════════
# Extract Full PDF Text
# ═══════════════════════════════════════════════════════════════════════

def _extract_full_pdf_text(pdf_path: str, max_pages: int = 40) -> str:
    """Extract full text from a PDF using PyMuPDF."""
    try:
        import fitz
    except ImportError:
        logger.warning("PyMuPDF not installed; cannot extract full text.")
        return ""

    doc = fitz.open(pdf_path)
    pages_text: List[str] = []
    total = min(len(doc), max_pages)

    for i in range(total):
        page = doc[i]
        text = page.get_text("text")
        if text.strip():
            pages_text.append(f"--- Page {i+1} ---\n{text}")

    doc.close()
    full_text = "\n\n".join(pages_text)
    logger.info(f"Extracted {len(pages_text)} pages of text ({len(full_text)} chars)")
    return full_text


# ═══════════════════════════════════════════════════════════════════════
# The AI Commission Prompt
# ═══════════════════════════════════════════════════════════════════════

ANALYZER_PROMPT = """You are acting as the KSERC (Kerala State Electricity Regulatory Commission) itself.
You must decide the APPROVED amount for every expense component in a Truing-Up Petition.

You have been given:
1. The FULL TEXT of the truing-up petition submitted by a Small Distribution Licensee (SDL).
2. The KSERC Tariff Regulations 2021 (key clauses).
3. The MYT Approved Baseline norms for all licensees.

YOUR ROLE:
You are NOT just checking numbers against norms. You are the Commission. You must make
NUANCED decisions exactly like the real KSERC does in their truing-up orders. This means:

DECISION-MAKING RULES:
1. O&M EXPENSES (Employee, R&M, A&G):
   - The MYT norms use a 4.454% escalation rate (70:30 CPI:WPI weighted average).
   - At truing-up, the Commission uses ACTUAL inflation for the year (not the estimated 4.454%).
   - SEARCH THE WEB for actual CPI and WPI inflation rates for India for the relevant financial year.
   - Compute inflation-adjusted norm = Base Year O&M × (1 + actual_weighted_inflation)^years
   - If claimed <= inflation-adjusted norm: APPROVE AS CLAIMED.
   - If claimed > inflation-adjusted norm but the petition provides valid justification
     (statutory wage revisions, court orders, force majeure): MAY APPROVE ABOVE NORM.
   - If claimed > inflation-adjusted norm with no justification: CAP AT INFLATION-ADJUSTED NORM.
   - If claimed < MYT norm: APPROVE AS CLAIMED (actual cost, not the norm).

2. POWER PURCHASE COST:
   - This is an UNCONTROLLABLE factor — should generally be approved as claimed.
   - BUT: apply the distribution loss penalty/gain formula:
     If actual dist. loss > target: penalty = excess_loss_lakh_kwh × avg_cost
     If actual dist. loss < target: gain shared 2:1 (licensee:consumer)

3. DEPRECIATION:
   - Normally capped at MYT norm.
   - BUT: Depreciation shall NOT be allowed on assets created through grants,
     consumer contributions, or capital subsidies (Regulation Clause 27).
   - SEARCH THE WEB for any grants this licensee may have received.

4. RETURN ON NET FIXED ASSETS (RoNFA):
   - Rate: 5.50% on eligible net fixed assets.
   - Same grant exclusion as depreciation applies.
   - If actual NFA is lower than projected, approve at actual.

5. INTEREST ON LOANS:
   - Approve at actual or normative rate, whichever is lower.
   - Check if the licensee has refinanced at lower rates.

6. CARRYING COST:
   - This is the carrying cost on past revenue gaps already approved.
   - Generally approved as claimed if consistent with prior orders.

7. SECTION 3(1) DUTY:
   - ALWAYS DISALLOW. KSERC has consistently rejected this in all previous orders.

8. INTERIM RELIEF:
   - Search for any interim relief orders granted to this licensee.
   - If interim relief was given, it should be adjusted in the final truing-up.

9. OTHER CONSIDERATIONS:
   - Look for any special circumstances mentioned in the petition.
   - Consider the financial health of the licensee.
   - Check if any regulatory changes affect the current year.

OUTPUT FORMAT (strict JSON):
{
  "approved_expenses": {
    "power_purchase_cost": {"amount": <float>, "justification": "<string>"},
    "employee_cost": {"amount": <float>, "justification": "<string>"},
    "repair_maintenance": {"amount": <float>, "justification": "<string>"},
    "admin_general": {"amount": <float>, "justification": "<string>"},
    "depreciation": {"amount": <float>, "justification": "<string>"},
    "interest_long_term": {"amount": <float>, "justification": "<string>"},
    "interest_consumer_deposits": {"amount": <float>, "justification": "<string>"},
    "interest_working_capital": {"amount": <float>, "justification": "<string>"},
    "carrying_cost": {"amount": <float>, "justification": "<string>"},
    "return_on_nfa": {"amount": <float>, "justification": "<string>"},
    "other_debits": {"amount": <float>, "justification": "<string>"},
    "other_expenses": {"amount": <float>, "justification": "<string>"},
    "section3_duty": {"amount": <float>, "justification": "<string>"}
  },

  "inflation_data": {
    "cpi_rate_pct": <float>,
    "wpi_rate_pct": <float>,
    "weighted_rate_pct": <float>,
    "source": "<string: URL or source of inflation data>"
  },

  "grants_discovered": {
    "found": <boolean>,
    "total_lakhs": <float>,
    "details": "<string>"
  },

  "interim_relief": {
    "found": <boolean>,
    "amount_lakhs": <float>,
    "details": "<string>"
  },

  "overall_assessment": "<string: 3-5 sentence Commission-style summary>"
}

IMPORTANT:
- Return ONLY valid JSON. No markdown fences, no explanation outside the JSON.
- Every justification must be detailed, citing specific regulation clauses, page numbers
  from the petition, or web sources.
- Be thorough but fair — you are the Commission, not a cost-cutter.
- If you cannot find specific data, make a reasonable decision and note the uncertainty.
"""


# ═══════════════════════════════════════════════════════════════════════
# Main Analyzer Function
# ═══════════════════════════════════════════════════════════════════════

def analyze_petition_deep(
    pdf_path: str,
    licensee_name: str,
    financial_year: str,
) -> Dict[str, Any]:
    """
    Deep-analyze a petition PDF using Gemini with Google Search.
    Acts as the KSERC Commission — makes actual per-component decisions.

    Returns a structured dict of decisions for the Auditor to apply.
    """
    from src.gemini_client import generate

    # 1. Extract full PDF text
    logger.info(f"[Analyzer] Extracting full text from PDF: {pdf_path}")
    pdf_text = _extract_full_pdf_text(pdf_path)
    if not pdf_text:
        logger.warning("[Analyzer] No text extracted from PDF.")
        return _empty_insights()

    # 2. Load local knowledge base
    knowledge_base = _load_knowledge_base()

    # 3. Build the prompt with all context
    full_prompt = (
        f"{ANALYZER_PROMPT}\n\n"
        f"=== CURRENT PETITION DETAILS ===\n"
        f"Licensee: {licensee_name}\n"
        f"Financial Year: {financial_year}\n\n"
        f"=== LOCAL KNOWLEDGE BASE ===\n{knowledge_base}\n\n"
        f"=== FULL PETITION TEXT ===\n{pdf_text}\n\n"
        f"Now act as the KSERC Commission. For each expense component, decide the "
        f"approved amount. Search the web for actual CPI/WPI inflation for FY {financial_year}, "
        f"grants given to {licensee_name}, and any interim relief orders. "
        f"Return your decisions as JSON."
    )

    # 4. Call Gemini via centralized client
    try:
        raw = generate(
            full_prompt,
            model=GEMINI_MODEL,
            temperature=0.1,
            response_mime_type="application/json",
            system_instruction=(
                "You are the Kerala State Electricity Regulatory Commission (KSERC). "
                "You must rigorously audit the licensee's claims against the provided regulations. "
                "Think step-by-step for each expense component before making your final decision. "
                "Your final output must be exactly matching the requested JSON structure."
            ),
        )
        logger.info(f"[Analyzer] Gemini response (first 800 chars): {raw[:800]}")

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        insights = json.loads(raw)
        logger.info(
            f"[Analyzer] AI Commission decisions received: "
            f"{len(insights.get('approved_expenses', {}))} components decided"
        )
        return insights

    except json.JSONDecodeError as e:
        logger.error(f"[Analyzer] Failed to parse Gemini JSON response: {e}")
        logger.error(f"[Analyzer] Raw response: {raw[:1000]}")
        return _empty_insights()
    except Exception as e:
        logger.error(f"[Analyzer] Gemini call failed: {e}")
        return _empty_insights()


def _empty_insights() -> Dict[str, Any]:
    """Return an empty insights dict when analysis fails."""
    return {
        "approved_expenses": {},
        "inflation_data": {},
        "grants_discovered": {"found": False, "total_lakhs": 0.0, "details": ""},
        "interim_relief": {"found": False, "amount_lakhs": 0.0, "details": ""},
        "overall_assessment": "Deep analysis was not performed — using fallback rule-based auditor.",
    }
