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
from src.config import GEMINI_MODEL

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
    all_pdf_paths: List[str],
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

    # ── Check cache first (Firestore-backed, persists across deployments) ──
    from src.tools.extraction_cache import (
        compute_pdf_hash, get_cached_deep_extraction, save_deep_extraction_cache
    )
    pdf_hash = compute_pdf_hash(all_pdf_paths)

    cached = None  # DISABLED: fresh extraction for current petition always
    if cached:
        return cached

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
        logger.info(f"[Deep Extract] Uploading {len(all_pdf_paths)} PDF(s) for single-call extraction...")
        raw = generate_with_pdf(
            pdf_path=all_pdf_paths if len(all_pdf_paths) > 1 else all_pdf_paths[0],
            prompt=prompt,
            model=GEMINI_MODEL,
            temperature=0.0,
            response_mime_type="application/json",
            system_instruction=system_instruction,
        )

        if not raw:
            logger.warning("[Deep Extract] Gemini returned empty response")
            return {}
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        data = None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"[Deep Extract] Initial JSON parse failed: {e}")
            # Recovery 1: Fix common issues (trailing commas, unescaped chars)
            fixed = raw
            fixed = re.sub(r',\s*}', '}', fixed)  # trailing comma before }
            fixed = re.sub(r',\s*]', ']', fixed)  # trailing comma before ]
            try:
                data = json.loads(fixed)
                logger.info("[Deep Extract] JSON recovered after trailing-comma fix")
            except json.JSONDecodeError:
                pass
            
            # Recovery 2: Truncate at last valid closing brace
            if data is None:
                # Find the last complete object
                brace_count = 0
                last_valid = -1
                for i, ch in enumerate(raw):
                    if ch == '{': brace_count += 1
                    elif ch == '}': 
                        brace_count -= 1
                        if brace_count == 0:
                            last_valid = i
                            break
                if last_valid > 0:
                    truncated = raw[:last_valid + 1]
                    truncated = re.sub(r',\s*}', '}', truncated)
                    truncated = re.sub(r',\s*]', ']', truncated)
                    try:
                        data = json.loads(truncated)
                        logger.info(f"[Deep Extract] JSON recovered by truncating at pos {last_valid}")
                    except json.JSONDecodeError:
                        pass
            
            if data is None:
                logger.error(f"[Deep Extract] JSON recovery failed. Raw length: {len(raw)}, first 200: {raw[:200]}")
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

    # ── Save to cache (Firestore-backed) ──────────────────────────────
    if all_tables:
        pass  # DISABLED: never cache petition data — always fresh extract
        # save_deep_extraction_cache(pdf_hash, licensee_name, financial_year, result)

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

    # ── Check cache (Firestore-backed, persists across deployments) ──────
    from src.tools.extraction_cache import (
        compute_pdf_hash as _hash, get_cached_order_extraction, save_order_extraction_cache
    )
    pdf_hash = _hash(pdf_path)

    cached = get_cached_order_extraction(pdf_hash, licensee_name, financial_year)
    if cached:
        return cached

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
            model=GEMINI_MODEL,
            temperature=0.0,
            response_mime_type="application/json",
            system_instruction=system_instruction,
        )

        if not raw:
            logger.warning(f"[Order Extract] Gemini returned empty response for {licensee_name}")
            return {}
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

    # ── Save to cache (Firestore-backed) ──────────────────────────────
    save_order_extraction_cache(pdf_hash, licensee_name, financial_year, result)

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

    # ── Check combined cache (Firestore-backed) ───────────────────────
    from src.tools.extraction_cache import get_cached_all_order_learnings, save_all_order_learnings

    cached = get_cached_all_order_learnings()
    if cached:
        count = len(cached.get("order_learnings", {}))
        logger.info(f"[ORDER LEARNING CACHE HIT] {count} past orders loaded from Firestore")
        return cached

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

    # ── Save combined cache (Firestore-backed) ───────────────────────
    save_all_order_learnings(combined)
    logger.info(f"[ORDER LEARNING SAVE] Saved {len(order_learnings)} order learnings")

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
    all_pdf_paths = [pdf_path] + state.get("annexure_pdf_paths", [])
    result = extract_all_tables(
        all_pdf_paths=all_pdf_paths,
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

    # ── Phase 3: Extract wage revision data from employee cost details ──
    # Wage revision is petition-specific (any licensee can have it in any year).
    # Sources:
    #   1. Employee cost table rows mentioning "wage/pay revision" or "prior period"
    #   2. Employee cost justification text mentioning revision amounts
    wage_revision_current = 0.0
    wage_revision_prior = 0.0

    # Source 1: Scan employee cost tables for wage revision line items
    employee_tables = get_tables_by_component(result, "employee")
    for t in employee_tables:
        for row in t.get("rows", []):
            # Check each column for wage/pay revision keywords
            row_text = " ".join(str(v).lower() for v in row.values())
            if any(kw in row_text for kw in ["wage revision", "pay revision", "salary revision"]):
                # Try to find the amount value — look for numeric columns
                for col_name, val in row.items():
                    col_lower = col_name.lower()
                    if any(fy_kw in col_lower for fy_kw in [fy, "current", "amount", "total", "actual"]):
                        try:
                            amt = float(str(val).replace(",", "").replace("(", "-").replace(")", ""))
                            if amt > 0:
                                if "prior" in row_text:
                                    wage_revision_prior = amt
                                    logger.info(f"Found prior period wage revision: Rs.{amt:.2f}L from table")
                                else:
                                    wage_revision_current = amt
                                    logger.info(f"Found current year wage revision: Rs.{amt:.2f}L from table")
                        except (ValueError, TypeError):
                            pass
            elif "prior period" in row_text:
                for col_name, val in row.items():
                    col_lower = col_name.lower()
                    if any(fy_kw in col_lower for fy_kw in [fy, "current", "amount", "total", "actual"]):
                        try:
                            amt = float(str(val).replace(",", "").replace("(", "-").replace(")", ""))
                            if amt > 0:
                                wage_revision_prior = amt
                                logger.info(f"Found prior period amount: Rs.{amt:.2f}L from table")
                        except (ValueError, TypeError):
                            pass

    # Source 2: Parse employee justification text for revision amounts
    if wage_revision_current == 0.0 or wage_revision_prior == 0.0:
        emp_justification = get_justification(result, "employee")
        if emp_justification:
            import re as _re

            # ── Pattern A: Cumulative breakdown like
            # "Rs.48.12 (Rs.27.21 for 2023-24 and Rs.20.91 for 2024-25)"
            cumulative_pattern = _re.compile(
                r"(?:rs\.?\s*|₹\s*)([\d,.]+)\s*(?:lakh|lac)?\s*"
                r"\(\s*(?:rs\.?\s*|₹\s*)([\d,.]+)\s*(?:lakh|lac)?\s*"
                r"(?:for\s+)?(\d{4}[-–]\d{2,4})\s*"
                r"(?:and|&|,)\s*"
                r"(?:rs\.?\s*|₹\s*)([\d,.]+)\s*(?:lakh|lac)?\s*"
                r"(?:for\s+)?(\d{4}[-–]\d{2,4})\s*\)",
                _re.IGNORECASE,
            )
            cm = cumulative_pattern.search(emp_justification)
            if cm:
                try:
                    amt1 = float(cm.group(2).replace(",", ""))
                    fy1 = cm.group(3)
                    amt2 = float(cm.group(4).replace(",", ""))
                    fy2 = cm.group(5)
                    # Match year to current FY to decide which is current vs prior
                    fy_short = fy[-2:] if len(fy) >= 2 else fy  # e.g. "25" from "2024-25"
                    if fy_short in fy2 or fy in fy2:
                        wage_revision_current = amt2
                        wage_revision_prior = amt1
                    elif fy_short in fy1 or fy in fy1:
                        wage_revision_current = amt1
                        wage_revision_prior = amt2
                    else:
                        # Can't determine — assign larger as current
                        wage_revision_current = max(amt1, amt2)
                        wage_revision_prior = min(amt1, amt2)
                    logger.info(
                        f"Cumulative wage breakdown: {fy1}=Rs.{amt1:.2f}L, {fy2}=Rs.{amt2:.2f}L → "
                        f"current={wage_revision_current:.2f}L, prior={wage_revision_prior:.2f}L"
                    )
                except (ValueError, TypeError, IndexError):
                    pass

            # ── Pattern B: "additional impact of wage revision... amounts to Rs.20.91"
            if wage_revision_current == 0.0:
                additional_pattern = _re.compile(
                    r"(?:additional\s+impact|current\s+(?:financial\s+)?year)[^.]*?"
                    r"(?:rs\.?\s*|₹\s*)([\d,.]+)\s*(?:lakh|lac)",
                    _re.IGNORECASE,
                )
                am = additional_pattern.search(emp_justification)
                if am:
                    try:
                        amt = float(am.group(1).replace(",", ""))
                        if amt > 0:
                            wage_revision_current = amt
                            logger.info(f"Found current year wage revision (additional impact): Rs.{amt:.2f}L")
                    except (ValueError, TypeError):
                        pass

            # ── Pattern C: "claim of Rs.27.21... was not allowed" → prior period
            if wage_revision_prior == 0.0:
                denied_pattern = _re.compile(
                    r"(?:claim|claimed)[^.]*?(?:rs\.?\s*|₹\s*)([\d,.]+)\s*(?:lakh|lac)[^.]*?"
                    r"(?:not\s+allowed|denied|rejected|disallowed)",
                    _re.IGNORECASE,
                )
                dm = denied_pattern.search(emp_justification)
                if dm:
                    try:
                        amt = float(dm.group(1).replace(",", ""))
                        if amt > 0:
                            wage_revision_prior = amt
                            logger.info(f"Found prior period wage revision (denied earlier): Rs.{amt:.2f}L")
                    except (ValueError, TypeError):
                        pass

            # ── Pattern D (fallback): Generic wage revision amount extraction
            if wage_revision_current == 0.0:
                wage_pattern = _re.compile(
                    r"(?:wage|pay|salary)\s*revision[^.]*?"
                    r"(?:rs\.?\s*|₹\s*)([\d,.]+)\s*(?:lakh|lac|cr)",
                    _re.IGNORECASE,
                )
                # Collect all matches and try to assign correctly
                all_matches = []
                for m in wage_pattern.finditer(emp_justification):
                    try:
                        amt = float(m.group(1).replace(",", ""))
                        context = emp_justification[max(0, m.start()-100):m.end()+100].lower()
                        is_denied = any(kw in context for kw in ["not allowed", "denied", "rejected", "disallowed"])
                        is_prior = "prior" in context or is_denied
                        all_matches.append({"amt": amt, "is_prior": is_prior, "context": context[:60]})
                    except (ValueError, TypeError):
                        pass

                for match in all_matches:
                    if match["is_prior"] and wage_revision_prior == 0.0:
                        wage_revision_prior = match["amt"]
                        logger.info(f"Found prior period wage revision: Rs.{match['amt']:.2f}L")
                    elif not match["is_prior"] and wage_revision_current == 0.0:
                        wage_revision_current = match["amt"]
                        logger.info(f"Found current year wage revision from justification: Rs.{match['amt']:.2f}L")

            # ── Pattern E (fallback): "prior period" amounts
            if wage_revision_prior == 0.0:
                prior_pattern = _re.compile(
                    r"prior\s*period[^.]*?"
                    r"(?:rs\.?\s*|₹\s*)([\d,.]+)\s*(?:lakh|lac|cr)",
                    _re.IGNORECASE,
                )
                for m in prior_pattern.finditer(emp_justification):
                    try:
                        amt = float(m.group(1).replace(",", ""))
                        if amt > 0 and wage_revision_prior == 0.0:
                            wage_revision_prior = amt
                            logger.info(f"Found prior period from justification text: Rs.{amt:.2f}L")
                    except (ValueError, TypeError):
                        pass

    # Source 3: Dedicated Gemini call for wage revision (FALLBACK)
    # Runs when Sources 1-2 fail (deep extraction returned 0 employee tables)
    if wage_revision_current == 0.0 and wage_revision_prior == 0.0:
        logger.info("[Wage Revision] Sources 1-2 found nothing, trying focused Gemini extraction...")
        try:
            from src.gemini_client import generate_with_pdf as _gen_pdf
            wage_prompt = (
                f"Analyze this KSERC truing-up petition for {licensee} FY {fy}.\n\n"
                f"Find if the licensee EXPLICITLY claims WAGE REVISION or PAY REVISION.\n"
                f"This means a formal government-mandated pay scale revision such as:\n"
                f"- Wage revision / Pay revision / Salary revision\n"
                f"- Pay commission implementation (e.g., 11th BPC, CDA pay revision)\n"
                f"- Pay arrears specifically from a wage/pay revision\n"
                f"- Prior period wage revision amounts denied in earlier truing-up orders\n\n"
                f"IMPORTANT: Do NOT confuse general employee cost increases (medical, bonus, "
                f"increments, hiring) with wage revision. Only report if the petition explicitly "
                f"uses words like 'wage revision', 'pay revision', 'salary revision', 'pay commission', "
                f"'CDA', 'BPC', or 'pay arrears'.\n\n"
                f"Return JSON in this EXACT format:\n"
                f'{{"mentions_wage_revision": false, '
                f'"wage_revision_current_year_amount": 0.0, '
                f'"wage_revision_prior_period_amount": 0.0, '
                f'"total_wage_revision_claimed": 0.0}}\n\n'
                f"- mentions_wage_revision: Set to true ONLY if the petition explicitly mentions "
                f"wage/pay revision with a specific amount. Set to false if no such claim.\n"
                f"- wage_revision_current_year_amount: Amount in Rs. Lakhs for FY {fy}. Use 0.0 if not claimed.\n"
                f"- wage_revision_prior_period_amount: Amount in Rs. Lakhs from previous years. Use 0.0 if not claimed.\n"
                f"- total_wage_revision_claimed: Sum of current + prior. Use 0.0 if none.\n\n"
                f"DO NOT hallucinate amounts. If unsure, return all zeros with mentions_wage_revision=false.\n"
                f"Return ONLY valid JSON. No markdown. No explanation."
            )
            # Use all PDFs — wage revision may be in any annexure
            wage_pdf_path = all_pdf_paths if len(all_pdf_paths) > 1 else pdf_path
            raw_wage = _gen_pdf(
                pdf_path=wage_pdf_path,
                prompt=wage_prompt,
                model=GEMINI_MODEL,
                temperature=0.0,
                response_mime_type="application/json",
            )
            if not raw_wage:
                logger.warning("[Wage Revision] Gemini returned empty response")
                raise ValueError("Empty Gemini response")
            logger.info(f"[Wage Revision] Gemini raw response: {raw_wage[:300]}")
            wage_data = json.loads(raw_wage.strip())
            
            # Only apply if petition explicitly mentions wage revision
            mentions_wr = wage_data.get("mentions_wage_revision", False)
            if not mentions_wr:
                logger.info("[Wage Revision] Gemini confirms: petition does NOT mention wage/pay revision — no wage revision applied")
            else:
                wr_prior = float(wage_data.get("wage_revision_prior_period_amount", 0) or 0)
                wr_current = float(wage_data.get("wage_revision_current_year_amount", 0) or 0)
                wr_total = float(wage_data.get("total_wage_revision_claimed", 0) or 0)
                
                if wr_prior > 0:
                    wage_revision_prior = wr_prior
                    logger.info(f"[Wage Revision] Focused extraction: prior period = Rs.{wr_prior:.2f}L")
                if wr_current > 0:
                    wage_revision_current = wr_current
                    logger.info(f"[Wage Revision] Focused extraction: current year = Rs.{wr_current:.2f}L")
                if wr_total > 0:
                    logger.info(f"[Wage Revision] Total claimed: Rs.{wr_total:.2f}L")
        except Exception as e:
            logger.warning(f"[Wage Revision] Focused extraction failed: {e}")

    if wage_revision_current > 0.0:
        enrichments["wage_revision_current_year"] = wage_revision_current
        logger.info(f"Wage revision (current year): Rs.{wage_revision_current:.2f}L → state")
    if wage_revision_prior > 0.0:
        enrichments["wage_revision_prior_period"] = wage_revision_prior
        logger.info(f"Wage revision (prior period): Rs.{wage_revision_prior:.2f}L → state")

    # ── Phase 4: Focused R&M line item extraction from PDF ──────────────
    # Extract individual R&M expenditure items for one-time classification.
    # Like wage revision (Source 3), this uses a focused Gemini PDF call
    # rather than relying on the massive deep extraction prompt.
    # The auditor uses these items to classify one-time vs routine expenses
    # per KSERC Regulation 80(3).
    existing_rm_items = state.get("rm_line_items", [])
    if not existing_rm_items:
        logger.info("[R&M Items] No R&M line items in state, trying focused Gemini extraction...")
        try:
            from src.gemini_client import generate_with_pdf as _gen_pdf_rm
            rm_prompt = (
                f"Extract ALL individual Repairs & Maintenance (R&M) expenditure line items "
                f"from this petition for {licensee} FY {fy}.\n\n"
                f"Look for tables or paragraphs listing R&M items such as:\n"
                f"  - Transformer repairs/replacements\n"
                f"  - Cable repairs/laying\n"
                f"  - Substation maintenance\n"
                f"  - Testing and inspection\n"
                f"  - Annual maintenance contracts (AMC)\n"
                f"  - Electrical equipment servicing\n"
                f"  - Building repairs\n"
                f"  - Road/civil works\n"
                f"  - Any other R&M items with individual amounts\n\n"
                f"For each item, also classify it as:\n"
                f"  - CAPITAL_EXPENDITURE: Creates/replaces a long-life physical component\n"
                f"  - ONE_TIME_RM: Genuine one-time non-recurring repair/restoration\n"
                f"  - ROUTINE_RM: Recurring maintenance already in annual O&M norm\n\n"
                f"Return a JSON array of objects. Each object must have:\n"
                f'  "description": string (the R&M item description),\n'
                f'  "amount": number (amount in Rs. Lakhs),\n'
                f'  "classification": "CAPITAL_EXPENDITURE" | "ONE_TIME_RM" | "ROUTINE_RM",\n'
                f'  "reason": string (one-line reason for classification)\n\n'
                f"If no individual line items can be found, return an empty array [].\n"
                f"Do NOT include the total R&M amount as a line item.\n"
                f"Return ONLY the JSON array, no other text."
            )
            raw_rm = _gen_pdf_rm(
                pdf_path=pdf_path,
                prompt=rm_prompt,
                model=GEMINI_MODEL,
                temperature=0.0,
                response_mime_type="application/json",
            )
            if not raw_rm:
                logger.warning("[R&M Items] Gemini returned empty response")
                raise ValueError("Empty Gemini response")
            rm_items = json.loads(raw_rm.strip())
            if isinstance(rm_items, list) and len(rm_items) > 0:
                enrichments["rm_line_items"] = rm_items
                total_rm = sum(i.get("amount", 0) for i in rm_items)
                logger.info(
                    f"[R&M Items] Focused extraction: {len(rm_items)} items, "
                    f"total Rs.{total_rm:.2f}L"
                )
                for item in rm_items:
                    logger.info(f"  - {item.get('description', '?')}: Rs.{item.get('amount', 0):.2f}L")
            else:
                logger.info("[R&M Items] Focused extraction: no individual line items found")
        except Exception as e:
            logger.warning(f"[R&M Items] Focused extraction failed: {e}")

    return {
        "detailed_tables": result,
        **enrichments,
    }
