"""
Re-extract 2023-24 Trued-Up Order sub-item data from KSERC PDFs → Firestore.
Focuses on:
  - R&M line items (approved by Commission)
  - A&G line items (approved by Commission) 
  - Employee line items (approved by Commission)
  - Energy sales by consumer category
  - Depreciation by asset group

This MERGES into existing precedent data (does not overwrite totals).

Usage:
    python scripts/re_extract_subitem.py
"""
import sys, os, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

from src.tools.db import get_precedent, save_precedent

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

# ── Config ──
PDFS = {
    "KDHP": r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\kannan devan 2023-24.pdf",
    "Technopark": r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\techonaprk2023-24.pdf",
    "Infopark": r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\info[aprk 2023-24 acutal trued up.pdf",
}
FY = "2023-24"

PROMPT = """You are an expert at extracting financial data from KSERC (Kerala State Electricity Regulatory Commission) trued-up orders.

This PDF is a KSERC Commission Order that trues up a licensee's accounts for a specific financial year.

I need you to extract the APPROVED/TRUED-UP sub-item breakdowns for the following components:

## 1. R&M (Repairs & Maintenance) LINE ITEMS — APPROVED by Commission
Look for the R&M comparison table. It typically has columns: Particulars | Claimed/Truing Up | Trued Up/Approved
Extract each individual line item's APPROVED/TRUED-UP value:
- Plant & Machinery
- Buildings
- Lines & Cable Networks
- Vehicles
- LT Lines/Upkeeps etc.
- Gross R&M Expenses (total)

## 2. A&G (Administration & General) LINE ITEMS — APPROVED by Commission  
Look for the A&G comparison table:
- Rent Rates & Taxes
- Insurance
- Telephone & Postage
- Legal charges
- Audit Fees
- Travelling Expenses
- Conveyance and vehicle hire charges
- Electricity charges
- Printing & Stationery
- Miscellaneous Expenses
- License Fee and other related fees
- Security arrangements
- Gross A&G Expenses (total)

## 3. Employee Cost LINE ITEMS — APPROVED by Commission
Look for the Employee Cost comparison table:
- Basic Salary
- Dearness Allowance (DA)
- Leave Travel Allowance (LTA)
- Earned Leave/Leave Encashment
- Other Allowances
- Medical Reimbursement
- Overtime Payment
- Bonus/Ex-gratia
- Staff Welfare
- Provident Fund (PF) contribution
- Directors Remuneration / Manager salary
- Gross Employee Expenses (total)

## 4. R&M CLAIMED LINE ITEMS — what the licensee claimed
Same items as #1 but use the "Truing Up" / "Claimed" column values.

## 5. A&G CLAIMED LINE ITEMS — what the licensee claimed
Same items as #2 but use the "Truing Up" / "Claimed" column values.

## 6. Employee CLAIMED LINE ITEMS — what the licensee claimed  
Same items as #3 but use the "Truing Up" / "Claimed" column values.

## 7. Energy Sales by Consumer Category — TRUED UP
Look for the category-wise energy sales table:
- HT I A Industrial
- HT I B Industrial
- HT II General
- HT III Agriculture
- HT IV Commercial
- LT I Domestic
- LT IV Industries
- LT V Agriculture
- LT VI General/Non-Domestic
- LT VII Commercial
- LT VIII Street Lighting/Public Lighting
- Total Sales (in Lakh Units or MU)

Also extract the Number of Consumers per category if available.

## 8. Depreciation by Asset Group — APPROVED
- Transformers (above/below cutoff)
- Distribution Lines (above/below cutoff)
- Meters (above/below cutoff)
- IT Equipment (above/below cutoff)
- Others (above/below cutoff)
- Grand Total

IMPORTANT RULES:
- Use ONLY the Commission's APPROVED / TRUED UP column values for approved fields
- Use the licensee's CLAIMED / PETITION / TRUING UP column values for claimed fields  
- All monetary values in Rs. Lakhs
- If a specific line item is not found in the order, use 0.0
- If the order does not have a particular comparison table, still try to find the values in the text
- Return the data as a JSON object

Return a JSON object with these keys:
{
  "rm_line_items": {
    "plant_machinery": <number>,
    "buildings": <number>,
    "lines_cable_networks": <number>,
    "vehicles": <number>,
    "lt_lines_upkeeps": <number>,
    "gross_rm_expenses": <number>
  },
  "ag_line_items": {
    "rent_rates_taxes": <number>,
    "insurance": <number>,
    "telephone_postage": <number>,
    "legal_charges": <number>,
    "audit_fees": <number>,
    "travelling_expenses": <number>,
    "conveyance_vehicle_hire": <number>,
    "electricity_charges": <number>,
    "printing_stationery": <number>,
    "miscellaneous_expenses": <number>,
    "license_fee": <number>,
    "security_arrangements": <number>,
    "gross_ag_expenses": <number>
  },
  "employee_line_items": {
    "basic_salary": <number>,
    "dearness_allowance": <number>,
    "leave_travel_allowance": <number>,
    "earned_leave_encashment": <number>,
    "other_allowances": <number>,
    "medical_reimbursement": <number>,
    "overtime_payment": <number>,
    "bonus_exgratia": <number>,
    "staff_welfare": <number>,
    "provident_fund": <number>,
    "directors_remuneration": <number>,
    "gross_employee_expenses": <number>
  },
  "rm_claimed_line_items": { ... same keys as rm_line_items ... },
  "ag_claimed_line_items": { ... same keys as ag_line_items ... },
  "employee_claimed_line_items": { ... same keys as employee_line_items ... },
  "energy_sales_by_category": {
    "ht_ia_industrial": <number in MU>,
    "ht_ib_industrial": <number in MU>,
    "ht_ii_general": <number in MU>,
    "ht_iii_agriculture": <number in MU>,
    "ht_iv_commercial": <number in MU>,
    "lt_i_domestic": <number in MU>,
    "lt_iv_industries": <number in MU>,
    "lt_v_agriculture": <number in MU>,
    "lt_vi_general": <number in MU>,
    "lt_vii_commercial": <number in MU>,
    "lt_viii_street_lighting": <number in MU>,
    "total_sales": <number in MU>
  },
  "consumers_by_category": {
    "ht_ia_industrial": <number>,
    "ht_ib_industrial": <number>,
    ...same categories...
    "total_consumers": <number>
  },
  "depreciation_asset_wise": {
    "transformers": <number>,
    "distribution_lines": <number>,
    "meters": <number>,
    "it_equipment": <number>,
    "others": <number>,
    "grand_total": <number>
  }
}
"""


def extract_subitems(licensee: str, pdf_path: str) -> dict:
    """Extract sub-item breakdowns from a single PDF."""
    logger.info(f"Extracting sub-items for {licensee} from {Path(pdf_path).name}...")
    
    client = genai.Client(
        api_key=os.environ.get("GOOGLE_API_KEY"),
        http_options={"api_version": "v1alpha"},
    )
    
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    
    response = client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=[pdf_part, PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )
    
    data = json.loads(response.text)
    
    # Log what we got
    for key in ["rm_line_items", "ag_line_items", "employee_line_items", 
                "rm_claimed_line_items", "ag_claimed_line_items",
                "energy_sales_by_category", "consumers_by_category"]:
        items = data.get(key, {})
        non_zero = {k: v for k, v in items.items() if v and float(v) > 0}
        logger.info(f"  {key}: {len(non_zero)}/{len(items)} non-zero values")
        if non_zero:
            for k, v in non_zero.items():
                logger.info(f"    {k}: {v}")
    
    return data


def main():
    for licensee, pdf_path in PDFS.items():
        if not Path(pdf_path).exists():
            logger.error(f"  PDF not found: {pdf_path}")
            continue
        
        # Extract new sub-item data
        sub_data = extract_subitems(licensee, pdf_path)
        
        # Load existing precedent data
        existing = get_precedent(licensee, FY)
        if not existing:
            logger.warning(f"  No existing data for {licensee} FY {FY} — saving fresh")
            save_precedent(licensee, FY, sub_data)
        else:
            # MERGE: overwrite sub-item keys, keep everything else
            merged = dict(existing)
            for key in ["rm_line_items", "ag_line_items", "employee_line_items",
                        "rm_claimed_line_items", "ag_claimed_line_items", 
                        "employee_claimed_line_items",
                        "energy_sales_by_category", "consumers_by_category",
                        "depreciation_asset_wise"]:
                new_val = sub_data.get(key, {})
                non_zero = {k: v for k, v in new_val.items() if v and float(v) > 0}
                if non_zero:
                    merged[key] = new_val
                    logger.info(f"  Updated {key} ({len(non_zero)} non-zero values)")
                else:
                    logger.info(f"  Skipping {key} (no non-zero values in new extraction)")
            
            save_precedent(licensee, FY, merged)
        
        logger.info(f"  ✓ Merged {licensee} FY {FY} to Firestore\n")
    
    # Verify
    logger.info("=== Verification ===")
    for licensee in PDFS:
        p = get_precedent(licensee, FY)
        if p:
            rm = p.get("rm_line_items", {})
            ag = p.get("ag_line_items", {})
            rm_nz = {k: v for k, v in rm.items() if v and float(v) > 0}
            ag_nz = {k: v for k, v in ag.items() if v and float(v) > 0}
            logger.info(f"{licensee}: RM items={len(rm_nz)}, AG items={len(ag_nz)}")
            if rm_nz:
                logger.info(f"  RM: {rm_nz}")
            if ag_nz:
                logger.info(f"  AG: {ag_nz}")
        else:
            logger.warning(f"{licensee} FY {FY}: NOT FOUND in Firestore!")


if __name__ == "__main__":
    main()
