"""
KSERC Cross-Licensee Learning & Norm Extractor — Gemini-powered
=================================================================

WHAT THIS MODULE DOES:
1. Learns KSERC methodology from ALL past orders (every licensee)
2. Extracts the correct "Revised ARR&ERC Approved" benchmarks
3. Studies regulations, amendments, and interim orders

CRITICAL: When extracting numbers from tables, this module ALWAYS:
- Identifies all column headers FIRST
- Reads from the "Revised ARR&ERC Approved" column specifically
- Cross-validates to ensure we're NOT reading MYT or Claimed columns

Data sources (in priority order):
1. ALL past truing-up orders — KSERC methodology patterns across ALL licensees
2. The petition's own Annex B — "Revised ARR&ERC Approved" column
3. MYT Order — original control period norms (fallback)
4. Regulations + all 3 Amendments + Interim Orders
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.config import GEMINI_MODEL

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Licensee → Reference Document mapping
# ═══════════════════════════════════════════════════════════════════════

MYT_ORDER_FILES = {
    "kdhp": "Kannan Devan Hills Plantations MYT Order 26-11-25.pdf",
    "kannan": "Kannan Devan Hills Plantations MYT Order 26-11-25.pdf",
    "infopark": "Infopark MYT Order (OP 09 2023).pdf",
    "technopark": "Technopark MYT Order OP 12 2023.pdf",
    "cseza": "CSEZA MYT Order 19 1 24.pdf",
    "cochin special": "CSEZA MYT Order 19 1 24.pdf",
}

PAST_ORDER_FILES = {
    "kdhp": [
        "Kannan Devan Hills Plantations Company FY 2022-23 Truing Up Order.pdf",
        "Kannan Devan Hills Plantations Company FY 2021-22 Truing Up Order.pdf",
        "KANNADEVAN 2023-24.pdf",
    ],
    "kannan": [
        "Kannan Devan Hills Plantations Company FY 2022-23 Truing Up Order.pdf",
        "Kannan Devan Hills Plantations Company FY 2021-22 Truing Up Order.pdf",
        "KANNADEVAN 2023-24.pdf",
    ],
    "infopark": [
        "Infopark True-Up 2022-23 (OP 82 2023).pdf",
    ],
    "technopark": [
        "Technopark True-Up 2022-23 (OP 84 2023).pdf",
    ],
    "cseza": [
        "Cochin Special Economic Zone Authority FY 2020-21 Truing Up Order.pdf",
        "Cochin Special Economic Zone Authority FY 2019-20 Truing Up Order.pdf",
        "Cochin Special Economic Zone Authority FY 2018-19 Truing Up Order.pdf",
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# Step 0: Learn KSERC Methodology from ALL Past Orders
# ═══════════════════════════════════════════════════════════════════════

def _learn_kserc_methodology(
    licensee_name: str,
    financial_year: str,
) -> Dict[str, Any]:
    """
    Study ALL past orders (every licensee), regulations, and amendments
    to learn KSERC's consistent decision methodology.

    This queries:
    - past_orders (Technopark, Infopark, CSEZA, KDHP truing-up orders)
    - other_licensee_orders (Rubberpark, Cochin Port, Thrissur, KINESCO, Smart City, KSEBL)
    - regulations (Tariff Regulations 2021 + all 3 amendments)
    - myt_orders (all MYT orders for methodology understanding)

    Returns a methodology dict with rules for each expense component.
    """
    try:
        from src.rag.file_search_store import query_regulations
    except ImportError:
        logger.warning("file_search_store not available for methodology learning")
        return {}

    prompt = f"""You are studying ALL KSERC (Kerala State Electricity Regulatory Commission) past truing-up orders, 
regulations, MYT orders, and amendments to learn the Commission's EXACT methodology for auditing each expense component.

Study ALL the past truing-up orders available (for ALL licensees — Technopark, Infopark, CSEZA, KDHP, 
Rubberpark, Cochin Port, Thrissur Corporation, KINESCO, Smart City, KSEBL), along with the Tariff 
Regulations 2021. Also analyze the First Amendment (2023), Second Amendment (2024), and Third Amendment (2025)
to understand any methodology changes.

For the licensee "{licensee_name}" FY {financial_year}, extract the EXACT methodology KSERC uses for EACH component.

