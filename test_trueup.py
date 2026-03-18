"""Quick test: Full truing up audit with all fixes."""
import sys, os, json, logging
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)-8s | %(message)s")

from src.agents.extractor import extract_petition_data
from src.agents.deep_table_extractor import deep_extract_node
from src.knowledge.myt_loader import MYTLoader
from src.agents.auditor import audit_petition

PDF_DIR = r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\Petition for the approval of Truing up of accounts for the FYs 2024-25. - KDHPCL"
state = {
    "petition_pdf_path": os.path.join(PDF_DIR, "1_Petition.pdf"),
    "petition_pdf_paths": [
        os.path.join(PDF_DIR, "1_Petition.pdf"),
        os.path.join(PDF_DIR, "Annex B_Electricity Audit 2024-25_Audit v6 - with ARR-ERC.pdf"),
    ],
    "original_filenames": ["1_Petition.pdf", "Annex B_Electricity Audit 2024-25_Audit v6 - with ARR-ERC.pdf"],
    "licensee_name": "KDHP",
    "financial_year": "2024-25",
}

# Step 1: Extract
print("=" * 60)
print("STEP 1: EXTRACTION")
result = extract_petition_data(state)
state.update(result)

# Step 1.5: Deep table extraction (wage revision)
print("\n" + "=" * 60)
print("STEP 1.5: DEEP TABLE EXTRACTION")
state["annexure_pdf_paths"] = state["petition_pdf_paths"][1:]
deep_result = deep_extract_node(state)
if deep_result:
    state.update(deep_result)

# Step 2: Load MYT norms + Audit
print("\n" + "=" * 60)
print("STEP 2: AUDIT")
loader = MYTLoader()
state["myt_baseline_norms"] = loader.load_myt_baselines("KDHP", "2024-25")
state["accumulated_surplus"] = 0.0
audit_result = audit_petition(state)
state.update(audit_result)

# Print results
print("\n" + "=" * 60)
print("TRUED UP RESULTS - KDHP FY 2024-25")
print("=" * 60)
claimed = state.get("claimed_expenses", {})
approved = state.get("approved_expenses", {})
print(f"\n{'Component':<30} {'Claimed':>12} {'Approved':>12} {'Diff':>12}")
print("-" * 66)
for key in ["power_purchase_cost", "employee_cost", "repair_maintenance", "admin_general",
            "depreciation", "interest_long_term", "interest_consumer_deposits",
            "interest_working_capital", "return_on_nfa", "other_debits", "section3_1_duty"]:
    c = claimed.get(key, 0.0)
    a = approved.get(key, 0.0)
    d = round(a - c, 2)
    print(f"  {key:<28} {c:>12.2f} {a:>12.2f} {d:>12.2f}")

# Prior period
prior = approved.get("prior_period_employee_cost", 0.0)
if prior > 0:
    print(f"  {'prior_period_employee_cost':<28} {'—':>12} {prior:>12.2f}")

print("-" * 66)
total_c = sum(claimed.get(k, 0.0) for k in claimed)
total_a = sum(approved.get(k, 0.0) for k in approved)
print(f"  {'TOTAL':<28} {total_c:>12.2f} {total_a:>12.2f}")

print(f"\nEnergy Input: {state.get('energy_input_lakh_units')} LU")
print(f"APPC: {state.get('appc_rs_per_unit')} Rs/kWh")
print(f"Wage Rev Current: {state.get('wage_revision_current_year', 0.0)} L")
print(f"Wage Rev Prior: {state.get('wage_revision_prior_period', 0.0)} L")
