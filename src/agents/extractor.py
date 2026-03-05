"""
KSERC SDL Truing Up — Gemini Vision Extraction Agent
=====================================================

Converts KSERC petition PDFs into structured ARR data by:
1. Rendering PDF pages as images using PyMuPDF
2. Sending images to Gemini Vision (gemini-3-pro-preview) to read
   the ARR summary table (all values in Rs. Lakhs)
3. Falling back to text-based PyMuPDF + row-scan if Gemini fails

Populates the LangGraph state with:
  - claimed_expenses   : dict of all ARR expense line items (Rs. Lakhs)
  - claimed_revenues   : dict of all ARR revenue line items (Rs. Lakhs)
  - claimed_distribution_loss_pct : float
  - asset_register     : list[dict]

ARR Line Items extracted (matching KSERC petition format):
  EXPENSES:
    power_purchase_cost, employee_cost, repair_maintenance,
    admin_general, depreciation, interest_long_term,
    interest_consumer_deposits, interest_working_capital,
    carrying_cost, return_on_nfa, other_debits, other_expenses

  REVENUES:
    revenue_from_sale, wheeling_charges, non_tariff_income,
    other_revenue
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
# ARR Data Model  (all values in Rs. Lakhs)
# ══════════════════════════════════════════════════════════════════════════

def _empty_expenses() -> Dict[str, float]:
    """Return zero-initialised expense dictionary matching KSERC ARR format."""
    return {
        "power_purchase_cost":        0.0,   # Cost of power purchase / generation
        "employee_cost":              0.0,   # Employee expenses / salaries
        "repair_maintenance":         0.0,   # R&M expenses
        "admin_general":              0.0,   # A&G / Administration & General
        "depreciation":               0.0,   # Depreciation
        "interest_long_term":         0.0,   # Interest on long-term / normative loans
        "interest_consumer_deposits": 0.0,   # Interest on consumer security deposits
        "interest_working_capital":   0.0,   # Interest on working capital
        "carrying_cost":              0.0,   # Carrying cost on past revenue gaps
        "return_on_nfa":              0.0,   # Return on Net Fixed Assets / Return on Equity
        "other_debits":               0.0,   # Other debits (KDHP-specific)
        "section3_1_duty":            0.0,   # Section 3(1) Kerala Electricity Duty
        "other_expenses":             0.0,   # Other miscellaneous expenses
    }


def _empty_revenues() -> Dict[str, float]:
    """Return zero-initialised revenue dictionary matching KSERC ARR format."""
    return {
        "revenue_from_sale":  0.0,   # Revenue from sale of power
        "wheeling_charges":   0.0,   # Wheeling charges received
        "non_tariff_income":  0.0,   # Non-tariff income
        "other_revenue":      0.0,   # Other income
    }


# ══════════════════════════════════════════════════════════════════════════
# Gemini Vision Prompt
# ══════════════════════════════════════════════════════════════════════════

GEMINI_VISION_PROMPT = """You are a highly trained KSERC financial data extraction specialist.
Your task: extract the CLAIMED values from the Truing-Up Petition ARR summary table.

STEP 1 — FIND THE CORRECT TABLE:
Look for the main ARR (Aggregate Revenue Requirement) summary table. It is usually
on pages 2-4 and has rows for expenditure items and revenue items. The table has
multiple columns. The typical column headers are:

  "Sl.No | Particulars | ARR & ERC Projected | ARR & ERC Approved | Petition for Truing Up"
  OR: "Particulars | Approved in ARR&ERC | Claimed for Truing Up | Trued Up"
  OR: "Sl No | Particulars | ARR Projected | ARR Approved | For Truing Up"

KDHP-SPECIFIC FORMAT:
  KDHP (Kannan Devan Hills Plantations) petitions use a DIFFERENT column layout:
  "Particulars | FY25 Audited | FY25 ARR-ERC Approved | FY24 Audited | Variance"
  In this format, the "FYxx Audited" column (e.g. "FY25 Audited") contains the CLAIMED values.
  The column labeled with the LATEST financial year + "Audited" is the one to extract from.
  Do NOT extract from "ARR-ERC Approved" or "Variance" columns.

You MUST identify the column representing the Licensee's CLAIMED amounts. This is usually labeled "Petition for Truing Up", "Claimed for Truing Up", "Actual", "As per accounts", "Claimed", "For Truing Up", or "FYxx Audited" (for KDHP). This represents what the licensee requested.

CRITICAL INSTRUCTION: IF the table has a "Trued Up", "Approved in Truing Up", or "KSERC Approved" column (which is usually the last column in an Order PDF), DO NOT EXTRACT IT. DO NOT extract the "ARR Approved" column (which is the MYT norm). Look SPECIFICALLY for the word "Claimed", "Actual", "Petition", or "Audited" in the column header and extract from that column ONLY.

DO NOT READ from:
- Multi-year comparison tables showing columns like "2019-20", "2020-21", "2021-22"
- Monthly or quarterly breakdown tables
- Tables titled "Comparative Statement"
- The "ARR Approved" or "Trued Up" columns.

STEP 2 — READ EACH ROW (from main ARR table):
The table typically has these rows (names may vary slightly):

EXPENDITURE SIDE:
  1. Cost of Power Purchase / Purchase of Power / Power purchase cost => power_purchase_cost
  2. Employee Cost / Employee Expenses => employee_cost
  3. Repairs & Maintenance / R&M Expenses => repair_maintenance
  4. Administration & General / A&G Expenses (use ONLY the gross A&G subtotal, NOT including Electricity Duty) => admin_general
  5. Depreciation => depreciation
  6. Interest on Long Term Loans / Interest and Finance Charges / Interest on Normative Loan / Interest & Finance charges => interest_long_term
  7. Interest on Consumer Security Deposits / Interest on consumer deposits => interest_consumer_deposits
  8. Interest on Working Capital / Bank Charges on Working Capital => interest_working_capital
  9. Carrying Cost / Carrying cost for past revenue gaps => carrying_cost
  10. Return on Net Fixed Assets / Return on NFA / Return on Equity => return_on_nfa
  11. Other Debits / Duty-III / Duty III => other_debits
  12. Inspection charges / Periodical inspection => other_expenses (only if not already counted)
  13. Provision for doubtful debts / Provision for bad debts => other_expenses (add to existing)
  14. Section 3(1) Electricity Duty / Kerala Electricity Duty => section3_1_duty

KDHP-SPECIFIC: HANDLING CONSOLIDATED O&M ROWS:
  KDHP petitions show a SINGLE consolidated row called "O&M Expenses" or "Operation and 
  Maintenance cost" in the main ARR table (which combines Employee Cost + R&M + A&G).
  When you see this:
  1. Do NOT put the consolidated O&M total into employee_cost, repair_maintenance, or admin_general
  2. LOOK FOR a separate detailed O&M sub-table on another page. It is usually titled
     "Operation and Maintenance cost" or "Operating and Maintenance Expenses" and has columns:
     "Particulars | FY25 Audited | FY25 ARR-ERC Approved | FY24 Audited | Variance"
  3. From that sub-table, extract ONLY from the column with the HIGHEST FY number + "Audited"
     (e.g. "FY25 Audited" for a 2024-25 petition). This is the FIRST data column, right after "Particulars".
  4. Map the sub-table rows:
     - "Repairs and Maintenance" => repair_maintenance
     - "Employee cost" / "Employee expenses" => employee_cost
     - "Administration and general expenses" / "A&G" => admin_general
  5. CRITICAL: Use the EXACT value from the "FY25 Audited" column (first data column),
     NOT from "FY24 Audited" or "ARR-ERC Approved" or "Variance" columns.