Return a JSON object with this structure:
{{
    "employee_cost": {{
        "method": "<exact methodology — e.g., 'MYT base year norm × actual CPI(70%)+WPI(30%) inflation'>",
        "regulation_clause": "<clause number from Tariff Regulations 2021>",
        "amendment_changes": "<any changes from amendments, or 'none'>",
        "past_pattern": "<what KSERC did in past orders — e.g., 'always caps at inflation-escalated norm, no exceptions'>"
    }},
    "repair_maintenance": {{
        "method": "<exact methodology>",
        "regulation_clause": "<clause>",
        "amendment_changes": "<changes or 'none'>",
        "past_pattern": "<pattern>",
        "one_time_expense_rule": "<how KSERC handles one-time R&M expenses>"
    }},
    "admin_general": {{
        "method": "<exact methodology>",
        "regulation_clause": "<clause>",
        "amendment_changes": "<changes or 'none'>",
        "past_pattern": "<pattern>",
        "bee_audit_fee_rule": "<how KSERC handles BEE energy audit fee — added as change-in-law?>"
    }},
    "depreciation": {{
        "method": "<exact methodology — SLM at what rate?>",
        "regulation_clause": "<clause>",
        "grant_deduction_rule": "<how grants/subsidies affect depreciation>",
        "surplus_asset_rule": "<how assets from accumulated surplus are treated>",
        "past_pattern": "<pattern>"
    }},
    "interest_long_term": {{
        "method": "<exact methodology — actual rate or normative?>",
        "regulation_clause": "<clause>",
        "normative_loan_rule": "<70:30 equity:debt split rule>",
        "no_loan_rule": "<what happens if licensee has no actual loan portfolio>"
    }},
    "interest_consumer_deposits": {{
        "method": "<exact methodology — SBI rate as of which date?>",
        "regulation_clause": "<clause>",
        "past_pattern": "<pattern>"
    }},
    "interest_working_capital": {{
        "method": "<exact methodology>",
        "regulation_clause": "<clause>",
        "negative_wc_rule": "<what happens if working capital is negative>"
    }},
    "return_on_nfa": {{
        "method": "<exact methodology — rate? on what base?>",
        "regulation_clause": "<clause>",
        "equity_identifiable_rate": "<rate when equity is identifiable>",
        "equity_not_identifiable_rate": "<rate when equity is NOT identifiable>",
        "grant_deduction_rule": "<how grants affect RoNFA base>",
        "surplus_asset_rule": "<how surplus-funded assets are treated>"
    }},
    "power_purchase_cost": {{
        "method": "<exact methodology for distribution loss adjustment>",
        "regulation_clause": "<clause for distribution loss>",
        "excess_loss_penalty": "<formula for excess distribution loss>",
        "efficiency_gain_sharing": "<2:1 gain sharing rule>",
        "kseb_verification": "<how KSERC verifies PPC against KSEB records>"
    }},
    "section3_1_duty": {{
        "method": "<always disallow — cite exact reasoning>",
        "regulation_clause": "<Kerala Electricity Duty Act reference>",
        "past_pattern": "<consistent across ALL orders>"
    }},
    "carrying_cost": {{
        "method": "<approve as claimed or recalculate?>",
        "regulation_clause": "<clause>",
        "past_pattern": "<pattern>"
    }},
    "other_debits": {{
        "method": "<methodology>",
        "provision_doubtful_debts_rule": "<always disallowed unless written off>",
        "bank_guarantee_rule": "<legal charges against KSERC — disallowed>",
        "inspection_charges_rule": "<periodical inspection — approved>"
    }},
    "non_tariff_income": {{
        "method": "<how KSERC treats NTI — imputed or actual?>",
        "regulation_clause": "<clause>",
        "imputed_interest_rule": "<does KSERC impute interest on accumulated surplus?>"
    }},
    "inflation_escalation": {{
        "formula": "<CPI weight and WPI weight>",
        "cpi_weight_pct": 70,
        "wpi_weight_pct": 30,
        "regulation_clause": "<Annexure-7 reference>",
        "amendment_changes": "<any changes in amendments>"
    }},
    "o_and_m_general_rule": {{
        "description": "<overall O&M norm methodology from Tariff Regulations>",
        "controllable_vs_uncontrollable": "<classification>",
        "escalation_method": "<how base year O&M is escalated>"
    }}
}}

