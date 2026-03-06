"""
KSERC SDL Truing Up — Deep Table Extractor
============================================

Extracts ALL tables from a KSERC petition PDF — not just the main ARR summary.
Sends ALL pages to Gemini Vision in batches and asks it to identify and extract
every table with its context, justification text, and structured data.

Tables extracted include:
- Phase-wise Power Purchase Cost (fixed/variable/incentive per campus)
- Employee Cost breakdown (salary, pension, medical, etc.)
- R&M breakdown by category  
- A&G breakdown (audit fees, BEE fee, legal, insurance, etc.)
- GFA & Depreciation schedule (opening, additions, closing, rate)
- Capital structure (equity, debt, grants, consumer contribution)
- Energy balance (input, sold, loss %, demand kVA)
- Escalation factor computation (CPI, WPI, weighted average)
- Non-tariff income breakdown
- Loan details (balances, interest rates)
- Consumer security deposit details
- Working capital computation
- Any other tables present in the petition

The output is a structured dict stored in state["detailed_tables"].
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
# Deep Table Extraction Prompt
# ══════════════════════════════════════════════════════════════════════════

DEEP_TABLE_PROMPT = """You are an expert KSERC (Kerala State Electricity Regulatory Commission) document analyst.

Your task: Extract EVERY table and supporting justification text from this KSERC petition PDF.

IMPORTANT: This petition is filed by a distribution licensee for truing-up of accounts.
It contains multiple tables under different expense/revenue components. You must extract
ALL of them, not just the main ARR summary table.

For EACH table you find, extract:
1. The table title/heading (e.g., "Table 9: Phase wise power purchase cost for 2022-23")
2. The table number if present
3. The component it belongs to (power_purchase, employee, rm, ag, depreciation, etc.)
4. ALL rows and columns as structured data
5. Any justification text the licensee provides before/after the table explaining their claim

Return a JSON object with this structure:

{
  "tables_found": [
    {
      "table_number": "Table 9",
      "title": "Phase wise power purchase cost for the period 2022-23",
      "component": "power_purchase",
      "page_number": 5,
      "headers": ["Campus", "Maximum demand kVA", "Energy Received lakh units", "Fixed charges Rs lakh", "Variable charges Rs lakh", "Incentive Rs lakh", "Other charge Rs lakh", "Total charge Rs lakh"],
      "rows": [
        {"Campus": "Phase-1", "Maximum demand kVA": 135000, "Energy Received lakh units": 432.09, "Fixed charges Rs lakh": 500.25, "Variable charges Rs lakh": 2541.91, "Incentive Rs lakh": -38.48, "Other charge Rs lakh": 0, "Total charge Rs lakh": 3003.68},
        {"Campus": "Phase -2 & 3", "Maximum demand kVA": 55158, "Energy Received lakh units": 212.75, "Fixed charges Rs lakh": 205.00, "Variable charges Rs lakh": 1252.55, "Incentive Rs lakh": -19.78, "Other charge Rs lakh": 0, "Total charge Rs lakh": 1437.77}
      ],
      "totals": {"Maximum demand kVA": 202834, "Energy Received lakh units": 669.67, "Total charge Rs lakh": 4652.88},
      "derived_values": {"avg_power_purchase_cost_per_unit": 6.95}
    }
  ],
  "component_justifications": {
    "power_purchase": "The licensee states that power purchase cost increased from Rs.3494.83 lakh in 2021-22 to Rs.4652.88 lakh in 2022-23 due to increase in energy consumption. The average cost of power purchase has increased from Rs.6.79 per unit to Rs.6.95 per unit.",
    "employee_cost": "The licensee claims Rs.54.54 lakh towards employee expenses as against Rs.27.14 lakh approved in ARR. The increase is stated to be on account of revision of pay scales and addition of new staff for Phase-IV campus.",
    "repair_maintenance": "The R&M expenses of Rs.447.65 lakh are claimed as against Rs.317.37 lakh approved. The licensee states that the increase is due to replacement of damaged cables in Phase-1 and maintenance of new installations.",
    "admin_general": "A&G expenses of Rs.92.05 lakh include statutory audit fee, energy audit fee (BEE mandated), insurance, legal expenses, and other administrative costs.",
    "depreciation": "Depreciation of Rs.162.45 lakh is claimed based on SLM method at CERC rates on the approved GFA.",
    "interest_long_term": "Interest on long term loan of Rs.8.96 lakh is claimed on the outstanding loan balance.",
    "interest_consumer_deposits": "Interest on consumer security deposits of Rs.72.70 lakh is claimed at SBI 1-year term deposit rate.",
    "return_on_nfa": "Return on NFA of Rs.86.60 lakh is claimed at the rate approved by KSERC.",
    "distribution_loss": "The actual distribution loss during 2022-23 was X.XX% as against the target of Y.YY% set in the MYT order.",
    "general": "Any overall justification text from the petition."
  },
  "energy_data": {
    "energy_input_mu": 0,
    "energy_sold_mu": 0,
    "energy_wheeled_mu": 0,
    "actual_distribution_loss_pct": 0,
    "max_demand_kva": 0,
    "contract_demand_kva": 0,
    "excess_demand_charges": 0
  },
  "capital_structure": {
    "equity": 0,
    "loan_outstanding": 0,
    "grants": 0,
    "consumer_contribution": 0,
    "opening_gfa": 0,
    "additions_gfa": 0,
    "closing_gfa": 0,
    "opening_nfa": 0,
    "closing_nfa": 0,
    "accumulated_depreciation": 0
  },
  "escalation_factors": {
    "cpi_annual_increase_pct": 0,
    "wpi_annual_increase_pct": 0,
    "weighted_avg_70_30_pct": 0,
    "four_year_average_pct": 0
  },
  "loan_details": [
    {
      "lender": "e.g. KSEB Ltd / Bank name",
      "outstanding_amount": 0,
      "interest_rate_pct": 0,
      "interest_amount": 0
    }
  ],
  "consumer_deposit_details": {
    "opening_balance": 0,
    "additions": 0,
    "refunds": 0,
    "closing_balance": 0,
    "interest_rate_pct": 0,
    "interest_amount": 0
  }
}