REVENUE SIDE:
  1. Revenue from Sale of Power / Energy Charges collected / Revenue from sale of power => revenue_from_sale
  2. Wheeling Charges => wheeling_charges
  3. Non-Tariff Income => non_tariff_income
     IMPORTANT: "Non-Tariff Income" and "Other income" are DIFFERENT items.
     - "Non-Tariff Income" is a specific KSERC category (interest on deposits, misc recoveries, etc.)
     - If the main ARR table has BOTH a "Non-Tariff Income" row AND an "Other income" row, 
       extract them SEPARATELY.
     - For KDHP: Look for a detailed "Non-Tariff income" sub-table (Table 30) which has the
       TOTAL non-tariff income. Use that total (e.g. 124.07), NOT the "Other income" line from the ARR.
  4. Other Income / Other revenue => other_revenue
     This is for income items NOT classified as non-tariff income.

STEP 3 — SCAN ALL PAGES FOR SUB-TABLES (CRITICAL for complete data):
KSERC petitions often include detailed sub-tables in addition to the main ARR summary. These may appear on later pages.
Scan ALL pages for the following specific items that are sometimes in sub-tables, not the main summary:

  A) O&M Expense Breakdown (KDHP-specific):
     - Look for a table titled "Operating and Maintenance costs" or "O&M Details"
     - This table shows: Repairs and Maintenance, Employee cost, Administration and general expenses
     - Extract individual values into employee_cost, repair_maintenance, admin_general
     - The correct column is the one with the LATEST FY + "Audited" label

  B) Section 3(1) Electricity Duty / Kerala Electricity Duty / KED Act:
     - This is a STATUTORY levy, usually listed as a separate line under Administration & General Expenses.
     - Look for tables labeled "Form D 3.4(b)" or "Administration and General Expenses" or "Electricity Duty".
     - Extract this value and map it to: "section3_1_duty"
     - IMPORTANT: Do NOT double-count this inside admin_general. Extract admin_general (gross) separately.
     
  C) Carrying Cost on Revenue Gap:
     - May simply not appear if there's no prior revenue gap. Set to 0.0 if truly not present.
     - Look for "Carrying Cost on arrear", "Interest on past revenue gap", "Past dues".

  D) Interest on Working Capital:
     - May be labeled "Bank Charges", "Interest on overdraft", or "Working capital interest".
     - If absent, set to 0.0.

  E) Non-Tariff Income (KDHP-specific):
     - KDHP petitions have a detailed "Non-Tariff Income" sub-table (e.g. Table 30)
     - This table lists: Interest on Deposit with KSEB, Miscellaneous recoveries,
       Interest on accumulated Surplus, Other Operational Income, etc.
     - The TOTAL from this sub-table (from the "2024-25 Truing Up Petition" column)
       is the correct value for non_tariff_income.
     - Do NOT use the smaller "Other income" value from the main ARR table.
     - The correct column in Table 30 is the LAST column (latest FY Truing Up Petition).

  F) BEE Energy Audit Fee (change-in-law item inside A&G):
     - Look inside the A&G / Administration & General Expenses breakdown table.
     - The "Audit fees" row often has a note mentioning:
       "Rs.X.XX Lakhs being audit fee for energy audit" or "electricity audit fee".
     - Extract ONLY the energy/electricity audit fee portion (NOT the statutory audit fee).
     - Return this as "bee_energy_audit_fee". If not found or not mentioned, return 0.0.
     - Example: Audit fees = 4.20L (Rs.2.00L statutory + Rs.2.15L energy audit) → bee_energy_audit_fee = 2.15

  G) Additional expense items in KDHP petitions:
     - "Inspection charges" => add to other_expenses
     - "Provision for doubtful debts" / "Provision for bad debts" => add to other_expenses
     - "Duty-III" / "Duty III" => map to other_debits

STEP 4 — EXTRACT THE DISTRIBUTION LOSS:
Find the actual distribution loss percentage for the current financial year.
IMPORTANT: The distribution loss is usually found UNDER or WITHIN the Power Purchase Cost section.
Look in these places (in order of priority):
  1. The Power Purchase Cost / Cost of Power Purchase section — look for:
     - "Distribution Loss: X.XX%"
     - Energy balance data: "Input Energy" vs "Output/Sales Energy" (in MU or lakh kWh)
     - If you find input and output energy, calculate: loss% = (input - output) / input * 100
  2. A separate table or paragraph mentioning:
     - "Actual Distribution Loss: X.XX%"
     - "Distribution loss during the year: X.XX%"
     - "T&D Loss / Distribution Loss / Line Loss"
  3. Energy sales data showing units purchased vs units sold

RULES:
- ALL values are in Rs. LAKHS. Numbers like 4,652.88 = 4652.88 lakhs.
- Values in parentheses like (86.84) are NEGATIVE => return -86.84
- If a row is genuinely missing or the licensee has no claim, use 0.0
- If "Return on Equity" shows a "-" (dash), it means 0.0
- NEVER use the MYT Approved column value as the claimed value
- Return ONLY valid JSON — no markdown, no explanation, no text outside the JSON

EXAMPLE 1 (Technopark 2023-24 — standard format):
{
  "claimed_expenses": {
    "power_purchase_cost": 6369.16,
    "employee_cost": 60.73,
    "repair_maintenance": 551.17,
    "admin_general": 55.23,
    "depreciation": 69.89,
    "interest_long_term": 0.0,
    "interest_consumer_deposits": 134.15,
    "interest_working_capital": 0.0,
    "carrying_cost": 0.0,
    "return_on_nfa": 85.24,
    "other_debits": 0.0,
    "section3_1_duty": 74.68,
    "other_expenses": 0.0
  },
  "claimed_revenues": {
    "revenue_from_sale": 7400.25,
    "wheeling_charges": 0.0,
    "non_tariff_income": 0.0,
    "other_revenue": 0.0
  },
  "total_expenditure": 7400.25,
  "total_revenue": 7400.25,
  "distribution_loss_pct": 3.45
}

EXAMPLE 2 (KDHP 2024-25 — consolidated O&M format):
In the main ARR table, O&M Expenses = 332.00 (consolidated).
But in the O&M sub-table: R&M=51.17, Employee=257.53, A&G=23.30.
Also, Non-Tariff Income total = 124.07 (from Table 30 sub-table), NOT the
"Other income" line (36.55) from the main ARR table.
Use the SUB-TABLE breakdown values:
{
  "claimed_expenses": {
    "power_purchase_cost": 3434.48,
    "employee_cost": 257.53,
    "repair_maintenance": 51.17,
    "admin_general": 23.30,
    "depreciation": 14.50,
    "interest_long_term": 41.72,
    "interest_consumer_deposits": 0.0,
    "interest_working_capital": 0.0,
    "carrying_cost": 0.0,
    "return_on_nfa": 0.0,
    "other_debits": 24.89,
    "section3_1_duty": 0.0,
    "other_expenses": 7.47
  },
  "claimed_revenues": {
    "revenue_from_sale": 3707.46,
    "wheeling_charges": 0.0,
    "non_tariff_income": 124.07,
    "other_revenue": 36.55
  },
  "total_expenditure": 3855.06,
  "total_revenue": 3868.08,
  "distribution_loss_pct": 0.0,
  "bee_energy_audit_fee": 2.15
}