CRITICAL INSTRUCTIONS:
- Study ALL orders for ALL licensees, not just {licensee_name}
- Include specific regulation clause numbers
- Note any differences in treatment between SDL licensees vs KSEBL
- Note any changes introduced by the amendments
- Return ONLY the JSON object, no other text
"""

    try:
        result = query_regulations(
            prompt,
            categories=["past_orders", "other_licensee_orders", "regulations", "myt_orders"],
            model=GEMINI_MODEL,
        )
        parsed = _parse_json_response(result, "KSERC Methodology")
        if parsed:
            logger.info(f"Learned KSERC methodology: {len(parsed)} component rules extracted")
            for k, v in parsed.items():
                if isinstance(v, dict):
                    method = v.get("method", v.get("description", v.get("formula", "?")))
                    logger.info(f"  {k}: {str(method)[:100]}")
                else:
                    logger.info(f"  {k}: {str(v)[:100]}")
        return parsed
    except Exception as e:
        logger.error(f"Methodology learning failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════
# Main extraction function
# ═══════════════════════════════════════════════════════════════════════

def extract_myt_norms(
    licensee_name: str,
    financial_year: str,
    petition_annexures: list = None,
) -> Dict[str, Any]:
    """
    Extract audit benchmarks by studying ALL past orders and regulations.

    Priority (HARDCODED JSON IS PRIMARY — Gemini CANNOT override):
    0. LOAD hardcoded myt_baselines.json as the AUTHORITATIVE numeric source
    1. LEARN methodology from ALL past orders across ALL licensees (Gemini)
    2. Licensee justifications vs KSERC past responses (Gemini)
    3. Gemini queries fill ONLY gaps not covered by hardcoded JSON
    """
    logger.info(f"=== Cross-Licensee Learning & Norm Extraction: {licensee_name} FY {financial_year} ===")

    from concurrent.futures import ThreadPoolExecutor, as_completed
    import json as _json
    from pathlib import Path

    result: Dict[str, Any] = {}

    # ══════════════════════════════════════════════════════════════════
    # STEP 0 (PRIMARY): Load hardcoded myt_baselines.json
    # These values are AUTHORITATIVE and CANNOT be overridden by Gemini
    # ══════════════════════════════════════════════════════════════════
    hardcoded_norms = {}
    try:
        baselines_path = Path(__file__).resolve().parents[2] / "data" / "myt_baselines" / "myt_baselines.json"
        with open(baselines_path, "r", encoding="utf-8") as f:
            all_baselines = _json.load(f)
        # Find the matching licensee (case-insensitive substring match)
        for lic_key, lic_data in all_baselines.items():
            if lic_key.lower() in licensee_name.lower() or licensee_name.lower() in lic_key.lower():
                year_data = lic_data.get("baselines", {}).get(financial_year, {})
                if year_data:
                    for k, v in year_data.items():
                        if isinstance(v, (int, float)) and not k.startswith("_"):
                            hardcoded_norms[k] = float(v)
                            result[k] = float(v)
                    logger.info(f"[PRIMARY] Loaded {len(hardcoded_norms)} hardcoded norms from myt_baselines.json for {lic_key} FY {financial_year}")
                    for k, v in sorted(hardcoded_norms.items()):
                        logger.info(f"  [HARDCODED] {k}: {v}")
                else:
                    logger.warning(f"No baselines found in myt_baselines.json for {lic_key} FY {financial_year}")
                break
    except Exception as e:
        logger.error(f"Failed to load myt_baselines.json: {e}")

    # ══════════════════════════════════════════════════════════════════
    # STEP 1: Run Gemini queries for METHODOLOGY and JUSTIFICATIONS
    # (These provide non-numeric context that hardcoded JSON cannot)
    # ══════════════════════════════════════════════════════════════════
    logger.info("[MYT PARALLEL] Running methodology + justification queries...")

    def _step0_methodology():
        return ("methodology", _learn_kserc_methodology(licensee_name, financial_year))

    def _step1_annex_b():
        return ("annex_norms", _query_petition_arr_erc(licensee_name, financial_year, petition_annexures))

    def _step2_precedents():
        return ("past_norms", _query_cross_licensee_precedents(licensee_name, financial_year))

    def _step3_myt_order():
        return ("myt_norms", _query_myt_order_norms(licensee_name, financial_year))

    parallel_results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(_step0_methodology),
            executor.submit(_step1_annex_b),
            executor.submit(_step2_precedents),
            executor.submit(_step3_myt_order),
        ]
        for future in as_completed(futures):
            try:
                key, data = future.result()
                parallel_results[key] = data
                logger.info(f"  [MYT PARALLEL] {key} done")
            except Exception as e:
                logger.error(f"  [MYT PARALLEL] query failed: {e}")

    # ── Merge parallel results — ONLY for values NOT in hardcoded JSON ──
    # Step 0: Methodology (always store — non-numeric)
    methodology = parallel_results.get("methodology")
    if methodology:
        result["_methodology_rules"] = methodology
        logger.info(f"Methodology rules learned from ALL past orders: {len(methodology)} components")

    # Step 1: Annex B — fill ONLY gaps not covered by hardcoded JSON
    annex_norms = parallel_results.get("annex_norms")
    if annex_norms:
        filled = 0
        for k, v in annex_norms.items():
            if not k.startswith("_") and k not in hardcoded_norms:
                result[k] = v
                filled += 1
                logger.info(f"Annex B (gap-fill): {k} = {v}")
            elif not k.startswith("_") and k in hardcoded_norms:
                logger.info(f"Annex B SKIPPED (hardcoded exists): {k} = {v} (keeping hardcoded {hardcoded_norms[k]})")
        logger.info(f"Annex B: {filled} gap-fill values used, {len(annex_norms) - filled} skipped (hardcoded)")

    # Step 2: Cross-licensee precedents (fill gaps only, never override hardcoded)
    past_norms = parallel_results.get("past_norms")
    if past_norms:
        for key, val in past_norms.items():
            if not key.startswith("_") and key not in hardcoded_norms and (key not in result or result.get(key, 0.0) == 0.0):
                result[key] = val
                logger.info(f"Cross-licensee precedent (gap-fill): {key} = {val}")

    # Step 3: MYT order norms (fill gaps only, never override hardcoded)
    myt_norms = parallel_results.get("myt_norms")
    if myt_norms:
        for key, val in myt_norms.items():
            if not key.startswith("_") and key not in hardcoded_norms and (key not in result or result.get(key, 0.0) == 0.0):
                result[key] = val
                logger.info(f"MYT norm (gap-fill): {key} = {val}")

    # ── Step 4: Amendments — never override hardcoded norms ────────
    amendment_rules = _query_all_regulations_and_amendments(licensee_name, financial_year)
    if amendment_rules:
        for key, val in amendment_rules.items():
            if not key.startswith("_") and isinstance(val, (int, float)) and val > 0:
                if key not in hardcoded_norms:
                    old = result.get(key, 0.0)
                    result[key] = val
                    if isinstance(old, (int, float)) and old > 0:
                        logger.info(f"Amendment override (gap-fill): {key} = {val} (was {old})")
                else:
                    logger.info(f"Amendment SKIPPED (hardcoded exists): {key} = {val} (keeping hardcoded {hardcoded_norms[key]})")

    # ── Step 5: Justification analysis ──
    justification_analysis = _analyze_licensee_justifications(licensee_name, financial_year)
    if justification_analysis:
        result["_justification_analysis"] = justification_analysis
        logger.info(f"Justification analysis completed: {len(justification_analysis)} components analyzed")
        if "_methodology_rules" in result:
            result["_methodology_rules"]["_justification_responses"] = justification_analysis

    logger.info(f"Final norms for {licensee_name} FY {financial_year}: "
                f"{sum(1 for k,v in result.items() if not k.startswith('_') and isinstance(v, (int,float)) and v > 0)} numeric values")
    for k, v in sorted(result.items()):
        if not k.startswith("_") and isinstance(v, (int, float)) and v > 0:
            source = "[HARDCODED]" if k in hardcoded_norms else "[GEMINI]"
            logger.info(f"  {source} {k}: {v}")

    return result


# ═══════════════════════════════════════════════════════════════════════
# Step 1: Query Petition's Annex B — PRECISE Column Reading
# ═══════════════════════════════════════════════════════════════════════

def _query_petition_arr_erc(
    licensee_name: str,
    financial_year: str,
    petition_annexures: list = None,
) -> Dict[str, float]:
    """
    Extract Revised ARR&ERC Approved values from the petition's Annex B.

    CRITICAL: Uses a two-step prompt to ensure correct column reading:
    1. First identify ALL column headers in the ARR table
    2. Then extract ONLY from the "Revised ARR&ERC Approved" column
    """
    try:
        from src.rag.file_search_store import query_regulations
    except ImportError:
        logger.warning("file_search_store not available")
        return {}

    prompt = f"""TASK: Extract the "Revised ARR&ERC Approved" values from the petition for {licensee_name} FY {financial_year}.

