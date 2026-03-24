"""
Extract 2023-24 Trued-Up Order data from KSERC PDFs → Firestore.

Usage:
    python scripts/extract_trued_up_order.py
"""
import sys, os, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

from src.tools.db import save_precedent

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

# ── Config ──
PDFS = {
    "KDHP": r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\KANNADEVAN 2023-24.pdf",
    "Technopark": r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\techonaprk2023-24.pdf",
    "Infopark": r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\info[aprk 2023-24 acutal trued up.pdf",
}
FY = "2023-24"

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "approved_expenses": {
            "type": "object",
            "description": "Commission-approved (trued-up) expenses in Rs. Lakhs",
            "properties": {
                "power_purchase_cost": {"type": "number"},
                "employee_cost": {"type": "number"},
                "repair_maintenance": {"type": "number"},
                "admin_general": {"type": "number"},
                "depreciation": {"type": "number"},
                "interest_long_term": {"type": "number"},
                "interest_working_capital": {"type": "number"},
                "interest_consumer_deposits": {"type": "number"},
                "return_on_nfa": {"type": "number"},
                "other_debits": {"type": "number"},
                "other_expenses": {"type": "number"},
                "section3_1_duty": {"type": "number"},
            }
        },
        "approved_revenues": {
            "type": "object",
            "properties": {
                "revenue_from_sale": {"type": "number"},
                "non_tariff_income": {"type": "number"},
                "wheeling_charges": {"type": "number"},
            }
        },
        "total_approved_expenditure": {"type": "number"},
        "total_approved_revenue": {"type": "number"},
        "revenue_gap_surplus": {"type": "number", "description": "Positive=surplus, Negative=gap"},
        "ag_line_items": {
            "type": "object",
            "description": "A&G sub-items approved by Commission (Rs. Lakhs). Use the TRUED UP / APPROVED column.",
            "properties": {
                "rent_rates_taxes": {"type": "number"},
                "insurance": {"type": "number"},
                "telephone_postage": {"type": "number"},
                "legal_charges": {"type": "number"},
                "audit_fees": {"type": "number"},
                "travelling_expenses": {"type": "number"},
                "conveyance_vehicle_hire": {"type": "number"},
                "electricity_charges": {"type": "number"},
                "printing_stationery": {"type": "number"},
                "miscellaneous_expenses": {"type": "number"},
                "license_fee": {"type": "number"},
                "security_arrangements": {"type": "number"},
                "gross_ag_expenses": {"type": "number"},
            }
        },
        "rm_line_items": {
            "type": "object",
            "description": "R&M sub-items approved by Commission (Rs. Lakhs)",
            "properties": {
                "plant_machinery": {"type": "number"},
                "buildings": {"type": "number"},
                "lines_cable_networks": {"type": "number"},
                "vehicles": {"type": "number"},
                "lt_lines_upkeeps": {"type": "number"},
                "gross_rm_expenses": {"type": "number"},
            }
        },
        "employee_line_items": {
            "type": "object",
            "description": "Employee cost sub-items APPROVED by Commission (Rs. Lakhs)",
            "properties": {
                "basic_salary": {"type": "number"},
                "dearness_allowance": {"type": "number"},
                "leave_travel_allowance": {"type": "number"},
                "earned_leave_encashment": {"type": "number"},
                "other_allowances": {"type": "number"},
                "medical_reimbursement": {"type": "number"},
                "overtime_payment": {"type": "number"},
                "bonus_exgratia": {"type": "number"},
                "staff_welfare": {"type": "number"},
                "provident_fund": {"type": "number"},
                "salary_manager_executive": {"type": "number"},
                "directors_remuneration": {"type": "number"},
                "gross_employee_expenses": {"type": "number"},
            }
        },
        "employee_claimed_line_items": {
            "type": "object",
            "description": "Employee cost sub-items CLAIMED by the licensee (Rs. Lakhs)",
            "properties": {
                "basic_salary": {"type": "number"},
                "dearness_allowance": {"type": "number"},
                "leave_travel_allowance": {"type": "number"},
                "earned_leave_encashment": {"type": "number"},
                "other_allowances": {"type": "number"},
                "medical_reimbursement": {"type": "number"},
                "overtime_payment": {"type": "number"},
                "bonus_exgratia": {"type": "number"},
                "staff_welfare": {"type": "number"},
                "provident_fund": {"type": "number"},
                "salary_manager_executive": {"type": "number"},
                "directors_remuneration": {"type": "number"},
                "gross_employee_expenses": {"type": "number"},
            }
        },
        "energy_sales_by_category": {
            "type": "object",
            "description": "Energy sales in Lakh Units by tariff category, as approved/trued-up",
            "properties": {
                "ht_ia_industrial": {"type": "number"},
                "ht_ib_industrial": {"type": "number"},
                "ht_ii_general": {"type": "number"},
                "ht_iii_agriculture": {"type": "number"},
                "ht_iv_commercial": {"type": "number"},
                "lt_i_domestic": {"type": "number"},
                "lt_iv_industries": {"type": "number"},
                "lt_v_agriculture": {"type": "number"},
                "lt_vi_general": {"type": "number"},
                "lt_vii_commercial": {"type": "number"},
                "lt_viii_street_lighting": {"type": "number"},
                "total_sales": {"type": "number"},
            }
        },
        "depreciation_asset_wise": {
            "type": "object",
            "description": "Depreciation approved by asset group (Rs. Lakhs)",
            "properties": {
                "transformers_above13": {"type": "number"},
                "distribution_lines_above13": {"type": "number"},
                "meters_above13": {"type": "number"},
                "it_equipment_above13": {"type": "number"},
                "others_above13": {"type": "number"},
                "subtotal_above13": {"type": "number"},
                "transformers_below13": {"type": "number"},
                "distribution_lines_below13": {"type": "number"},
                "meters_below13": {"type": "number"},
                "it_equipment_below13": {"type": "number"},
                "others_below13": {"type": "number"},
                "subtotal_below13": {"type": "number"},
                "grand_total": {"type": "number"},
            }
        },
        "distribution_loss_pct": {"type": "number"},
        "energy_input_lakh_units": {"type": "number"},
        "energy_sales_lakh_units": {"type": "number"},
        "ronfa_details": {
            "type": "object",
            "properties": {
                "gross_fixed_assets": {"type": "number"},
                "accumulated_depreciation": {"type": "number"},
                "consumer_contribution": {"type": "number"},
                "nfa_for_normative_loan": {"type": "number"},
                "balance_nfa": {"type": "number"},
                "rate_of_return_pct": {"type": "number"},
                "eligible_return": {"type": "number"},
            }
        },
        "claimed_expenses": {
            "type": "object",
            "description": "Expenses CLAIMED by the licensee in the truing-up petition (Rs. Lakhs)",
            "properties": {
                "power_purchase_cost": {"type": "number"},
                "employee_cost": {"type": "number"},
                "repair_maintenance": {"type": "number"},
                "admin_general": {"type": "number"},
                "depreciation": {"type": "number"},
                "interest_long_term": {"type": "number"},
                "return_on_nfa": {"type": "number"},
                "other_debits": {"type": "number"},
                "other_expenses": {"type": "number"},
            }
        },
        "ag_claimed_line_items": {
            "type": "object",
            "description": "A&G sub-items CLAIMED by the licensee (Rs. Lakhs). Use the 'Truing Up' column.",
            "properties": {
                "rent_rates_taxes": {"type": "number"},
                "insurance": {"type": "number"},
                "telephone_postage": {"type": "number"},
                "legal_charges": {"type": "number"},
                "audit_fees": {"type": "number"},
                "travelling_expenses": {"type": "number"},
                "conveyance_vehicle_hire": {"type": "number"},
                "electricity_charges": {"type": "number"},
                "printing_stationery": {"type": "number"},
                "miscellaneous_expenses": {"type": "number"},
                "license_fee": {"type": "number"},
                "security_arrangements": {"type": "number"},
                "gross_ag_expenses": {"type": "number"},
            }
        },
        "rm_claimed_line_items": {
            "type": "object",
            "description": "R&M sub-items CLAIMED by the licensee (Rs. Lakhs)",
            "properties": {
                "plant_machinery": {"type": "number"},
                "buildings": {"type": "number"},
                "lines_cable_networks": {"type": "number"},
                "vehicles": {"type": "number"},
                "lt_lines_upkeeps": {"type": "number"},
                "gross_rm_expenses": {"type": "number"},
            }
        },
    }
}