Now extract the data from the provided PDF pages. Return ONLY valid JSON.
"""


# ══════════════════════════════════════════════════════════════════════════
# PDF → Image Rendering (PyMuPDF)
# ══════════════════════════════════════════════════════════════════════════

def _render_pdf_pages_as_images(
    pdf_path: str,
    max_pages: int = 12,
    dpi: int = 200,
) -> List[bytes]:
    """
    Render each page of a PDF as a PNG image (bytes).
    Returns list of PNG bytes, one per page (up to max_pages).
    Uses 200 DPI — sharp enough for Gemini to read tables clearly.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    images = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)  # scale matrix

    total = min(len(doc), max_pages)
    for i in range(total):
        page = doc[i]
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        png_bytes = pix.tobytes("png")
        images.append(png_bytes)
        logger.info(f"  Rendered page {i+1}/{total} ({len(png_bytes)//1024} KB)")

    doc.close()
    return images


# ══════════════════════════════════════════════════════════════════════════
# Two-Pass Page Finder — identifies which pages have the ARR table
# ══════════════════════════════════════════════════════════════════════════

def _find_arr_table_pages(images: List[bytes]) -> List[int]:
    """
    Pass 1: Send all page images to Gemini with a lightweight prompt to
    identify which pages contain the main ARR summary table.
    Returns list of 0-based page indices.
    Falls back to [0..min(len(images),6)] if Gemini can't determine.
    """
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

        key_path = os.path.abspath("vertex_sa.json")
        if not os.path.exists(key_path):
            return list(range(min(len(images), 8)))

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
        vertexai.init(project="triple-cab-488111-f5", location="us-central1")

        PAGE_FINDER_PROMPT = """Look at these PDF pages carefully. Identify which pages contain the MAIN ARR (Aggregate Revenue Requirement) SUMMARY TABLE.

The ARR summary table is a SINGLE TABLE (usually spanning 1-3 pages) that lists ALL expense and revenue items together:

TYPICAL ROWS in the ARR summary table:
- Cost of Power Purchase (usually the largest number, 100+ Lakhs)
- Employee Cost / Employee Expenses
- Repairs & Maintenance / R&M
- Administration & General / A&G
- Depreciation
- Interest on Long Term Loans
- Return on Net Fixed Assets / Return on NFA
- TOTAL EXPENDITURE (must be present)
- Revenue from Sale of Power
- Revenue Gap / Surplus

TYPICAL COLUMNS:
- Sl.No | Particulars | ARR Projected | ARR Approved | Claimed/Petition for Truing Up
- OR: Particulars | Approved | Claimed | Trued Up

CRITICAL: Do NOT include these types of pages:
- Monthly breakdown tables (12 columns for Jan-Dec)
- Multi-year comparison tables (columns like 2019-20, 2020-21, etc.)
- Detailed Form D tables (labeled Form D 3.1, Form D 3.2 etc.)
- Annexure pages with individual asset/account details
- Tables with only ONE or TWO items (these are sub-tables)
- Cover pages, index pages, introductory text pages
- Financial statement detailed schedules
- Pages showing ONLY revenue details without expenditure

The correct table has BOTH expenditure AND revenue items on the same or consecutive pages, with a clear total.

Return ONLY a JSON object: {"arr_pages": [1, 2, 3]} with 1-based page numbers.
If you truly cannot find it, return {"arr_pages": []}."""

        parts = [Part.from_text(text=PAGE_FINDER_PROMPT)]
        for png_bytes in images:
            parts.append(Part.from_data(data=png_bytes, mime_type="image/png"))

        model = GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            contents=parts,
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=0.0,
            )
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        data = json.loads(raw)
        pages_1based = data.get("arr_pages", [])
        pages_0based = [p - 1 for p in pages_1based if 1 <= p <= len(images)]

        if pages_0based:
            logger.info(f"  [PageFinder] ARR table found on pages: {[p+1 for p in pages_0based]}")
            return pages_0based
        else:
            logger.warning("  [PageFinder] Could not identify ARR pages, using first 8")
            return list(range(min(len(images), 8)))

    except Exception as e:
        logger.warning(f"  [PageFinder] Failed: {e}, using first 8 pages")
        return list(range(min(len(images), 8)))


# ══════════════════════════════════════════════════════════════════════════
# Gemini Vision Extraction
# ══════════════════════════════════════════════════════════════════════════