STEP 1 — COLUMN IDENTIFICATION:
First, find the ARR-ERC (Annual Revenue Requirement & Expected Revenue from Charges) table in the petition.
List ALL column headers you see in this table. Typical columns include:
- "MYT Approved" or "MYT Order" (original multi-year tariff projection — DO NOT use this)
- "Revised ARR&ERC Approved" or "Approved ARR" or "KSERC Approved" (Commission's approved amount — USE THIS)
- "Actual" or "Claimed" or "Petition" or "Truing Up" (licensee's claimed amount — DO NOT use this)

STEP 2 — CORRECT COLUMN EXTRACTION:
Extract values ONLY from the "Revised ARR&ERC Approved" column.

⚠️ COLUMN VERIFICATION:
- The "Revised ARR&ERC Approved" values should generally be BETWEEN the MYT values and the Claimed values
- If the values you extract are very close to or exactly match the "Claimed" column → you are reading the WRONG column
- If the values you extract exactly match the "MYT Approved" column → you are reading the WRONG column
- For O&M components (employee, R&M, A&G): Revised Approved is typically LOWER than Claimed but may be slightly higher than MYT
- For PPC: Revised Approved can be higher or lower than Claimed depending on distribution loss adjustment

Return JSON with these keys (all values in Rs. Lakhs):
{{
    "column_headers_found": ["<list all column headers you found>"],
    "column_used": "<exact name of the column you are reading from>",
    "employee_cost": <Revised ARR Approved employee cost>,
    "repair_maintenance": <Revised ARR Approved R&M>,
    "admin_general": <Revised ARR Approved A&G>,
    "depreciation": <Revised ARR Approved depreciation>,
    "interest_long_term": <Revised ARR Approved interest on loans>,
    "interest_consumer_deposits": <Revised ARR Approved interest on consumer deposits>,
    "interest_working_capital": <Revised ARR Approved interest on working capital>,
    "return_on_nfa": <Revised ARR Approved return on NFA>,
    "carrying_cost": <Revised ARR Approved carrying cost>,
    "other_debits": <Revised ARR Approved other debits>,
    "power_purchase_cost": <Revised ARR Approved PPC>,
    "target_distribution_loss_pct": <approved distribution loss target %>,
    "total_arr": <total Revised ARR>,
    "gross_fixed_assets": <GFA if mentioned>,
    "net_fixed_assets": <NFA if mentioned>,
    "grants_subsidies": <grants/subsidies if mentioned>,
    "normative_loan": <normative loan if mentioned>,
    "avg_power_purchase_cost_rs_per_kwh": <avg PPC rate Rs/kWh>
}}

IMPORTANT:
- Use 0.0 for values not found
- Return ONLY the JSON object, no other text
"""

    try:
        result = query_regulations(
            prompt,
            categories=["myt_orders", "past_orders", "regulations"],
            model=GEMINI_MODEL,
        )
        parsed = _parse_json_response(result, "Revised ARR&ERC")
        
        # Log which column was used for verification
        col_used = parsed.pop("column_used", "unknown")
        col_headers = parsed.pop("column_headers_found", [])
        if col_used:
            logger.info(f"Column used for extraction: '{col_used}'")
        if col_headers:
            logger.info(f"Column headers found: {col_headers}")
        
        return parsed
    except Exception as e:
        logger.error(f"Revised ARR&ERC query failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════
# Step 2: Cross-Licensee Precedent Learning
# ═══════════════════════════════════════════════════════════════════════

def _query_cross_licensee_precedents(
    licensee_name: str,
    financial_year: str,
) -> Dict[str, float]:
    """
    Query ALL past truing-up orders across ALL licensees for:
    1. KSERC-approved amounts for this specific licensee
    2. Methodology patterns from other licensees (for cross-validation)
    
    Queries: past_orders + other_licensee_orders categories
    """
    try:
        from src.rag.file_search_store import query_regulations
    except ImportError:
        return {}

    try:
        parts = financial_year.split("-")
        prev_start = int(parts[0]) - 1
        prev_end = int(parts[1]) - 1
        prev_fy = f"{prev_start}-{prev_end:02d}"
    except (ValueError, IndexError):
        prev_fy = financial_year

    prompt = f"""Study ALL past Truing-Up Orders available — for EVERY licensee 
(Technopark, Infopark, CSEZA/Cochin SEZ, KDHP/Kannan Devan, Rubberpark, Cochin Port, 
Thrissur Corporation, KINESCO, Smart City, KSEBL).

I need TWO things:

PART A — SPECIFIC LICENSEE APPROVED AMOUNTS:
From past orders for "{licensee_name}", find the KSERC-APPROVED (NOT claimed) 
expense amounts from the most recent truing-up order (preferably FY {prev_fy} or earlier).
Look at the "Orders of the Commission" section or the final approved ARR/expenditure table.

⚠️ CRITICAL: Read the APPROVED column, NOT the Claimed/Petition column!
- The Approved amount is what KSERC allowed AFTER applying cuts
- It is typically LESS than the Claimed amount for O&M components
- Look for phrases like "the Commission hereby approves Rs. X lakh"

PART B — CROSS-LICENSEE METHODOLOGY PATTERNS:
From orders for OTHER licensees, identify consistent patterns:
- How does KSERC treat O&M expenses? (inflation-escalated norms?)
- How does KSERC handle one-time expenses vs recurring?
- Does KSERC treat all SDL licensees the same way?
- What are common disallowance patterns?

Return a JSON object with APPROVED amounts (Rs. Lakhs):
{{
    "employee_cost": <KSERC approved employee cost>,
    "repair_maintenance": <KSERC approved R&M>,
    "admin_general": <KSERC approved A&G>,
    "depreciation": <KSERC approved depreciation>,
    "interest_long_term": <KSERC approved interest on loans>,
    "interest_consumer_deposits": <KSERC approved interest on deposits>,
    "interest_working_capital": <KSERC approved IWC>,
    "return_on_nfa": <KSERC approved RoNFA>,
    "power_purchase_cost": <KSERC approved PPC>,
    "target_distribution_loss_pct": <distribution loss target used>,
    "actual_distribution_loss_pct": <actual distribution loss>,
    "total_approved_expenditure": <total approved expenditure>,
    "total_approved_revenue": <total approved revenue>,
    "revenue_gap_surplus": <revenue gap/surplus>,
    "source_fy": "<which FY this data is from>",
    "source_order": "<order number like OP XX/YYYY>"
}}

IMPORTANT:
- Use APPROVED amounts (what KSERC allowed), NOT the claimed amounts
- These are from the "Orders of the Commission" section
- Return ONLY the JSON object, no other text
"""

    try:
        result = query_regulations(
            prompt,
            categories=["past_orders", "other_licensee_orders"],
            model=GEMINI_MODEL,
        )
        return _parse_json_response(result, "Cross-Licensee Precedents")
    except Exception as e:
        logger.error(f"Cross-licensee precedent query failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════
# Step 3: Query MYT Order (Fallback)
# ═══════════════════════════════════════════════════════════════════════

def _query_myt_order_norms(
    licensee_name: str,
    financial_year: str,
) -> Dict[str, float]:
    """Query MYT Order for original control period norms (fallback only)."""
    try:
        from src.rag.file_search_store import query_regulations
    except ImportError:
        return {}

    licensee_lower = licensee_name.lower()
    myt_file = None
    for key, filename in MYT_ORDER_FILES.items():
        if key in licensee_lower:
            myt_file = filename
            break

    if not myt_file:
        logger.warning(f"No MYT Order found for licensee: {licensee_name}")
        return {}

    prompt = f"""From the MYT Order for {licensee_name} (file: {myt_file}), extract the 
KSERC-approved ARR figures for FY {financial_year}.

Look for the ARR table with columns for each year of the control period (2022-23 to 2026-27).

⚠️ CRITICAL — CORRECT COLUMN:
The MYT Order has multiple years as columns. Pick EXACTLY the column for FY {financial_year}.
Do NOT mix up years — each column has a specific year header.

Return a JSON object (all values in Rs. Lakhs):
{{
    "employee_cost": <MYT approved employee cost for {financial_year}>,
    "repair_maintenance": <MYT approved R&M for {financial_year}>,
    "admin_general": <MYT approved A&G for {financial_year}>,
    "depreciation": <MYT approved depreciation for {financial_year}>,
    "interest_long_term": <MYT approved interest on loans for {financial_year}>,
    "interest_consumer_deposits": <MYT approved interest on deposits for {financial_year}>,
    "interest_working_capital": <MYT approved IWC for {financial_year}>,
    "return_on_nfa": <MYT approved return on NFA for {financial_year}>,
    "other_debits": <MYT approved other debits for {financial_year}>,
    "power_purchase_cost": <MYT approved PPC for {financial_year}>,
    "target_distribution_loss_pct": <approved distribution loss target %>,
    "total_arr": <total ARR for {financial_year}>,
    "gross_fixed_assets": <GFA if mentioned>,
    "net_fixed_assets": <NFA if mentioned>,
    "grants_subsidies": <grants/subsidies if mentioned>,
    "normative_loan": <normative loan if mentioned>
}}

Return ONLY the JSON object, no other text.
"""

    try:
        result = query_regulations(
            prompt,
            categories=["myt_orders"],
            model=GEMINI_MODEL,
        )
        return _parse_json_response(result, "MYT Order")
    except Exception as e:
        logger.error(f"MYT Order query failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════
# Step 4: Query ALL Regulations, Amendments & Interim Orders
# ═══════════════════════════════════════════════════════════════════════

def _query_all_regulations_and_amendments(
    licensee_name: str,
    financial_year: str,
) -> Dict[str, Any]:
    """
    Check ALL regulations, amendments, and interim orders for methodology changes.
    
    Queries:
    - KSERC Tariff Regulations 2021 (base)
    - First Amendment, 2023
    - Second Amendment, 2024
    - Third Amendment, 2025
    - Interim Tariff Extension Order
    - Kerala Electricity Duty Act, 1963
    - Kerala Electricity Duty Rules, 1963
    - 2018 Tariff Regulations (for historical comparison)
    """
    try:
        from src.rag.file_search_store import query_regulations
    except ImportError:
        return {}

    prompt = f"""Study ALL KSERC regulatory documents thoroughly:

1. KSERC Tariff Regulations 2021 (base regulations)
2. First Amendment to Tariff Regulations (2023)
3. Second Amendment to Tariff Regulations (2024)
4. Third Amendment to Tariff Regulations (2025)
5. Interim Tariff Extension Order
6. Kerala Electricity Duty Act, 1963
7. Kerala Electricity Duty Rules, 1963

For {licensee_name} FY {financial_year}, identify:

A) ARE THERE ANY CHANGES from the base Tariff Regulations 2021 that affect:
   - O&M escalation methodology (CPI+WPI weights changed?)
   - Distribution loss target methodology
   - Depreciation rate or method
   - RoNFA rate
   - Interest rate methodology (EBLR changes?)
   - Any new provisions or removals

B) INTERIM TARIFF: Is there an interim tariff extension that affects this FY?

