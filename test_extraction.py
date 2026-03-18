"""Quick test: does Gemini now extract energy_input=548.8 LU with the updated prompt?"""
import sys, os, json, logging
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s")

from src.agents.extractor import extract_petition_data

PDF_DIR = r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\Petition for the approval of Truing up of accounts for the FYs 2024-25. - KDHPCL"
state = {
    "petition_pdf_path": os.path.join(PDF_DIR, "1_Petition.pdf"),
    "petition_pdf_paths": [
        os.path.join(PDF_DIR, "1_Petition.pdf"),
        os.path.join(PDF_DIR, "Annex B_Electricity Audit 2024-25_Audit v6 - with ARR-ERC.pdf"),
    ],
    "licensee_name": "KDHP",
    "financial_year": "2024-25",
}

result = extract_petition_data(state)

print("\n" + "=" * 60)
print("EXTRACTION RESULTS")
print("=" * 60)
print(f"  energy_input_lakh_units:  {result.get('energy_input_lakh_units')}")
print(f"  energy_sales_lakh_units:  {result.get('energy_sales_lakh_units')}")
print(f"  actual_loss_lakh_units:   {result.get('actual_loss_lakh_units')}")
print(f"  appc_rs_per_unit:         {result.get('appc_rs_per_unit')}")
print(f"  power_purchase_cost:      {result.get('claimed_expenses', {}).get('power_purchase_cost')}")
print(f"  employee_cost:            {result.get('claimed_expenses', {}).get('employee_cost')}")
print()
print("EXPECTED:")
print(f"  energy_input_lakh_units:  548.8  (54.88 MU x 10)")
print(f"  appc_rs_per_unit:         6.26")
print(f"  power_purchase_cost:      3434.48")