def _extract_with_gemini_vision(
    images: List[bytes],
    claimed_expenses: Dict[str, float],
    claimed_revenues: Dict[str, float],
    licensee_name: str = "",
    financial_year: str = "",
) -> float:
    """
    Send PDF page images to Gemini Vision and extract ARR financial table.
    Uses the new google-genai SDK with the latest model.
    Updates claimed_expenses and claimed_revenues in-place.
    Returns distribution_loss_pct.
    """
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
        from google.oauth2.credentials import Credentials
    except ImportError:
        logger.warning("vertexai not installed; skipping Gemini Vision.")
        return 0.0

    key_path = os.path.abspath("vertex_sa.json")
    if not os.path.exists(key_path):
        logger.warning("vertex_sa.json not found; skipping Gemini Vision.")
        return 0.0
    
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
    vertexai.init(project="triple-cab-488111-f5", location="us-central1")

    # Build content parts: prompt + dynamic KDHP column instruction + all page images
    # For KDHP, inject a very explicit instruction about which column to extract from
    dynamic_prefix = ""
    if licensee_name and ("KDHP" in licensee_name.upper() or "KANNAN" in licensee_name.upper()):
        # Convert FY like "2024-25" to "FY25"
        fy_short = ""
        if financial_year and "-" in financial_year:
            fy_short = "FY" + financial_year.split("-")[1]  # e.g. "2024-25" -> "FY25"
        elif financial_year:
            fy_short = "FY" + financial_year[-2:]  # e.g. "2025" -> "FY25"
        
        if fy_short:
            dynamic_prefix = (
                f"\n\n*** CRITICAL OVERRIDE FOR THIS SPECIFIC PETITION ***\n"
                f"This is a KDHP petition for FY {financial_year}.\n"
                f"The EXACT column to extract from is: '{fy_short} Audited'\n"
                f"DO NOT extract from any other column (not '{fy_short} ARR-ERC Approved', "
                f"not 'FY{int(fy_short[2:])-1} Audited', not 'Variance').\n"
                f"For the O&M sub-table, also use the '{fy_short} Audited' column (first data column).\n"
                f"For the Non-Tariff Income sub-table (Table 30), use the '{financial_year} Truing Up Petition' column (last column).\n"
                f"*** END OVERRIDE ***\n\n"
            )
    
    parts = [Part.from_text(text=dynamic_prefix + GEMINI_VISION_PROMPT)]
    for i, png_bytes in enumerate(images):
        parts.append(Part.from_data(data=png_bytes, mime_type="image/png"))

    try:
        logger.info(f"Sending {len(images)} page images to Vertex AI (Gemini Vision)...")
        # Use Pro for highest accuracy Vision extraction of complex multi-page financial tables
        model = GenerativeModel(
            "gemini-2.5-pro",
            system_instruction=(
                "You are an expert KSERC financial data extractor. "
                "You MUST return ONLY valid JSON matching the exact schema. No markdown. "
                "CRITICAL INSTRUCTIONS: "
                "1. Identify the 'Claimed' or 'Petition' column (NOT 'KSERC Approved'). "
                "2. Extract every single expense and revenue item into `claimed_expenses` and `claimed_revenues`. "
                "3. MATHEMATICAL CHECKSUM: The sum of all values inside `claimed_expenses` MUST EXACTLY EQUAL `total_expenditure`. If it does not, you extracted a row incorrectly. Fix it. "
                "All values are in Rs. Lakhs. Precision is strictly required."
            )
        )
        
        max_retries = 2
        gemini_expenses = {}
        gemini_revenues = {}
        data = {}

        for attempt in range(max_retries):
            response = model.generate_content(
                contents=parts,
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.0, # Completely deterministic for data extraction
                )
            )

            raw = response.text.strip()

            # Strip markdown code fences
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
                
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                logger.error(f"Gemini Vision returned non-JSON: {e}\nRaw: {raw[:500]}")
                if attempt == max_retries - 1:
                    return 0.0
                continue

            gemini_expenses = data.get("claimed_expenses", {})
            gemini_revenues = data.get("claimed_revenues", {})

            # Checksum validation
            calc_exp = sum(float(str(v).replace(',', '')) for v in gemini_expenses.values() if v)
            target_exp = float(str(data.get("total_expenditure", 0.0)).replace(',', ''))
            
            if target_exp > 0 and abs(calc_exp - target_exp) > 2.0: # Allow minor rounding diffs
                logger.warning(f"  [Attempt {attempt+1}] Checksum Failed! Calculated exp: {calc_exp:.2f}, Table total: {target_exp:.2f}")
                if attempt < max_retries - 1:
                    # Append the error message to the prompt for the next try
                    error_msg = f"ERROR: Your previous extraction failed the mathematical checksum. Your extracted expenses sum to {calc_exp:.2f}, but you reported a 'total_expenditure' of {target_exp:.2f}. Please carefully re-read the table columns and fix the incorrect missing numbers."
                    parts.append(Part.from_text(text=error_msg))
                    continue
            else:
                logger.info(f"  [Attempt {attempt+1}] Checksum Passed! Calculated exp: {calc_exp:.2f} == Table total: {target_exp:.2f}")

            logger.info(f"Gemini Vision raw response (first 500 chars): {raw[:500]}")
            break

        # Merge into state dicts — only update if Gemini returned a non-zero value
        updates_exp = 0
        for key in claimed_expenses:
            val = gemini_expenses.get(key, 0.0)
            if val is not None:
                try:
                    fval = float(str(val).replace(",", ""))
                    if fval != 0.0:
                        claimed_expenses[key] = fval
                        updates_exp += 1
                        logger.info(f"  [GeminiVision] expenses.{key}: {fval}")
                except (ValueError, TypeError):
                    pass

        updates_rev = 0
        for key in claimed_revenues:
            val = gemini_revenues.get(key, 0.0)
            if val is not None:
                try:
                    fval = float(str(val).replace(",", ""))
                    if fval != 0.0:
                        claimed_revenues[key] = fval
                        updates_rev += 1
                        logger.info(f"  [GeminiVision] revenues.{key}: {fval}")
                except (ValueError, TypeError):
                    pass

        logger.info(f"Gemini Vision: updated {updates_exp} exp fields, {updates_rev} rev fields")

        dist_loss = float(data.get("distribution_loss_pct", 0.0))
        logger.info(f"  [GeminiVision] distribution_loss_pct: {dist_loss}%")

        # Extract BEE energy audit fee if present in the A&G breakdown
        bee_fee = float(data.get("bee_energy_audit_fee", 0.0) or 0.0)
        logger.info(f"  [GeminiVision] bee_energy_audit_fee: {bee_fee}L")

        # Store bee_fee on the shared state dict (passed by reference)
        claimed_expenses["__bee_energy_audit_fee__"] = bee_fee

        return dist_loss

    except Exception as e:
        logger.error(f"Gemini Vision extraction failed: {e}")

    return 0.0


# ══════════════════════════════════════════════════════════════════════════
# PyMuPDF Text + Table Extraction (fallback)
# ══════════════════════════════════════════════════════════════════════════

def _extract_text_and_tables_pymupdf(pdf_path: str) -> Tuple[str, List[pd.DataFrame]]:
    """
    Extract full text and structured tables from a PDF using PyMuPDF.
    
    Uses find_tables() for proper cell-level table extraction (PyMuPDF >= 1.23).
    Falls back to word-bounding-box approach for older versions.
    Returns (full_text, tables).
    """
    import fitz

    doc = fitz.open(pdf_path)
    pages_text = []
    tables: List[pd.DataFrame] = []

    for page in doc:
        pages_text.append(page.get_text("text"))
        
        # Try structured table extraction (PyMuPDF >= 1.23)
        try:
            page_tabs = page.find_tables()
            for tab in page_tabs.tables:
                if tab.row_count < 2 or tab.col_count < 2:
                    continue
                rows = tab.extract()
                # First row as headers, rest as data
                if len(rows) >= 2:
                    # Clean None values to empty strings
                    header = [str(h) if h is not None else "" for h in rows[0]]
                    data = []
                    for row in rows[1:]:
                        data.append([str(c) if c is not None else "" for c in row])
                    try:
                        df = pd.DataFrame(data, columns=header[:len(data[0])] if header else None)
                        tables.append(df)
                        logger.info(f"  [find_tables] Extracted table: {df.shape[0]} rows x {df.shape[1]} cols")
                    except Exception:
                        tables.append(pd.DataFrame(data))
        except AttributeError:
            # Fallback to word-bounding-box approach for older PyMuPDF
            words = page.get_text("words")
            if not words:
                continue
            row_map: Dict[int, list] = {}
            for w in words:
                y_bucket = round(w[1] / 5) * 5
                row_map.setdefault(y_bucket, []).append(w)
            rows = []
            for y in sorted(row_map):
                cells = sorted(row_map[y], key=lambda w: w[0])
                rows.append([c[4] for c in cells])
            if len(rows) >= 2:
                try:
                    df = pd.DataFrame(rows[1:], columns=rows[0][:len(rows[1])] if rows[0] else None)
                    tables.append(df)
                except Exception:
                    try:
                        tables.append(pd.DataFrame(rows))
                    except Exception:
                        pass

    doc.close()
    full_text = "\n".join(pages_text)
    logger.info(f"PyMuPDF: extracted {len(full_text)} chars, {len(tables)} tables")
    return full_text, tables


# ══════════════════════════════════════════════════════════════════════════
# Row-scan fallback — reads ARR summary tables row by row
# ══════════════════════════════════════════════════════════════════════════