C) ELECTRICITY DUTY: What does Section 3(1) of the Kerala Electricity Duty Act say about
   passing duty to consumers? (Confirm: duty CANNOT be passed to consumers)

D) SPECIFIC NORMS for FY {financial_year}: If any amendment modifies specific numerical
   values for this year, extract them.

Return a JSON object with ONLY values actually CHANGED by amendments/regulations:
{{
    "employee_cost": <new norm if changed by amendment, else 0>,
    "repair_maintenance": <new norm if changed, else 0>,
    "admin_general": <new norm if changed, else 0>,
    "target_distribution_loss_pct": <new target if changed, else 0>,
    "depreciation_rate_pct": <new rate if changed, else 0>,
    "ronfa_rate_pct": <new RoNFA rate if changed, else 0>,
    "cpi_weight_pct": <CPI weight if changed from 70%, else 0>,
    "wpi_weight_pct": <WPI weight if changed from 30%, else 0>,
    "interim_tariff_applicable": <1 if interim tariff applies, else 0>,
    "section3_1_duty_passthrough_allowed": <0 means NOT allowed, as per Act>,
    "amendments_summary": "<summary of all changes that affect FY {financial_year}>"
}}

Use 0 for unchanged values. Return ONLY the JSON object, no other text.
"""

    try:
        result = query_regulations(
            prompt,
            categories=["regulations"],
            model=GEMINI_MODEL,
        )
        parsed = _parse_json_response(result, "Regulations & Amendments")
        # Filter to only numeric non-zero values (amendments_summary is string, keep it in methodology)
        numeric = {}
        for k, v in parsed.items():
            if isinstance(v, (int, float)) and v > 0:
                numeric[k] = float(v)
        return numeric
    except Exception as e:
        logger.error(f"Regulations & Amendments query failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════
# JSON parsing helper
# ═══════════════════════════════════════════════════════════════════════

def _parse_json_response(text: str, source: str) -> Dict[str, Any]:
    """Parse Gemini's JSON response, handling markdown code blocks and nested objects."""
    if not text:
        return {}

    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        clean = "\n".join(lines)

    try:
        data = json.loads(clean)
        result = {}
        for k, v in data.items():
            if isinstance(v, (int, float)):
                result[k] = float(v)
            elif isinstance(v, str):
                try:
                    result[k] = float(v.replace(",", ""))
                except ValueError:
                    result[k] = v  # Keep string values like source_fy, amendments_summary
            elif isinstance(v, dict):
                result[k] = v  # Keep nested dicts (methodology rules)
            elif isinstance(v, list):
                result[k] = v  # Keep lists (column headers)
        logger.info(f"Parsed {len(result)} values from {source} response")
        return result
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse {source} JSON: {e}")
        logger.debug(f"Raw response: {clean[:500]}")
        return {}


