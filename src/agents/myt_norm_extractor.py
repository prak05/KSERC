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
            model="gemini-2.5-flash",
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

    Priority:
    0. LEARN methodology from ALL past orders across ALL licensees
    1. Petition's own Annex B — "Revised ARR&ERC Approved" column
    2. Past truing-up orders — KSERC's final approved amounts (ALL licensees)
    3. MYT Order — original control period norms (fallback)
    4. Regulations + Amendments — methodology overrides
    5. Licensee justifications vs KSERC past responses
    """
    logger.info(f"=== Cross-Licensee Learning & Norm Extraction: {licensee_name} FY {financial_year} ===")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    result: Dict[str, Any] = {}

    # ── Steps 0-3 run IN PARALLEL (independent queries) ─────────────
    logger.info("[MYT PARALLEL] Running Steps 0-3 in parallel (4 workers)...")

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

    # ── Merge parallel results (same priority order as before) ────────
    # Step 0: Methodology
    methodology = parallel_results.get("methodology")
    if methodology:
        result["_methodology_rules"] = methodology
        logger.info(f"Methodology rules learned from ALL past orders: {len(methodology)} components")

    # Step 1: Annex B (primary)
    annex_norms = parallel_results.get("annex_norms")
    if annex_norms:
        for k, v in annex_norms.items():
            if not k.startswith("_"):
                result[k] = v
        logger.info(f"Revised ARR&ERC Approved from Annex B: {len(annex_norms)} values")

    # Step 2: Cross-licensee precedents (fill gaps only)
    past_norms = parallel_results.get("past_norms")
    if past_norms:
        for key, val in past_norms.items():
            if not key.startswith("_") and (key not in result or result.get(key, 0.0) == 0.0):
                result[key] = val
                logger.info(f"Cross-licensee precedent: {key} = {val}")

    # Step 3: MYT order norms (fallback for gaps)
    myt_norms = parallel_results.get("myt_norms")
    if myt_norms:
        for key, val in myt_norms.items():
            if not key.startswith("_") and (key not in result or result.get(key, 0.0) == 0.0):
                result[key] = val
                logger.info(f"MYT norm (fallback): {key} = {val}")

    # ── Step 4: SEQUENTIAL — Amendments override earlier values ────────
    amendment_rules = _query_all_regulations_and_amendments(licensee_name, financial_year)
    if amendment_rules:
        for key, val in amendment_rules.items():
            if not key.startswith("_") and isinstance(val, (int, float)) and val > 0:
                old = result.get(key, 0.0)
                result[key] = val
                if isinstance(old, (int, float)) and old > 0:
                    logger.info(f"Amendment override: {key} = {val} (was {old})")

    # ── Step 5: SEQUENTIAL — Justification analysis depends on methodology ──
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
            logger.info(f"  {k}: {v}")

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
            model="gemini-2.5-flash",
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
            model="gemini-2.5-flash",
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
            model="gemini-2.5-flash",
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
            model="gemini-2.5-flash",
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
            model="gemini-2.5-flash",
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