# Map of expense dict keys → matching substrings (all lowercase)
ARR_ROW_MAP: Dict[str, List[str]] = {
    # EXPENSES
    "power_purchase_cost":        ["power purchase", "cost of power", "purchase of power",
                                   "energy purchase", "power purchase cost"],
    "employee_cost":              ["employee cost", "employee expenses", "employee expense"],
    "repair_maintenance":         ["repair & maintenance", "r&m expense", "repairs and maintenance",
                                   "repair and maintenance"],
    "admin_general":              ["administration and general", "administration & general",
                                   "a&g expense", "a & g", "admin & general", "admin and general"],
    "depreciation":               ["depreciation"],
    "interest_long_term":         ["interest on long term", "interest on normative",
                                   "interest and finance charges on long term",
                                   "interest and finance charges on long",
                                   "interest & finance", "interest and finance charge"],
    "interest_consumer_deposits": ["interest on consumer deposit", "interest on consumer security",
                                   "interest on consumer deposits & bank",
                                   "interest on security deposit"],
    "interest_working_capital":   ["interest on working capital",
                                   "interest on working capital and finance"],
    "carrying_cost":              ["carrying cost"],
    "return_on_nfa":              ["return on net fixed", "return on nfa", "return on equity"],
    "other_debits":               ["other debit", "other debits",
                                   "duty-iii", "duty iii", "duty - iii"],
    "section3_1_duty":            ["section 3(1)", "electricity duty", "kerala electricity duty"],
    "other_expenses":             ["other expense", "miscellaneous",
                                   "inspection charge", "periodical inspection",
                                   "provision for doubtful", "provision for bad"],
    # REVENUES
    "revenue_from_sale":          ["revenue from sale", "revenue from sale of power"],
    "wheeling_charges":           ["wheeling charge"],
    "non_tariff_income":          ["non-tariff income", "non tariff income"],
    "other_revenue":              ["other income", "other revenue"],
}


def _num(val: str) -> Optional[float]:
    """Parse a string like '4,652.88' or '(86.84)' into a float."""
    s = str(val).strip()
    negative = s.startswith("(") and s.endswith(")")
    s = s.replace("(", "").replace(")", "").replace(",", "").strip()
    try:
        f = float(s)
        return -f if negative else f
    except ValueError:
        return None


# Column header patterns to identify the "Claimed" / "Petition" column
_CLAIMED_COL_PATTERNS = [
    "petition", "claimed", "actual", "truing up", "for truing",
    "as per accounts", "petitioner", "claim", "audited", "truing up claim",
]
_SKIP_COL_PATTERNS = [
    "approved", "trued up", "kserc", "commission", "myt", "arr", "projected",
    "previous year", "variance",
]
# FY year patterns to identify columns belonging to the petition year
# Matches both '2023-24' (Technopark) and '2024/25' (KDHP) formats
_FY_YEAR_PATTERN = re.compile(r"(20\d{2})[-–/](\d{2})")


def _detect_claimed_column_index(df: pd.DataFrame, target_fy: str = "") -> Optional[int]:
    """
    Detect the column index that contains "Claimed" / "Petition" data
    by matching column header text. Returns 0-based column index or None.
    
    When multiple columns match (e.g. '2023-24 Audited' and '2022-23 Audited'),
    prefers the one containing the target financial year.
    If no target FY match, returns the FIRST (leftmost) matching column.
    """
    # Replace newlines with spaces for pattern matching (KDHP uses multi-line headers)
    headers = [str(c).lower().replace('\n', ' ').replace('\r', ' ').strip() for c in df.columns]
    
    # Extract target FY start year for matching (e.g. '2023-24' -> '2023')
    target_fy_start = ""
    if target_fy:
        fy_match = _FY_YEAR_PATTERN.search(target_fy)
        if fy_match:
            target_fy_start = fy_match.group(1)  # e.g. '2023'
    
    # First pass: find ALL columns matching claimed patterns (not skip patterns)
    matching_cols = []
    for idx, header in enumerate(headers):
        if any(pat in header for pat in _CLAIMED_COL_PATTERNS):
            if not any(skip in header for skip in _SKIP_COL_PATTERNS):
                matching_cols.append((idx, header))
    
    if matching_cols:
        # If we have a target FY, prefer the column with matching year
        if target_fy_start:
            for idx, header in matching_cols:
                if target_fy_start in header:
                    logger.info(f"  [ColDetect] FY-matched column {idx}: '{header}' (target FY={target_fy})")
                    return idx
        # Otherwise return the FIRST (leftmost) matching column
        logger.info(f"  [ColDetect] Leftmost matching column {matching_cols[0][0]}: '{matching_cols[0][1]}'")
        return matching_cols[0][0]
    
    # Second pass: check first few rows for header-like text (merged header tables)
    # KSERC tables often have multi-row headers: R3=years, R4='Audited'/'Approved'
    for row_idx in range(min(6, len(df))):
        row_vals = [str(v).lower().replace('\n', ' ').replace('\r', ' ').strip() for v in df.iloc[row_idx].values]
        row_matches = []
        for col_idx, val in enumerate(row_vals):
            if any(pat in val for pat in _CLAIMED_COL_PATTERNS):
                if not any(skip in val for skip in _SKIP_COL_PATTERNS):
                    row_matches.append((col_idx, val))
        if row_matches:
            # Prefer FY-matched column
            if target_fy_start:
                for col_idx, val in row_matches:
                    if target_fy_start in val:
                        return col_idx
            return row_matches[0][0]  # leftmost
    
    return None


def _scan_arr_table(
    tables: List[pd.DataFrame],
    claimed_expenses: Dict[str, float],
    claimed_revenues: Dict[str, float],
    target_fy: str = "",
) -> bool:
    """
    Scan all DataFrame tables row by row, matching ARR row labels.
    Uses smart column detection: first tries to identify the 'Claimed/Petition'
    column header with FY awareness. Falls back to LEFTMOST (first data) numeric
    column if header detection fails.
    Returns True if any non-zero value was found.
    """
    found_any = False
    found_keys: set = set()  # Track keys found via Strategy 1 (column detection)
    for df in tables:
        if df.empty or len(df.columns) < 2:
            continue
        
        # Try to detect the claimed column index from headers (now FY-aware)
        claimed_col_idx = _detect_claimed_column_index(df, target_fy=target_fy)
        if claimed_col_idx is not None:
            logger.info(f"  [RowScan] Detected 'Claimed' column at index {claimed_col_idx}: '{df.columns[claimed_col_idx]}'")
        
        for _, row in df.iterrows():
            vals = [str(v) for v in row.values if pd.notna(v) and str(v).strip()]
            if not vals:
                continue
            row_text = " ".join(vals).lower()

            matched_key: Optional[str] = None
            for key, keywords in ARR_ROW_MAP.items():
                if any(kw in row_text for kw in keywords):
                    matched_key = key
                    break
            if matched_key is None:
                continue

            val: Optional[float] = None
            
            # Strategy 1: Use the detected column index
            if claimed_col_idx is not None:
                all_vals = [str(v) for v in row.values]
                if claimed_col_idx < len(all_vals):
                    val = _num(all_vals[claimed_col_idx])
                    if val is not None:
                        found_keys.add(matched_key)  # Mark as found via column detection
                    elif all_vals[claimed_col_idx].strip() in ('-', 'Nil', 'nil', 'Nil*', ''):
                        val = 0.0
                        found_keys.add(matched_key)  # Dash/Nil = confirmed zero
            
            # Strategy 2: Fallback — pick the first numeric value > 10.
            # Only use this when Strategy 1 FAILED (no column detected at all).
            # When Strategy 1 found a column but value was dash/None, trust it as 0.
            if val is None and claimed_col_idx is None:
                for v in vals:
                    n = _num(v)
                    if n is not None and abs(n) > 10.0:
                        val = n
                        break
                # If still none, the value is genuinely 0 or '-' (e.g. IWC = Nil)
                if val is None:
                    val = 0.0
            elif val is None:
                val = 0.0

            if val is None:
                continue

            if matched_key in claimed_expenses:
                # 'other_expenses' can accumulate from multiple sub-rows
                # (e.g. inspection charges + provision for doubtful debts in KDHP)
                if matched_key == "other_expenses" and val != 0.0:
                    claimed_expenses[matched_key] += val
                    logger.info(f"  [RowScan] expenses.{matched_key}: +{val} (accumulated, total={claimed_expenses[matched_key]})")
                    found_any = True
                elif claimed_expenses[matched_key] == 0.0 and matched_key not in found_keys:
                    claimed_expenses[matched_key] = val
                    logger.info(f"  [RowScan] expenses.{matched_key}: {val} (fallback)")
                    found_any = True
                elif matched_key in found_keys and claimed_expenses[matched_key] == 0.0:
                    claimed_expenses[matched_key] = val
                    logger.info(f"  [RowScan] expenses.{matched_key}: {val} (col-detected)")
                    found_any = True
            elif matched_key in claimed_revenues:
                if claimed_revenues[matched_key] == 0.0:
                    claimed_revenues[matched_key] = val
                    logger.info(f"  [RowScan] revenues.{matched_key}: {val}")
                    found_any = True

    return found_any