PROMPT = """You are an expert at extracting financial data from KSERC (Kerala State Electricity Regulatory Commission) trued-up orders.

This PDF is a KSERC Commission Order that trues up a licensee's accounts.

Extract ALL of the following data:

1. **approved_expenses**: The Commission's final approved amounts for each expense head (power purchase cost, employee cost, R&M, A&G, depreciation, interest, RoNFA, other debits, etc.)
2. **approved_revenues**: Commission-approved revenue from sale of power, non-tariff income, wheeling charges
3. **total_approved_expenditure** and **total_approved_revenue**
4. **revenue_gap_surplus**: The final revenue gap (negative) or surplus (positive) approved by the Commission
5. **ag_line_items**: The APPROVED A&G expense sub-items (rent, insurance, legal, audit fees, etc.)
6. **rm_line_items**: The APPROVED R&M sub-items (plant & machinery, buildings, lines & cables, vehicles, etc.)
7. **employee_line_items**: The APPROVED employee cost sub-items (basic salary, DA, LTA, overtime, PF, etc.) from the employee cost comparison table. Use the TRUED UP / APPROVED column.
8. **employee_claimed_line_items**: The CLAIMED employee cost sub-items from the petition column.
9. **energy_sales_by_category**: Energy sales in Lakh Units by tariff category (HT IA Industrial, HT IB Industrial, HT II General, HT III Agriculture, HT IV Commercial, LT I Domestic, LT IV Industries, LT V Agriculture, LT VI General, LT VII Commercial, LT VIII Street Lighting). Use the TRUED UP / APPROVED column.
10. **depreciation_asset_wise**: Depreciation by asset group — for assets above 13 years and below 13 years (transformers, distribution lines, meters, IT equipment, others). Extract depreciation amounts.
11. **distribution_loss_pct**: The actual distribution loss percentage
12. **energy_input_lakh_units** and **energy_sales_lakh_units**
13. **ronfa_details**: RoNFA computation (GFA, accumulated depreciation, consumer contribution, balance NFA, rate, eligible return)
14. **claimed_expenses**: The licensee's CLAIMED values from the petition (not the approved values)
15. **ag_claimed_line_items**: A&G sub-items as CLAIMED by the licensee
16. **rm_claimed_line_items**: R&M sub-items as CLAIMED by the licensee

IMPORTANT:
- Use ONLY the Commission's APPROVED / TRUED UP column values for approved fields
- Use the licensee's CLAIMED / PETITION / TRUING UP column values for claimed fields
- All monetary values in Rs. Lakhs
- If a value is not found, use 0.0
- Look for the final ARR summary table (usually near the end) for total expenditure/revenue
- For employee cost, look for the comparison table that shows Basic Salary, DA, LTA, Overtime, PF, etc.
- For energy sales, look for the table showing sales by tariff category
- For depreciation, look for the asset-wise depreciation table
"""