RULES:
- ALL monetary values are in Rs. Lakhs unless otherwise stated.
- Values in parentheses like (38.48) are NEGATIVE → return -38.48
- If a table or section is NOT present in the petition, omit it or use 0/empty values.
- Extract the ACTUAL justification text — quote the licensee's own words where possible.
- If there are year-over-year comparison tables (current year vs previous year), extract BOTH years.
- For energy data, convert units carefully: 1 MU = 10 lakh kWh.
- Include table numbers as they appear in the document (Table 1, Table 2, etc.)
- Do NOT fabricate data. If a value is unclear, use 0 and add a note.

Extract ALL tables from the provided pages. Return ONLY valid JSON."""


# ══════════════════════════════════════════════════════════════════════════
# Helper: Render PDF pages as images
# ══════════════════════════════════════════════════════════════════════════

def _render_all_pages(pdf_path: str, max_pages: int = 40, dpi: int = 150) -> List[bytes]:
    """
    Render ALL pages of the petition as PNG images for Gemini Vision.
    Uses 150 DPI (lower than ARR extraction's 200) to reduce token usage
    while maintaining table readability.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    total = min(total_pages, max_pages)
    images = []
    matrix = fitz.Matrix(dpi / 72, dpi / 72)

    for i in range(total):
        pix = doc[i].get_pixmap(matrix=matrix)
        images.append(pix.tobytes("png"))

    doc.close()
    logger.info(f"Rendered {len(images)}/{total_pages} pages at {dpi} DPI for deep table extraction")
    return images


# ══════════════════════════════════════════════════════════════════════════
# Core: Extract all tables from petition using Gemini Vision
# ══════════════════════════════════════════════════════════════════════════

def extract_all_tables(
    pdf_path: str,
    licensee_name: str = "",
    financial_year: str = "",
    max_pages: int = 40,
) -> Dict[str, Any]:
    """
    Extract ALL tables from a KSERC petition PDF using Gemini Vision.
    
    Sends pages in batches to handle large documents. Each batch covers
    ~10-15 pages. Results are merged across batches.
    
    Returns:
        Dict with keys: tables_found, component_justifications, energy_data,
        capital_structure, escalation_factors, loan_details,
        consumer_deposit_details
    """
    try:
        from src.gemini_client import generate_with_pdf
    except ImportError:
        logger.warning("google-genai not installed; deep table extraction skipped.")
        return _empty_result()

    # ── Check cache first ──────────────────────────────────────────────
    import hashlib
    cache_dir = Path(__file__).resolve().parent.parent.parent / ".extraction_cache"
    pdf_hash = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()[:16]
    cache_key = f"deep_{pdf_hash}_{licensee_name}_{financial_year}".replace(" ", "_")
    cache_file = cache_dir / f"{cache_key}.json"

    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            logger.info(f"[DEEP CACHE HIT] Using cached deep table extraction from {cache_file.name}")
            return cached
        except Exception as e:
            logger.warning(f"[DEEP CACHE] Failed to read cache: {e}, re-extracting...")

    # ── Single PDF upload call (replaces page rendering + batching) ────
    prompt = (
        f"This is the COMPLETE petition filed by "
        f"{licensee_name or 'a distribution licensee'} for FY {financial_year}. "
        f"Analyze the ENTIRE document.\n\n"
        f"{DEEP_TABLE_PROMPT}"
    )

    system_instruction = (
        "You are an expert KSERC petition analyst. "
        "Extract every table and justification from the provided PDF. "
        "Return ONLY valid JSON. No markdown. No explanation. "
        "All monetary values in Rs. Lakhs. "
        "Negative values in parentheses (e.g., (38.48) = -38.48). "
        "If no tables are found, return an empty tables_found array."
    )

    try:
        logger.info(f"[Deep Extract] Uploading entire PDF for single-call extraction...")
        raw = generate_with_pdf(
            pdf_path=pdf_path,
            prompt=prompt,
            model="gemini-2.5-flash",
            temperature=0.0,
            response_mime_type="application/json",
            system_instruction=system_instruction,
        )

        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        data = json.loads(raw)

    except json.JSONDecodeError as e:
        logger.error(f"[Deep Extract] JSON parse error: {e}")
        return _empty_result()
    except Exception as e:
        logger.error(f"[Deep Extract] PDF extraction failed: {e}")
        return _empty_result()

    # ── Build result from single-call response ─────────────────────────
    all_tables = data.get("tables_found", [])
    result = {
        "tables_found": all_tables,
        "component_justifications": data.get("component_justifications", {}),
        "energy_data": data.get("energy_data", {}),
        "capital_structure": data.get("capital_structure", {}),
        "escalation_factors": data.get("escalation_factors", {}),
        "loan_details": data.get("loan_details", []),
        "consumer_deposit_details": data.get("consumer_deposit_details", {}),
        "extraction_metadata": {
            "method": "native_pdf_upload",
            "total_tables_found": len(all_tables),
            "licensee": licensee_name,
            "financial_year": financial_year,
        },
    }

    logger.info(
        f"=== Deep Table Extraction Complete ===\n"
        f"  Method: Native PDF Upload (single call)\n"
        f"  Total tables found: {len(all_tables)}\n"
        f"  Components with justifications: {list(data.get('component_justifications', {}).keys())}\n"
        f"  Energy data fields: {len(data.get('energy_data', {}))}\n"
        f"  Capital structure fields: {len(data.get('capital_structure', {}))}\n"
        f"  Loan entries: {len(data.get('loan_details', []))}"
    )

    # ── Save to cache ──────────────────────────────────────────────────
    if all_tables:
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(
                json.dumps(result, indent=2, default=str), encoding="utf-8"
            )
            logger.info(f"[DEEP CACHE SAVE] Saved to {cache_file.name}")
        except Exception as e:
            logger.warning(f"[DEEP CACHE] Failed to save: {e}")

    return result


def _empty_result() -> Dict[str, Any]:
    """Return an empty result structure."""
    return {
        "tables_found": [],
        "component_justifications": {},
        "energy_data": {},
        "capital_structure": {},
        "escalation_factors": {},
        "loan_details": [],
        "consumer_deposit_details": {},
        "extraction_metadata": {"total_tables_found": 0},
    }


# ══════════════════════════════════════════════════════════════════════════
# Helpers: Look up specific table data from deep extraction
# ══════════════════════════════════════════════════════════════════════════

def get_tables_by_component(
    detailed_tables: Dict[str, Any], component: str
) -> List[Dict[str, Any]]:
    """
    Filter extracted tables by component name.
    
    Args:
        detailed_tables: Full deep extraction result
        component: One of "power_purchase", "employee", "rm", "ag",
                   "depreciation", "interest", "nfa", "nti", etc.
    
    Returns:
        List of table dicts belonging to that component.
    """
    tables = detailed_tables.get("tables_found", [])
    matching = []
    for t in tables:
        table_comp = str(t.get("component", "")).lower()
        title = str(t.get("title", "")).lower()
        
        # Match by component field
        if component.lower() in table_comp:
            matching.append(t)
            continue
        
        # Fallback: match by title keywords
        component_keywords = {
            "power_purchase": ["power purchase", "energy purchase", "ppc", "phase wise"],
            "employee": ["employee", "staff", "salary", "wages", "personnel"],
            "rm": ["repair", "maintenance", "r&m", "r & m"],
            "ag": ["admin", "general", "a&g", "a & g", "administration"],
            "depreciation": ["depreciation", "gfa", "gross fixed asset", "fixed assets"],
            "interest": ["interest", "loan", "finance charge", "working capital"],
            "nfa": ["net fixed asset", "nfa", "return on"],
            "nti": ["non-tariff", "non tariff", "other income", "miscellaneous"],
            "energy": ["energy", "distribution loss", "t&d loss", "demand"],
            "capital": ["capital", "equity", "grant", "consumer contribution"],
            "escalation": ["escalation", "cpi", "wpi", "inflation"],
            "deposit": ["deposit", "consumer security", "caution money"],
        }
        
        keywords = component_keywords.get(component.lower(), [component.lower()])
        if any(kw in title for kw in keywords):
            matching.append(t)
    
    return matching


def get_justification(
    detailed_tables: Dict[str, Any], component: str
) -> str:
    """
    Get the licensee's justification text for a specific component.
    
    Returns empty string if no justification found.
    """
    justifications = detailed_tables.get("component_justifications", {})
    
    # Direct match
    if component in justifications:
        return justifications[component]
    
    # Fuzzy match
    component_lower = component.lower()
    for key, text in justifications.items():
        if component_lower in key.lower() or key.lower() in component_lower:
            return text
    
    return ""


def get_phase_wise_ppc(detailed_tables: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get phase-wise / campus-wise power purchase cost breakdown.
    Returns list of rows with per-campus data.
    """
    ppc_tables = get_tables_by_component(detailed_tables, "power_purchase")
    
    for t in ppc_tables:
        title = str(t.get("title", "")).lower()
        if "phase" in title or "campus" in title:
            return t.get("rows", [])
    
    return []


def get_component_breakdown(
    detailed_tables: Dict[str, Any], component: str
) -> List[Dict[str, Any]]:
    """
    Get the itemized breakdown of a component (e.g., A&G items, R&M categories).
    Returns list of row dicts.
    """
    tables = get_tables_by_component(detailed_tables, component)
    
    # Find the breakdown/detail table (not the summary)
    for t in tables:
        rows = t.get("rows", [])
        if len(rows) >= 2:  # At least 2 rows = it's a breakdown
            return rows
    
    return []


# ══════════════════════════════════════════════════════════════════════════
# Order Table Extraction — Learn from Past KSERC Trued-Up Orders
# ══════════════════════════════════════════════════════════════════════════

# Prompt specifically designed for KSERC trued-up ORDERS (not petitions).
# Orders show what KSERC actually did with each table: what they approved,
# what they changed, and the reasoning behind each decision.

ORDER_TABLE_PROMPT = """You are an expert KSERC (Kerala State Electricity Regulatory Commission) order analyst.

Your task: Extract EVERY table from this KSERC Truing-Up ORDER along with KSERC's DECISIONS
on each component. This is NOT a petition — this is KSERC's official order responding to a petition.

CRITICAL DIFFERENCE from a petition:
- The order shows BOTH what the licensee CLAIMED and what KSERC APPROVED.
- For each component, KSERC provides reasoning for any difference.
- Tables often have columns like "Claimed by licensee" and "Approved by Commission" or
  "Revised ARR&ERC Approved" vs "Actual / Trued up amount".

For EACH table and component decision, extract:

{
  "order_tables": [
    {
      "table_number": "Table X",
      "title": "title of the table",
      "component": "power_purchase|employee|rm|ag|depreciation|interest|nfa|energy|capital|other",
      "headers": ["column headers"],
      "rows": [{"column1": val, "column2": val}],
      "totals": {}
    }
  ],
  "kserc_decisions": {
    "power_purchase": {
      "claimed_amount": 0,
      "approved_amount": 0,
      "adjustment_amount": 0,
      "kserc_reasoning": "Quote KSERC's exact reasoning text for their decision on PPC",
      "key_observations": ["List of specific observations KSERC made"],
      "methodology_applied": "What method/rule KSERC used (e.g., Regulation 73(3), distribution loss penalty)"
    },
    "employee_cost": {
      "claimed_amount": 0,
      "approved_amount": 0,
      "adjustment_amount": 0,
      "kserc_reasoning": "KSERC's reasoning for employee cost decision",
      "key_observations": ["e.g., 'excess over MYT norm', 'not supported by documents'"],
      "methodology_applied": "e.g., 'Capped at MYT approved norm for the year'"
    },
    "repair_maintenance": {
      "claimed_amount": 0,
      "approved_amount": 0,
      "adjustment_amount": 0,
      "kserc_reasoning": "",
      "key_observations": [],
      "methodology_applied": ""
    },
    "admin_general": {
      "claimed_amount": 0,
      "approved_amount": 0,
      "adjustment_amount": 0,
      "kserc_reasoning": "",
      "key_observations": [],
      "methodology_applied": ""
    },
    "depreciation": {
      "claimed_amount": 0,
      "approved_amount": 0,
      "adjustment_amount": 0,
      "kserc_reasoning": "",
      "key_observations": [],
      "methodology_applied": ""
    },
    "interest_long_term": {
      "claimed_amount": 0,
      "approved_amount": 0,
      "adjustment_amount": 0,
      "kserc_reasoning": "",
      "key_observations": [],
      "methodology_applied": ""
    },
    "interest_consumer_deposits": {
      "claimed_amount": 0,
      "approved_amount": 0,
      "adjustment_amount": 0,
      "kserc_reasoning": "",
      "key_observations": [],
      "methodology_applied": ""
    },
    "return_on_nfa": {
      "claimed_amount": 0,
      "approved_amount": 0,
      "adjustment_amount": 0,
      "kserc_reasoning": "",
      "key_observations": [],
      "methodology_applied": ""
    },
    "other_debits": {
      "claimed_amount": 0,
      "approved_amount": 0,
      "adjustment_amount": 0,
      "kserc_reasoning": "",
      "key_observations": [],
      "methodology_applied": ""
    }
  },
  "energy_decision": {
    "actual_loss_pct": 0,
    "target_loss_pct": 0,
    "penalty_or_gain": 0,
    "kserc_reasoning": "KSERC's reasoning on distribution loss",
    "excess_demand_action": "What KSERC said about excess demand charges"
  },
  "capital_structure_verified": {
    "gfa_claimed": 0,
    "gfa_approved": 0,
    "additions_claimed": 0,
    "additions_approved": 0,
    "kserc_reasoning": ""
  },
  "final_summary": {
    "total_claimed": 0,
    "total_approved": 0,
    "total_disallowed": 0,
    "revenue_gap_surplus": 0
  }
}

RULES:
- ALL monetary values are in Rs. Lakhs.
- Quote KSERC's EXACT reasoning text — do not paraphrase or summarize.
- Extract EVERY table from the order, including ARR comparison tables, energy tables, asset tables.
- For kserc_decisions, focus on what KSERC CHANGED from the claimed amount and WHY.
- If KSERC approved as claimed, still note that with reasoning like "approved as pet the petition".
- Include references to regulations (e.g., "Regulation 73(3)", "Regulation 27", "MYT Order para 15").
- Return ONLY valid JSON. No markdown.
"""


def extract_order_tables(
    pdf_path: str,
    licensee_name: str = "",
    financial_year: str = "",
    order_ref: str = "",
    max_pages: int = 40,
) -> Dict[str, Any]:
    """
    Extract ALL tables and KSERC decisions from a past trued-up order PDF.
    
    This is different from extract_all_tables() — it uses a specialized prompt
    that captures KSERC's decisions (claimed vs approved, reasoning, methodology).
    
    Returns:
        Dict with keys: order_tables, kserc_decisions, energy_decision,
        capital_structure_verified, final_summary
    """
    try:
        from src.gemini_client import generate_with_pdf
    except ImportError:
        logger.warning("google-genai not installed; order table extraction skipped.")
        return {}

    # ── Check cache ─────────────────────────────────────────────────────
    import hashlib
    cache_dir = Path(__file__).resolve().parent.parent.parent / ".extraction_cache"
    pdf_hash = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()[:16]
    cache_key = f"order_deep_{pdf_hash}_{licensee_name}_{financial_year}".replace(" ", "_")
    cache_file = cache_dir / f"{cache_key}.json"

    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            logger.info(f"[ORDER CACHE HIT] {licensee_name} FY {financial_year}")
            return cached
        except Exception:
            pass

    # ── Single PDF upload call (replaces rendering + batching) ──────────
    prompt = (
        f"This is the COMPLETE KSERC Truing-Up ORDER for "
        f"{licensee_name or 'a licensee'} FY {financial_year} "
        f"(Order ref: {order_ref}). "
        f"Analyze the ENTIRE document.\n\n"
        f"{ORDER_TABLE_PROMPT}"
    )

    system_instruction = (
        "You are an expert KSERC order analyst. "
        "Extract every table and KSERC decision from the provided trued-up order. "
        "Return ONLY valid JSON. No markdown. "
        "All monetary values in Rs. Lakhs. "
        "Quote KSERC's EXACT reasoning text."
    )

    try:
        logger.info(f"[Order Extract] Uploading entire order PDF for {licensee_name} FY {financial_year}...")
        raw = generate_with_pdf(
            pdf_path=pdf_path,
            prompt=prompt,
            model="gemini-2.5-flash",
            temperature=0.0,
            response_mime_type="application/json",
            system_instruction=system_instruction,
        )

        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        data = json.loads(raw)

    except json.JSONDecodeError as e:
        logger.error(f"[Order Extract] JSON parse error for {licensee_name}: {e}")
        return {}
    except Exception as e:
        logger.error(f"[Order Extract] PDF extraction failed for {licensee_name}: {e}")
        return {}

    # ── Build result ────────────────────────────────────────────────────
    all_order_tables = data.get("order_tables", [])
    result = {
        "order_tables": all_order_tables,
        "kserc_decisions": data.get("kserc_decisions", {}),
        "energy_decision": data.get("energy_decision", {}),
        "capital_structure_verified": data.get("capital_structure_verified", {}),
        "final_summary": data.get("final_summary", {}),
        "_meta": {
            "licensee": licensee_name,
            "fy": financial_year,
            "order_ref": order_ref,
            "method": "native_pdf_upload",
            "tables_found": len(all_order_tables),
        },
    }

    # ── Save to cache ──────────────────────────────────────────────────
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps(result, indent=2, default=str), encoding="utf-8"
        )
        logger.info(f"[ORDER CACHE SAVE] {cache_file.name}")
    except Exception as e:
        logger.warning(f"[ORDER CACHE] Failed to save: {e}")

    return result


def learn_from_past_orders() -> Dict[str, Any]:
    """
    Process ALL past trued-up orders and build a cross-licensee learning database.
    
    For each order, extracts tables and KSERC decisions. The result is a structured
    knowledge base that tells the auditor: "For this component, KSERC historically
    did X because Y."
    
    Returns:
        Dict with structure:
        {
            "order_learnings": {
                "Technopark_2022-23": { kserc_decisions, energy_decision, ... },
                "KDHP_2022-23":       { kserc_decisions, energy_decision, ... },
                ...
            },
            "cross_licensee_patterns": {
                "employee_cost": { avg_cut_pct, common_reasoning, ... },
                ...
            }
        }
    """
    import os

    # Import the TRUING_UP_ORDERS list
    try:
        from src.rag.precedent_extractor import TRUING_UP_ORDERS, DOCS_DIR
    except ImportError:
        logger.warning("precedent_extractor not available; cannot learn from past orders.")
        return {"order_learnings": {}, "cross_licensee_patterns": {}}

    # ── Check if we have a combined cache ──────────────────────────────
    cache_dir = Path(__file__).resolve().parent.parent.parent / ".extraction_cache"
    combined_cache = cache_dir / "all_order_learnings.json"

    if combined_cache.exists():
        try:
            cached = json.loads(combined_cache.read_text(encoding="utf-8"))
            count = len(cached.get("order_learnings", {}))
            logger.info(f"[ORDER LEARNING CACHE HIT] {count} past orders loaded")
            return cached
        except Exception:
            pass

    # ── Process orders in PARALLEL (3 at a time) ─────────────────────────
    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed

    order_learnings = {}

    # Build list of valid orders to process
    valid_orders = []
    for order_info in TRUING_UP_ORDERS:
        filepath = os.path.join(DOCS_DIR, order_info["file"])
        if not os.path.exists(filepath):
            logger.warning(f"Order file not found: {filepath}")
            continue
        valid_orders.append((order_info, filepath))

    logger.info(f"[ORDER LEARNING] Processing {len(valid_orders)} orders in parallel (3 at a time)...")

    def _process_single_order(order_info, filepath):
        """Process a single order — designed to run in a thread."""
        licensee = order_info["licensee"]
        fy = order_info["fy"]
        key = f"{licensee}_{fy}"
        logger.info(f"Learning from order: {licensee} FY {fy} ({order_info['file']})")
        result = extract_order_tables(
            pdf_path=filepath,
            licensee_name=licensee,
            financial_year=fy,
            order_ref=order_info.get("order_ref", ""),
        )
        return key, result

    # Run 3 orders in parallel to respect API rate limits
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_process_single_order, oi, fp): oi
            for oi, fp in valid_orders
        }
        for future in as_completed(futures):
            try:
                key, result = future.result()
                if result:
                    order_learnings[key] = result
                    decisions = result.get("kserc_decisions", {})
                    logger.info(f"  -> {len(decisions)} component decisions extracted for {key}")
                    for comp, d in decisions.items():
                        if isinstance(d, dict) and d.get("adjustment_amount", 0) != 0:
                            logger.info(
                                f"    {comp}: claimed={d.get('claimed_amount')}, "
                                f"approved={d.get('approved_amount')}, "
                                f"cut={d.get('adjustment_amount')}"
                            )
            except Exception as e:
                logger.error(f"  Order processing failed: {e}")

    # ── Build cross-licensee patterns ──────────────────────────────────
    cross_patterns = _build_cross_licensee_patterns(order_learnings)

    combined = {
        "order_learnings": order_learnings,
        "cross_licensee_patterns": cross_patterns,
    }

    # ── Save combined cache ────────────────────────────────────────────
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        combined_cache.write_text(
            json.dumps(combined, indent=2, default=str), encoding="utf-8"
        )
        logger.info(f"[ORDER LEARNING SAVE] Saved {len(order_learnings)} order learnings")
    except Exception as e:
        logger.warning(f"[ORDER LEARNING] Failed to save: {e}")

    return combined


def _build_cross_licensee_patterns(
    order_learnings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze table-level decisions across all past orders to find patterns.
    
    For each component, compute:
    - How often KSERC approves as claimed vs cuts
    - Average cut percentage
    - Common reasoning patterns
    - Regulation references
    """
    patterns = {}
    components = [
        "power_purchase", "employee_cost", "repair_maintenance",
        "admin_general", "depreciation", "interest_long_term",
        "interest_consumer_deposits", "return_on_nfa", "other_debits"
    ]

    for comp in components:
        entries = []
        reasonings = []
        methodologies = []

        for order_key, order_data in order_learnings.items():
            decisions = order_data.get("kserc_decisions", {})
            decision = decisions.get(comp, {})
            if not isinstance(decision, dict):
                continue

            claimed = float(decision.get("claimed_amount", 0) or 0)
            approved = float(decision.get("approved_amount", 0) or 0)
            reasoning = decision.get("kserc_reasoning", "")
            methodology = decision.get("methodology_applied", "")

            if claimed > 0:
                cut_pct = round((claimed - approved) / claimed * 100, 2) if claimed else 0
                entries.append({
                    "order": order_key,
                    "claimed": claimed,
                    "approved": approved,
                    "cut_pct": cut_pct,
                })

            if reasoning:
                reasonings.append(f"[{order_key}] {reasoning}")
            if methodology:
                methodologies.append(methodology)

        if entries:
            avg_cut = round(sum(e["cut_pct"] for e in entries) / len(entries), 2)
            times_cut = sum(1 for e in entries if e["cut_pct"] > 0.5)
            times_approved = sum(1 for e in entries if e["cut_pct"] <= 0.5)

            patterns[comp] = {
                "total_orders_analyzed": len(entries),
                "times_kserc_cut": times_cut,
                "times_approved_as_claimed": times_approved,
                "avg_cut_percentage": avg_cut,
                "max_cut_pct": max(e["cut_pct"] for e in entries),
                "min_cut_pct": min(e["cut_pct"] for e in entries),
                "entries": entries,
                "common_reasonings": reasonings[:5],  # Top 5 reasonings
                "methodologies": list(set(methodologies)),
            }

    return patterns


# ══════════════════════════════════════════════════════════════════════════
# LangGraph Node Function
# ══════════════════════════════════════════════════════════════════════════

def deep_extract_node(state: dict) -> dict:
    """
    LangGraph node: extract ALL tables from a KSERC petition PDF AND
    learn from past trued-up orders.
    
    Called AFTER the main ARR extraction (extract_petition_data).
    Stores results in state["detailed_tables"].
    
    Two-phase process:
    1. Extract ALL tables from the current petition
    2. Learn from ALL past trued-up orders (cached after first run)
       — This gives the auditor cross-licensee table-level decisions
    """
    pdf_path = state.get("petition_pdf_path", "")
    licensee = state.get("licensee_name", "Unknown")
    fy = state.get("financial_year", "")

    logger.info(f"=== deep_extract_node: {licensee} FY {fy} ===")

    if not pdf_path or not Path(pdf_path).exists():
        logger.warning(f"Petition PDF not found: {pdf_path}")
        return {"detailed_tables": _empty_result()}

    # ── Phase 1: Extract tables from current petition ──────────────────
    logger.info("--- Phase 1: Deep table extraction from petition ---")
    result = extract_all_tables(
        pdf_path=pdf_path,
        licensee_name=licensee,
        financial_year=fy,
    )

    # Log summary of what was found
    tables_found = result.get("tables_found", [])
    justifications = result.get("component_justifications", {})
    
    logger.info(f"Deep extraction found {len(tables_found)} tables:")
    for t in tables_found:
        title = t.get("title", "untitled")
        comp = t.get("component", "?")
        rows = len(t.get("rows", []))
        logger.info(f"  [{comp}] {title} ({rows} rows)")

    logger.info(f"Justifications for {len(justifications)} components:")
    for comp, text in justifications.items():
        preview = str(text)[:80]
        logger.info(f"  {comp}: {preview}...")

    # ── Phase 2: Learn from past trued-up orders ───────────────────────
    logger.info("--- Phase 2: Learning from past trued-up orders ---")
    order_learnings = learn_from_past_orders()

    # Attach order learnings to the result so auditor can access them
    result["order_learnings"] = order_learnings.get("order_learnings", {})
    result["cross_licensee_patterns"] = order_learnings.get("cross_licensee_patterns", {})

    # Log cross-licensee patterns
    patterns = result.get("cross_licensee_patterns", {})
    if patterns:
        logger.info(f"=== Cross-Licensee Patterns ({len(patterns)} components) ===")
        for comp, p in patterns.items():
            if isinstance(p, dict):
                logger.info(
                    f"  {comp}: avg_cut={p.get('avg_cut_percentage', 0)}%, "
                    f"cut {p.get('times_kserc_cut', 0)}/{p.get('total_orders_analyzed', 0)} times"
                )

    # Enrich energy data into state if found
    energy = result.get("energy_data", {})
    enrichments = {}
    if energy.get("energy_input_mu", 0) > 0 and state.get("energy_input_mu", 0) == 0:
        enrichments["energy_input_mu"] = energy["energy_input_mu"]
    if energy.get("energy_sold_mu", 0) > 0 and state.get("energy_sold_mu", 0) == 0:
        enrichments["energy_sold_mu"] = energy["energy_sold_mu"]
    if energy.get("excess_demand_charges", 0) > 0 and state.get("excess_demand_charges", 0) == 0:
        enrichments["excess_demand_charges"] = energy["excess_demand_charges"]

    if enrichments:
        logger.info(f"Enriched state with energy data: {enrichments}")

    return {
        "detailed_tables": result,
        **enrichments,
    }