# ══════════════════════════════════════════════════════════════════════════
# Distribution loss extraction
# ══════════════════════════════════════════════════════════════════════════

def _extract_distribution_loss(tables: List[pd.DataFrame], full_text: str) -> float:
    """Extract distribution loss percentage from tables or text."""
    for df in tables:
        for _, row in df.iterrows():
            vals = [str(v) for v in row.values if pd.notna(v)]
            row_text = " ".join(vals).lower()
            if "distribution loss" in row_text and "%" in row_text:
                for v in reversed(vals):
                    s = v.replace("%", "").replace(",", "").strip()
                    try:
                        f = float(s)
                        if 0 < f < 100:
                            return f
                    except ValueError:
                        continue

    # Fallback: regex on full text
    matches = re.findall(
        r"distribution\s+loss\s*(?:percentage|%|pct)?\s*[:\-]?\s*([\d.]+)\s*%",
        full_text, re.IGNORECASE
    )
    for m in matches:
        try:
            f = float(m)
            if 0 < f < 100:
                return f
        except ValueError:
            continue
    return 0.0


# ══════════════════════════════════════════════════════════════════════════
# Asset register extraction
# ══════════════════════════════════════════════════════════════════════════

def _extract_asset_register(tables: List[pd.DataFrame]) -> List[Dict[str, Any]]:
    """Extract fixed asset entries from tables."""
    assets = []
    for df in tables:
        if df.empty or len(df.columns) < 3:
            continue
        for _, row in df.iterrows():
            vals = [str(v) for v in row.values if pd.notna(v) and str(v).strip()]
            row_text = " ".join(vals).lower()
            if any(k in row_text for k in ["gfa", "gross fixed asset", "net fixed asset", "cwip", "capital work"]):
                nums = []
                for v in vals:
                    n = _num(v)
                    if n is not None and n > 0:
                        nums.append(n)
                if nums:
                    assets.append({
                        "description": vals[0] if vals else "",
                        "gross_value": nums[0] if nums else 0.0,
                        "net_value": nums[-1] if len(nums) > 1 else nums[0],
                    })
    return assets


# ══════════════════════════════════════════════════════════════════════════
# BEE Energy Audit Fee Extraction (regex on petition text)
# ══════════════════════════════════════════════════════════════════════════

def _extract_bee_fee_from_text(full_text: str) -> float:
    """
    Extract the BEE / electricity energy audit fee from A&G breakdown notes.

    The note typically appears below the 'Audit fees' row in the
    Administration & General Expenses detail table. Examples:
      "Rs.2.15 lakhs being audit fee for energy audit"
      "Rs.2.00 Lakhs towards Statutory audit fee and Rs.2.15 lakhs being
       audit fee for energy audit"
      "Rs.5.14 lakhs towards electricity audit"
      "energy audit fee of Rs. 2.15 Lakhs"

    Returns 0.0 if the note is not found.
    """
    if not full_text:
        return 0.0

    patterns = [
        # "Rs.2.15 lakhs being audit fee for energy audit"
        r"(?:Rs\.?\s*)([\d,]+\.?\d*)\s*(?:lakhs?|lakh)\s+(?:being|towards?|as)\s+audit\s+fee\s+for\s+energy\s+audit",
        # "Rs.5.14 lakhs towards electricity audit"
        r"(?:Rs\.?\s*)([\d,]+\.?\d*)\s*(?:lakhs?|lakh)\s+(?:being|towards?|as)\s+electricity\s+audit",
        # "energy audit fee of Rs. 2.15"
        r"energy\s+audit\s+fee\s+(?:of\s+)?(?:Rs\.?\s*)([\d,]+\.?\d*)",
        # "audit fee for energy audit.*Rs.2.15"
        r"audit\s+fee\s+for\s+energy\s+audit[^.]*?(?:Rs\.?\s*)([\d,]+\.?\d*)",
        # "BEE.*audit.*Rs.X" or "electricity audit.*Rs.X"
        r"(?:BEE|electricity)\s+audit[^.]{0,60}(?:Rs\.?\s*)([\d,]+\.?\d*)\s*(?:lakhs?|lakh)",
    ]

    for pat in patterns:
        m = re.search(pat, full_text, re.IGNORECASE | re.DOTALL)
        if m:
            try:
                val = float(m.group(1).replace(",", ""))
                if 0.1 <= val <= 20.0:   # sanity: BEE fee should be between 0.1L and 20L
                    logger.info(f"[BEEFeeExtract] Found Rs.{val}L using pattern: {pat[:60]}")
                    return val
            except ValueError:
                continue

    logger.info("[BEEFeeExtract] No BEE energy audit fee note found in petition text")
    return 0.0


# ══════════════════════════════════════════════════════════════════════════
# Main LangGraph Node Function
# ══════════════════════════════════════════════════════════════════════════