def extract_one(licensee: str, pdf_path: str) -> dict:
    """Extract trued-up data from a single PDF."""
    logger.info(f"Extracting {licensee} from {Path(pdf_path).name}...")
    
    client = genai.Client(
        api_key=os.environ.get("GOOGLE_API_KEY"),
        http_options={"api_version": "v1alpha"},
    )
    
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    
    response = client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=[pdf_part, PROMPT + "\n\nReturn a JSON object with these top-level keys: approved_expenses, approved_revenues, total_approved_expenditure, total_approved_revenue, revenue_gap_surplus, ag_line_items, rm_line_items, employee_line_items, employee_claimed_line_items, energy_sales_by_category, depreciation_asset_wise, distribution_loss_pct, energy_input_lakh_units, energy_sales_lakh_units, ronfa_details, claimed_expenses, ag_claimed_line_items, rm_claimed_line_items."],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )
    
    data = json.loads(response.text)
    logger.info(f"  {licensee}: extracted {len(data)} top-level fields")
    
    # Log key values
    ae = data.get("approved_expenses", {})
    total_exp = data.get("total_approved_expenditure", 0)
    total_rev = data.get("total_approved_revenue", 0)
    gap = data.get("revenue_gap_surplus", 0)
    logger.info(f"  Total Approved Exp: {total_exp}, Rev: {total_rev}, Gap/Surplus: {gap}")
    logger.info(f"  PPC: {ae.get('power_purchase_cost', 0)}, Emp: {ae.get('employee_cost', 0)}, "
                f"A&G: {ae.get('admin_general', 0)}, R&M: {ae.get('repair_maintenance', 0)}")
    
    return data


def main():
    for licensee, pdf_path in PDFS.items():
        if not Path(pdf_path).exists():
            logger.error(f"  PDF not found: {pdf_path}")
            continue
        
        data = extract_one(licensee, pdf_path)
        
        # Save to Firestore
        save_precedent(licensee, FY, data)
        logger.info(f"  ✓ Saved {licensee} FY {FY} to Firestore\n")
    
    # Verify
    logger.info("=== Verification ===")
    from src.tools.db import get_precedent
    for licensee in PDFS:
        p = get_precedent(licensee, FY)
        if p:
            ae = p.get("approved_expenses", {})
            logger.info(f"{licensee} FY {FY}: PPC={ae.get('power_purchase_cost', 0)}, "
                       f"Emp={ae.get('employee_cost', 0)}, A&G={ae.get('admin_general', 0)}")
        else:
            logger.warning(f"{licensee} FY {FY}: NOT FOUND in Firestore!")


if __name__ == "__main__":
    main()
