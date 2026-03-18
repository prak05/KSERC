"""Quick KDHP full audit test - get all trued up values."""
import sys, os, logging
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
logging.disable(logging.CRITICAL)  # Suppress all logs

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
result = extract_petition_data(state)
state.update(result)

# Step 1.5: Deep table (wage revision)
state["annexure_pdf_paths"] = state["petition_pdf_paths"][1:]
deep = deep_extract_node(state)
if deep:
    state.update(deep)

# Step 2: Audit
loader = MYTLoader()
state["myt_baseline_norms"] = loader.load_myt_baselines("KDHP", "2024-25")
state["accumulated_surplus"] = 0.0
audit = audit_petition(state)
state.update(audit)

# Print
claimed = state.get("claimed_expenses", {})
approved = state.get("approved_expenses", {})
print("=" * 70)
print("KDHP FY 2024-25 TRUED UP VALUES")
print("=" * 70)
components = [
    ("Power Purchase Cost", "power_purchase_cost"),
    ("Employee Cost", "employee_cost"),
    ("Repair & Maintenance", "repair_maintenance"),
    ("Admin & General", "admin_general"),
    ("Depreciation", "depreciation"),
    ("Interest Long Term", "interest_long_term"),
    ("Interest Consumer Dep", "interest_consumer_deposits"),
    ("Interest Working Cap", "interest_working_capital"),
    ("Return on NFA", "return_on_nfa"),
    ("Other Debits", "other_debits"),
    ("Section 3(1) Duty", "section3_1_duty"),
    ("Carrying Cost", "carrying_cost"),
    ("Other Expenses", "other_expenses"),
]
print(f"  {'Component':<25} {'Claimed':>10} {'Approved':>10} {'Diff':>10}")
print("-" * 60)
total_c, total_a = 0, 0
for name, key in components:
    c = claimed.get(key, 0.0)
    a = approved.get(key, 0.0)
    d = round(a - c, 2)
    total_c += c
    total_a += a
    if c > 0 or a > 0:
        print(f"  {name:<25} {c:>10.2f} {a:>10.2f} {d:>10.2f}")

prior = approved.get("prior_period_employee_cost", 0.0)
if prior > 0:
    total_a += prior
    print(f"  {'Prior Period Emp Cost':<25} {'':>10} {prior:>10.2f}")

print("-" * 60)
print(f"  {'TOTAL':<25} {total_c:>10.2f} {total_a:>10.2f} {round(total_a-total_c,2):>10.2f}")
print()
print("KEY ENERGY VALUES:")
print(f"  Energy Input:       {state.get('energy_input_lakh_units')} LU")
print(f"  Energy Sales:       {state.get('energy_sales_lakh_units')} LU")
print(f"  Actual Loss:        {state.get('actual_loss_lakh_units')} LU")
print(f"  APPC:               {state.get('appc_rs_per_unit')} Rs/kWh")
print(f"  Wage Rev Current:   {state.get('wage_revision_current_year', 0)} L")
print(f"  Wage Rev Prior:     {state.get('wage_revision_prior_period', 0)} L")
print(f"  BEE Audit Fee:      {state.get('bee_energy_audit_fee', 0)} L")
print(f"  Dist Loss %:        {state.get('claimed_distribution_loss_pct', 0)}%")
print(f"  Target Loss %:      {state.get('target_distribution_loss_pct', 0)}%")