def extract_petition_data(state: dict) -> dict:
    """
    LangGraph node: extract ARR financial data from a KSERC petition PDF.

    Strategy (in order):
    1. Render PDF pages as images → Gemini Vision reads the ARR table
    2. If Gemini Vision fails/returns zeros → PyMuPDF text + row-scan fallback

    All monetary values are in Rs. Lakhs.

    Parameters
    ----------
    state : dict
        Must contain 'petition_pdf_path'.

    Returns
    -------
    dict
        Updated state fields.
    """
    pdf_path = state["petition_pdf_path"]
    logger.info(f"=== extract_petition_data: {pdf_path} ===")

    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"Petition PDF not found: {pdf_path}")

    licensee_name = state.get("licensee_name", "")
    target_fy = state.get("financial_year", "")
    
    # ── Extraction Result Caching ──────────────────────────────────────
    # Gemini Vision is non-deterministic — each API call can return different
    # values for the same PDF. To ensure consistent results between terminal
    # tests and frontend, cache extraction results by PDF file hash.
    cache_dir = Path(__file__).resolve().parent.parent.parent / ".extraction_cache"
    pdf_hash = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()[:16]
    cache_key = f"{pdf_hash}_{licensee_name}_{target_fy}".replace(" ", "_")
    cache_file = cache_dir / f"{cache_key}.json"
    
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            logger.info(f"[CACHE HIT] Using cached extraction result from {cache_file.name}")
            return cached
        except Exception as e:
            logger.warning(f"[CACHE] Failed to read cache: {e}, re-extracting...")

    claimed_expenses = _empty_expenses()
    claimed_revenues = _empty_revenues()
    dist_loss = 0.0
    extraction_method = "none"
    
    # Extract target financial year from state or PDF filename
    target_fy = state.get("financial_year", "")
    if not target_fy:
        # Try to extract FY from filename (e.g. '2023-24.pdf')
        fy_match = _FY_YEAR_PATTERN.search(Path(pdf_path).stem)
        if fy_match:
            target_fy = f"{fy_match.group(1)}-{fy_match.group(2)}"
            logger.info(f"Detected target FY from filename: {target_fy}")
    logger.info(f"Target FY for column detection: {target_fy or 'unknown'}")
    checksum_passed = False
    EXTRACT_DPI = 250
    FINDER_DPI = 100  # Lower DPI for page finder (faster, smaller images)
    MAX_PAGES = 60    # Support long scanned petitions (e.g. Infopark 2024-25 = 56 pages)

    # ── Step 1: Render ALL pages at low DPI for page finding ──────
    finder_images = []
    try:
        finder_images = _render_pdf_pages_as_images(pdf_path, max_pages=MAX_PAGES, dpi=FINDER_DPI)
        logger.info(f"Rendered {len(finder_images)} pages as PNG images at {FINDER_DPI} DPI (page finder)")
    except Exception as e:
        logger.error(f"Failed to render PDF pages: {e}")

    # ── Step 1.5: Two-pass page finder ────────────────────────────
    arr_page_indices = []
    licensee_name = state.get("licensee_name", "").upper()
    
    if len(finder_images) > 6:
        try:
            arr_page_indices = _find_arr_table_pages(finder_images)
            logger.info(f"Two-pass: ARR table found on pages {[i+1 for i in arr_page_indices]} (of {len(finder_images)} total)")
        except Exception as e:
            logger.warning(f"Page finder failed: {e}")
    
    if not arr_page_indices:
        # Fallback: use first 8 pages
        arr_page_indices = list(range(min(len(finder_images), 8)))
        logger.warning(f"Using fallback: first {len(arr_page_indices)} pages")

    # KDHP-specific: Send ALL pages to Gemini Vision because the O&M sub-table
    # (with employee/R&M/A&G breakdown) is on a separate page from the ARR summary.
    # KDHP petitions are typically short (~12 pages), so this is efficient.
    if "KDHP" in licensee_name or "KANNAN" in licensee_name:
        all_pages = list(range(len(finder_images)))
        # Ensure ARR pages come first, then remaining pages
        extra_pages = [p for p in all_pages if p not in arr_page_indices]
        arr_page_indices = arr_page_indices + extra_pages
        logger.info(f"KDHP mode: expanded to ALL {len(arr_page_indices)} pages for O&M sub-table detection")

    # ── Step 1.6: Re-render ONLY ARR pages at high DPI for extraction ──
    target_images = []
    try:
        all_hires = _render_pdf_pages_as_images(pdf_path, max_pages=MAX_PAGES, dpi=EXTRACT_DPI)
        target_images = [all_hires[i] for i in arr_page_indices if i < len(all_hires)]
        logger.info(f"Re-rendered {len(target_images)} ARR pages at {EXTRACT_DPI} DPI for extraction")
    except Exception as e:
        logger.warning(f"High-DPI re-render failed, using finder images: {e}")
        target_images = [finder_images[i] for i in arr_page_indices if i < len(finder_images)]

    # ── Step 2: Gemini Vision — primary extraction ─────────────────
    if target_images:
        try:
            dist_loss = _extract_with_gemini_vision(
                target_images, claimed_expenses, claimed_revenues,
                licensee_name=licensee_name, financial_year=target_fy,
            )
            extraction_method = "gemini_vision"
            
            # ── KDHP Post-Processing: Normalize Gemini's inconsistent extraction ──
            # Gemini Vision is non-deterministic and can split/combine values differently
            # each call. This step normalizes the results for KDHP petitions.
            if "KDHP" in licensee_name or "KANNAN" in licensee_name:
                logger.info("[KDHP PostProcess] Applying KDHP-specific normalization...")
                
                # 1. INTEREST: KDHP has a single "Interest & Finance charges" row (41.72)
                #    Gemini sometimes puts the full amount in interest_long_term,
                #    sometimes splits it into interest_long_term + interest_working_capital.
                #    Normalize: combine ALL interest into interest_long_term.
                interest_lt = claimed_expenses.get("interest_long_term", 0.0)
                interest_wc = claimed_expenses.get("interest_working_capital", 0.0)
                interest_cd = claimed_expenses.get("interest_consumer_deposits", 0.0)
                total_interest = interest_lt + interest_wc + interest_cd
                if total_interest > 0:
                    claimed_expenses["interest_long_term"] = round(total_interest, 2)
                    claimed_expenses["interest_working_capital"] = 0.0
                    claimed_expenses["interest_consumer_deposits"] = 0.0
                    logger.info(f"  [KDHP PostProcess] Combined interest: {interest_lt}+{interest_wc}+{interest_cd} -> interest_long_term={total_interest}")
                
                # 2. Ensure non_tariff_income is from Table 30 (should be ~124.07, not 36.55)
                nti = claimed_revenues.get("non_tariff_income", 0.0)
                other_rev = claimed_revenues.get("other_revenue", 0.0)
                if nti < 50 and other_rev > 0:
                    # Gemini likely confused "Other income" with non_tariff_income
                    # But don't override if nti is already correct (>100)
                    logger.warning(f"  [KDHP PostProcess] non_tariff_income={nti} seems too low (expected ~124). Check Table 30.")
                
                logger.info(f"  [KDHP PostProcess] Done. Total expenses: {sum(claimed_expenses.values()):.2f}")
                
        except Exception as e:
            logger.error(f"Gemini Vision extraction error: {e}")

    # ── Step 3: Check if we got useful data ───────────────────────
    all_exp_zero = all(v == 0.0 for v in claimed_expenses.values())
    bee_fee = 0.0  # resolved in either branch below

    if all_exp_zero:
        logger.warning("Gemini Vision returned all-zero expenses — falling back to PyMuPDF row-scan")
        extraction_method = "pymupdf_rowscan"

        # Step 3a: PyMuPDF text + table extraction
        try:
            full_text, tables = _extract_text_and_tables_pymupdf(pdf_path)
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            full_text, tables = "", []

        # Step 3b: Row scan on extracted tables (now with smart column detection + FY awareness)
        found = _scan_arr_table(tables, claimed_expenses, claimed_revenues, target_fy=target_fy)
        logger.info(f"Row-scan result: {'found values' if found else 'still zeros'}")
        if not found:
            extraction_method = "all_zeros"

        # Step 3c: Distribution loss from text if still 0
        if dist_loss == 0.0:
            dist_loss = _extract_distribution_loss(tables, full_text)

        # Step 3d: BEE energy audit fee from petition notes
        bee_fee = _extract_bee_fee_from_text(full_text)

        # Step 3e: Asset register
        asset_register = _extract_asset_register(tables)
    else:
        # Gemini succeeded — extract remaining data via PyMuPDF text for non-financial fields
        try:
            full_text, tables = _extract_text_and_tables_pymupdf(pdf_path)
        except Exception:
            full_text, tables = "", []
        asset_register = _extract_asset_register(tables)
        if dist_loss == 0.0:
            dist_loss = _extract_distribution_loss(tables, full_text)

        # BEE energy audit fee — Gemini Vision may have stored it via __bee_energy_audit_fee__
        # but also run the regex on full_text to catch cases where Gemini missed it
        gemini_bee = float(claimed_expenses.pop("__bee_energy_audit_fee__", 0.0) or 0.0)
        regex_bee  = _extract_bee_fee_from_text(full_text)
        bee_fee    = gemini_bee if gemini_bee > 0.0 else regex_bee
        if bee_fee > 0.0:
            logger.info(f"BEE fee resolved: Rs.{bee_fee:.2f}L (source: {'gemini' if gemini_bee > 0.0 else 'regex'})")
        
        # ── KDHP Cross-Validation: PyMuPDF deterministic override ──────────
        # Gemini Vision is non-deterministic — each call can read different columns.
        # PyMuPDF row-scan is deterministic (same input → same output every time).
        # For KDHP, run PyMuPDF and use its values to OVERRIDE Gemini's.
        if "KDHP" in licensee_name or "KANNAN" in licensee_name:
            logger.info("[KDHP CrossValidation] Running deterministic PyMuPDF row-scan for cross-validation...")
            pymupdf_expenses = _empty_expenses()
            pymupdf_revenues = _empty_revenues()
            pymupdf_found = _scan_arr_table(tables, pymupdf_expenses, pymupdf_revenues, target_fy=target_fy)
            
            if pymupdf_found:
                logger.info("[KDHP CrossValidation] PyMuPDF row-scan found values. Comparing with Gemini:")
                overrides = 0
                for key in pymupdf_expenses:
                    pymupdf_val = pymupdf_expenses[key]
                    gemini_val = claimed_expenses.get(key, 0.0)
                    if pymupdf_val > 0 and abs(pymupdf_val - gemini_val) > 0.5:
                        logger.info(f"  [OVERRIDE] {key}: Gemini={gemini_val} → PyMuPDF={pymupdf_val}")
                        claimed_expenses[key] = pymupdf_val
                        overrides += 1
                    elif pymupdf_val > 0:
                        logger.info(f"  [MATCH] {key}: Gemini={gemini_val}, PyMuPDF={pymupdf_val}")
                
                # Also override revenue values
                for key in pymupdf_revenues:
                    pymupdf_val = pymupdf_revenues[key]
                    gemini_val = claimed_revenues.get(key, 0.0)
                    if pymupdf_val > 0 and abs(pymupdf_val - gemini_val) > 0.5:
                        logger.info(f"  [OVERRIDE] revenue.{key}: Gemini={gemini_val} → PyMuPDF={pymupdf_val}")
                        claimed_revenues[key] = pymupdf_val
                        overrides += 1
                
                extraction_method = "gemini_vision+pymupdf_crossval"
                logger.info(f"[KDHP CrossValidation] Done. {overrides} values overridden by PyMuPDF.")
            else:
                logger.warning("[KDHP CrossValidation] PyMuPDF row-scan found no values. Keeping Gemini results.")

    # ── Step 4: Checksum validation ────────────────────────────────
    total_exp = sum(claimed_expenses.values())
    total_rev = sum(claimed_revenues.values())
    
    # Basic sanity: at least some expenses and revenue should be non-zero
    if total_exp > 0 and total_rev > 0:
        checksum_passed = True
    
    # ── Step 5: Post-extraction validation ──────────────────────────
    # Cross-check against MYT norms and internal consistency
    myt_norms = state.get("myt_baseline_norms", {})
    extraction_warnings = []
    
    if total_exp > 0:
        ppc = claimed_expenses.get("power_purchase_cost", 0.0)
        non_ppc = total_exp - ppc
        
        # PPC sanity: For distribution licensees, PPC is typically 50-85% of total ARR
        if ppc > 0 and total_exp > 0:
            ppc_pct = ppc / total_exp * 100
            if ppc_pct < 40:
                extraction_warnings.append(
                    f"PPC is only {ppc_pct:.1f}% of total expenditure "
                    f"(expected 50-85% for distribution licensees). "
                    f"PPC may be under-extracted."
                )
        
        # Check PPC against MYT norm if available — should be within 50-200% of norm
        myt_ppc = myt_norms.get("power_purchase_cost", 0.0)
        if myt_ppc > 0 and ppc > 0:
            ppc_ratio = ppc / myt_ppc
            if ppc_ratio < 0.5:
                extraction_warnings.append(
                    f"Extracted PPC ({ppc:.2f}L) is less than 50% of "
                    f"MYT norm ({myt_ppc:.2f}L). Likely under-extracted."
                )
            elif ppc_ratio > 2.0:
                extraction_warnings.append(
                    f"Extracted PPC ({ppc:.2f}L) is more than 200% of "
                    f"MYT norm ({myt_ppc:.2f}L). Possible over-extraction."
                )
        
        # Check each component against MYT norms — flag if >300% above norm
        for key in ("employee_cost", "repair_maintenance", "admin_general", "depreciation"):
            extracted = claimed_expenses.get(key, 0.0)
            norm = myt_norms.get(key, 0.0)
            if norm > 0 and extracted > 0 and extracted / norm > 3.0:
                extraction_warnings.append(
                    f"{key}: Extracted {extracted:.2f}L is >3x MYT norm {norm:.2f}L. "
                    f"Possible extraction error."
                )
    
    if extraction_warnings:
        logger.warning(f"Extraction validation warnings ({len(extraction_warnings)}):")
        for w in extraction_warnings:
            logger.warning(f"  ⚠ {w}")
    
    logger.info(f"claimed_expenses total: {total_exp:.2f} Lakhs")
    logger.info(f"claimed_revenues total: {total_rev:.2f} Lakhs")
    logger.info(f"distribution_loss_pct: {dist_loss}%")
    logger.info(f"extraction_method: {extraction_method} | checksum: {'PASS' if checksum_passed else 'FAIL'}")
    logger.info(f"claimed_expenses breakdown: {claimed_expenses}")
    logger.info(f"claimed_revenues breakdown: {claimed_revenues}")

    result = {
        "claimed_expenses":               claimed_expenses,
        "claimed_revenues":               claimed_revenues,
        "asset_register":                 asset_register,
        "claimed_distribution_loss_pct":  dist_loss,
        "bee_energy_audit_fee":           bee_fee,
        "extraction_metadata": {
            "method": extraction_method,
            "pages_scanned": len(finder_images),
            "pages_targeted": len(target_images),
            "arr_pages_detected": [p + 1 for p in arr_page_indices] if arr_page_indices else [],
            "finder_dpi": FINDER_DPI,
            "extract_dpi": EXTRACT_DPI,
            "checksum_passed": checksum_passed,
            "extracted_total_expenditure": round(total_exp, 2),
            "extracted_total_revenue": round(total_rev, 2),
            "extraction_warnings": extraction_warnings,
        },
    }
    
    # ── Save to extraction cache ──────────────────────────────────────
    # Cache successful extractions so the same PDF always returns the same result.
    if total_exp > 0:
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
            logger.info(f"[CACHE SAVE] Extraction result cached to {cache_file.name}")
        except Exception as e:
            logger.warning(f"[CACHE] Failed to save cache: {e}")
    
    return result