# ═══════════════════════════════════════════════════════════════════════
# Step 5: Read Licensee Justifications & Match KSERC Past Responses
# ═══════════════════════════════════════════════════════════════════════

def _analyze_licensee_justifications(
    licensee_name: str,
    financial_year: str,
) -> Dict[str, Any]:
    """
    Read the licensee's justifications from their petition AND compare them
    against how KSERC responded to similar justifications in past orders.
    
    This is critical because:
    - Licensees provide reasons for claiming certain amounts (e.g., "employee cost
      increased due to new campus hires", "R&M higher due to cable replacement")
    - KSERC has CONSISTENT patterns of accepting or rejecting specific justifications
    - Past truing-up orders document BOTH the justification AND KSERC's response
    
    Returns a dict mapping each component to:
    - licensee_justification: What the licensee said
    - kserc_past_response: How KSERC responded to similar justifications
    - likely_decision: What KSERC is likely to do based on precedent
    """
    try:
        from src.rag.file_search_store import query_regulations
    except ImportError:
        logger.warning("file_search_store not available for justification analysis")
        return {}

    prompt = f"""TASK: Analyze licensee justifications and KSERC's past responses.

You have access to the petition from {licensee_name} for FY {financial_year} AND all past
truing-up orders from ALL licensees.

PART A — LICENSEE JUSTIFICATIONS (from the current petition):
Read the petition for {licensee_name} FY {financial_year} and extract the JUSTIFICATIONS 
the licensee provides for each expense claim. Licensees typically explain:
- WHY their employee cost is higher than MYT norms (new hires, pay revision, new campus)
- WHY R&M expenses increased (one-time cable replacement, equipment upgrade, storm damage)
- WHY A&G is higher (legal fees, audit fees, BEE energy audit)
- WHY depreciation differs from MYT (new asset additions, funding source)
- WHY interest charges are claimed (new loans, working capital needs)
- WHAT items are included in Other Debits (Section 3(1) duty, provision for bad debts)

PART B — KSERC PAST RESPONSES (from ALL past truing-up orders):
For EACH justification the licensee provides, find how KSERC responded to SIMILAR 
justifications in past orders. Look at ALL licensees' past orders:

Examples of what to look for:
- When a licensee claimed higher employee cost due to new hires → Did KSERC accept it or 
  cap it at the inflation-escalated MYT norm?
- When a licensee claimed one-time R&M for cable replacement → Did KSERC approve the full 
  amount or only a portion?
- When a licensee included bank guarantee charges in A&G → Did KSERC allow it or disallow it?
- When a licensee claimed provision for doubtful debts → Did KSERC approve it or reject it?
- When a licensee claimed Section 3(1) duty as expense → Did KSERC allow passing it to consumers?
- When a licensee claimed higher depreciation due to new assets funded by surplus → Did KSERC 
  deduct surplus-funded assets from the depreciation base?

Return a JSON object:
{{
    "employee_cost": {{
        "licensee_justification": "<what the licensee says in the petition>",
        "kserc_past_response": "<how KSERC responded to similar justifications in past orders>",
        "past_order_reference": "<which order(s) this pattern is from>",
        "likely_decision": "<approve as claimed / cap at inflation norm / partially approve / disallow>",
        "reasoning": "<why KSERC would likely make this decision>"
    }},
    "repair_maintenance": {{
        "licensee_justification": "<justification>",
        "kserc_past_response": "<past response>",
        "past_order_reference": "<reference>",
        "likely_decision": "<decision>",
        "reasoning": "<reasoning>"
    }},
    "admin_general": {{
        "licensee_justification": "<justification>",
        "kserc_past_response": "<past response>",
        "past_order_reference": "<reference>",
        "likely_decision": "<decision>",
        "reasoning": "<reasoning>"
    }},
    "depreciation": {{
        "licensee_justification": "<justification>",
        "kserc_past_response": "<past response>",
        "past_order_reference": "<reference>",
        "likely_decision": "<decision>",
        "reasoning": "<reasoning>"
    }},
    "interest_long_term": {{
        "licensee_justification": "<justification>",
        "kserc_past_response": "<past response>",
        "past_order_reference": "<reference>",
        "likely_decision": "<decision>",
        "reasoning": "<reasoning>"
    }},
    "interest_working_capital": {{
        "licensee_justification": "<justification>",
        "kserc_past_response": "<past response>",
        "past_order_reference": "<reference>",
        "likely_decision": "<decision>",
        "reasoning": "<reasoning>"
    }},
    "return_on_nfa": {{
        "licensee_justification": "<justification>",
        "kserc_past_response": "<past response>",
        "past_order_reference": "<reference>",
        "likely_decision": "<decision>",
        "reasoning": "<reasoning>"
    }},
    "other_debits": {{
        "licensee_justification": "<justification — what items are included>",
        "kserc_past_response": "<past response — KSERC item-wise treatment>",
        "past_order_reference": "<reference>",
        "likely_decision": "<decision>",
        "reasoning": "<reasoning>"
    }},
    "section3_1_duty": {{
        "licensee_justification": "<justification — licensee argues it should be passed through>",
        "kserc_past_response": "<ALWAYS disallowed — cite exact past order reasoning>",
        "past_order_reference": "<reference>",
        "likely_decision": "disallow",
        "reasoning": "<Kerala Electricity Duty Act — cannot be passed to consumers>"
    }},
    "power_purchase_cost": {{
        "licensee_justification": "<justification — actual PPC claimed>",
        "kserc_past_response": "<how KSERC adjusts PPC for distribution loss target>",
        "past_order_reference": "<reference>",
        "likely_decision": "<decision>",
        "reasoning": "<reasoning>"
    }}
}}

IMPORTANT:
- Read the ACTUAL petition text for this licensee, not just numbers
- Match justifications against ALL past orders (every licensee)
- Be specific about which past orders you're referencing
- Return ONLY the JSON object, no other text
"""

    try:
        result = query_regulations(
            prompt,
            categories=["past_orders", "other_licensee_orders", "myt_orders", "regulations"],
            model=GEMINI_MODEL,
        )
        parsed = _parse_json_response(result, "Justification Analysis")
        if parsed:
            logger.info(f"Justification analysis completed for {len(parsed)} components")
            for comp, analysis in parsed.items():
                if isinstance(analysis, dict):
                    decision = analysis.get("likely_decision", "?")
                    justification = str(analysis.get("licensee_justification", "?"))[:60]
                    logger.info(f"  {comp}: '{justification}...' → KSERC likely: {decision}")
        return parsed
    except Exception as e:
        logger.error(f"Justification analysis failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════
# LangGraph Node Function
# ═══════════════════════════════════════════════════════════════════════

def myt_extract_node(state: dict) -> dict:
    """
    LangGraph node: Learn KSERC methodology from ALL past orders + extract benchmarks.

    This runs BEFORE the auditor, populating:
    - myt_baseline_norms: numeric benchmarks for capping
    - kserc_methodology_rules: methodology dict from ALL past orders
    - Justification analysis (stored inside methodology rules)

    Priority: Learn ALL orders → Revised ARR Approved → Past Precedent → MYT → Amendments → Justifications
    """
    licensee = state.get("licensee_name", "")
    fy = state.get("financial_year", "")
    annexures = state.get("annexure_pdf_paths", [])

    logger.info("=" * 60)
    logger.info("CROSS-LICENSEE LEARNING & NORM EXTRACTION")
    logger.info(f"Licensee: {licensee} | FY: {fy}")
    logger.info("Studying ALL past orders, regulations, amendments...")
    logger.info("Reading licensee justifications & matching KSERC responses...")
    logger.info("=" * 60)

    if not licensee or not fy:
        logger.warning("Missing licensee_name or financial_year in state")
        return {}

    try:
        all_data = extract_myt_norms(licensee, fy, annexures)
        
        if not all_data:
            logger.warning("No norms extracted — auditor will use fallbacks")
            return {}
        
        # Separate methodology rules from numeric norms
        methodology = all_data.pop("_methodology_rules", {})
        
        # Separate justification analysis
        justification_analysis = all_data.pop("_justification_analysis", {})
        
        # Build the numeric norms dict (only float values)
        norms = {}
        for k, v in all_data.items():
            if isinstance(v, (int, float)):
                norms[k] = float(v)
        
        result = {"myt_baseline_norms": norms}
        
        # Merge justification analysis into methodology rules
        if justification_analysis:
            methodology["_justification_responses"] = justification_analysis
            logger.info(f"Justification responses stored for {len(justification_analysis)} components:")
            for comp, analysis in justification_analysis.items():
                if isinstance(analysis, dict):
                    decision = analysis.get("likely_decision", "?")
                    justification = str(analysis.get("licensee_justification", "?"))[:80]
                    logger.info(f"  {comp}: '{justification}' → KSERC likely: {decision}")
        
        if methodology:
            result["kserc_methodology_rules"] = methodology
            logger.info(f"Methodology rules stored: {len(methodology)} components")
        
        logger.info(f"Numeric norms stored: {len(norms)} values")
        return result
        
    except Exception as e:
        logger.error(f"Cross-licensee learning failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════
# Reference Data Upload: Extract norms from an uploaded MYT/Interim PDF
# ═══════════════════════════════════════════════════════════════════════

MYT_NORMS_JSON_PATH = Path(__file__).resolve().parents[2] / "data" / "myt_baselines" / "myt_baselines.json"

_MYT_EXTRACT_PROMPT = """You are reading a KSERC (Kerala State Electricity Regulatory Commission) order document.
This may be a Multi-Year Tariff (MYT) Order, an Interim Tariff Order, or a Truing-Up Order.

Extract ALL financial norms and targets from this document into a structured table.

For EACH financial year covered in this document AND for EACH licensee mentioned, extract:
- All expense norms (employee cost, R&M, A&G, depreciation, interest, return on NFA, etc.)
- Distribution loss targets
- Average power purchase cost (Rs/kWh)
- Escalation rates (if mentioned)
- Control period information

Return a JSON object structured as:
{
  "document_type": "<MYT_ORDER | INTERIM_TARIFF | TRUING_UP_ORDER>",
  "order_number": "<e.g. OP 09/2023>",
  "control_period": "<e.g. 2022-2027>",
  "licensees": {
    "<LicenseeName>": {
      "escalation_rates": {
        "<year>": <rate_pct>
      },
      "baselines": {
        "<year e.g. 2024-25>": {
          "power_purchase_cost": <Rs Lakhs>,
          "employee_cost": <Rs Lakhs>,
          "repair_maintenance": <Rs Lakhs>,
          "admin_general": <Rs Lakhs>,
          "depreciation": <Rs Lakhs>,
          "interest_long_term": <Rs Lakhs>,
          "interest_consumer_deposits": <Rs Lakhs>,
          "interest_working_capital": <Rs Lakhs>,
          "carrying_cost": <Rs Lakhs>,
          "return_on_nfa": <Rs Lakhs>,
          "other_debits": <Rs Lakhs>,
          "target_distribution_loss_pct": <percent>,
          "avg_power_purchase_cost_rs_per_kwh": <rate>
        }
      }
    }
  },
  "extracted_rows": [
    {
      "field": "<human readable field name>",
      "licensee": "<licensee name>",
      "year": "<financial year>",
      "value": <numeric value>,
      "unit": "<Rs Lakhs | % | Rs/kWh>",
      "page": <page_number_if_known>
    }
  ]
}

IMPORTANT:
- Use 0.0 for values not found
- Include ALL years present in the document
- The extracted_rows array is the flat table for UI display
- Return ONLY the JSON, no other text
"""


def extract_from_uploaded_pdf(pdf_path: str) -> dict:
    """
    Extract MYT norms / financial data from an uploaded reference PDF
    using Gemini's direct PDF upload (NOT RAG — the PDF is new and not indexed yet).

    Returns:
        {
          "document_type": ...,
          "order_number": ...,
          "licensees": { LicenseeName: { "baselines": { year: {norms} } } },
          "extracted_rows": [ {field, licensee, year, value, unit, page}, ... ]
        }
    """
    try:
        from src.gemini_client import generate_with_pdf
    except ImportError:
        logger.error("gemini_client not available for PDF extraction")
        return {"error": "gemini_client not available", "extracted_rows": []}

    logger.info(f"Extracting norms from uploaded PDF: {pdf_path}")
    try:
        raw = generate_with_pdf(
            pdf_path=pdf_path,
            prompt=_MYT_EXTRACT_PROMPT,
            model=GEMINI_MODEL,
            temperature=0.0,
            response_mime_type="application/json",
        )
        result = _parse_json_response(raw, "PDF Reference Upload")
        if not result:
            return {"error": "Extraction returned empty result", "extracted_rows": []}

        # ALWAYS rebuild extracted_rows from licensees.baselines structure.
        # Gemini may return extracted_rows directly but they often lack field_key,
        # which is required by write_norms_to_json. Rebuilding guarantees consistency.
        if result.get("licensees"):
            result["extracted_rows"] = _build_extracted_rows(result)
        elif "extracted_rows" in result:
            # Gemini only returned flat rows without licensees structure — ensure field_key exists
            for row in result["extracted_rows"]:
                if "field_key" not in row and "field" in row:
                    # Convert human-readable "Employee Cost" → "employee_cost"
                    row["field_key"] = row["field"].lower().replace(" ", "_").replace("&", "and")

        logger.info(f"Extracted {len(result.get('extracted_rows', []))} rows from PDF")
        return result
    except Exception as e:
        logger.error(f"Reference PDF extraction failed: {e}")
        return {"error": str(e), "extracted_rows": []}


def _build_extracted_rows(data: dict) -> list:
    """Flatten the licensees.baselines structure into rows for UI display."""
    rows = []
    licensees = data.get("licensees", {})
    for licensee_name, lic_data in licensees.items():
        baselines = lic_data.get("baselines", {})
        for year, norms in baselines.items():
            for field, value in norms.items():
                if isinstance(value, (int, float)):
                    unit = "%" if "pct" in field or "loss" in field or "rate" in field else \
                           "Rs/kWh" if "rs_per_kwh" in field else "Rs Lakhs"
                    rows.append({
                        "field": field.replace("_", " ").title(),
                        "field_key": field,
                        "licensee": licensee_name,
                        "year": year,
                        "value": value,
                        "unit": unit,
                        "page": None,
                    })
    return rows


def write_norms_to_json(confirmed_rows: list, order_number: str = "",
                        control_period: str = "", document_type: str = "") -> dict:
    """
    Merge confirmed extracted rows into myt_baselines.json.

    Args:
        confirmed_rows: List of {field_key, licensee, year, value} dicts
                        (edited by the user in the UI before confirming).
        order_number: e.g. "OP 09/2023"
        control_period: e.g. "2022-2027"
        document_type: "MYT_ORDER" | "INTERIM_TARIFF" | "TRUING_UP_ORDER"

    Returns:
        {"status": "ok", "updated_entries": N} or {"error": ...}
    """
    try:
        # Load existing JSON
        if MYT_NORMS_JSON_PATH.exists():
            with open(MYT_NORMS_JSON_PATH, "r", encoding="utf-8") as f:
                baselines = json.load(f)
        else:
            baselines = {}

        updated = 0
        # Licensee name normalization: Gemini uses full names, baselines use short keys
        _LICENSEE_ALIASES = {
            "kdhp": "KDHP", "kannan": "KDHP", "kanan": "KDHP", "kdhpcl": "KDHP",
            "kannan devan": "KDHP", "kanan devan": "KDHP",
            "infopark": "Infopark",
            "technopark": "Technopark",
            "cseza": "CSEZA", "cochin special": "CSEZA", "cochin sez": "CSEZA",
        }

        def _normalize_licensee(name: str) -> str:
            """Map Gemini's long licensee names to short keys in myt_baselines.json."""
            lower = name.lower().strip()
            # Try exact match first
            for alias, short in _LICENSEE_ALIASES.items():
                if alias in lower:
                    return short
            # Also check if exact key already exists in baselines
            for existing_key in baselines:
                if existing_key.lower() == lower:
                    return existing_key
            return name  # fallback: use as-is

        for row in confirmed_rows:
            licensee = _normalize_licensee(row.get("licensee", "").strip())
            year = row.get("year", "").strip()
            field_key = row.get("field_key", "").strip()
            # Fallback: derive field_key from human-readable field name
            if not field_key and row.get("field"):
                field_key = row["field"].lower().strip().replace(" ", "_").replace("&", "and")
            value = row.get("value")

            if not (licensee and year and field_key and value is not None):
                continue

            # Create nested structure if missing
            if licensee not in baselines:
                baselines[licensee] = {
                    "control_period": control_period,
                    "myt_order": order_number,
                    "escalation_rates": {},
                    "baselines": {},
                }
            if "baselines" not in baselines[licensee]:
                baselines[licensee]["baselines"] = {}
            if year not in baselines[licensee]["baselines"]:
                baselines[licensee]["baselines"][year] = {}

            # Update the specific field
            baselines[licensee]["baselines"][year][field_key] = float(value)

            # Update metadata if provided
            if order_number:
                baselines[licensee]["myt_order"] = order_number
            if control_period:
                baselines[licensee]["control_period"] = control_period

            updated += 1

        # Write back
        with open(MYT_NORMS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(baselines, f, indent=2, ensure_ascii=False)

        logger.info(f"Updated myt_baselines.json: {updated} values written")
        return {"status": "ok", "updated_entries": updated}

    except Exception as e:
        logger.error(f"Failed to write norms to JSON: {e}")
        return {"error": str(e)}
