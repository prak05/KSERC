"""Run FULL pipeline locally: extract + deterministic audit on KDHP petition."""
import sys
import os
sys.path.insert(0, r'c:\Users\adwai\OneDrive\Desktop\K-Project\kserc-trueup-engine')

os.environ["GOOGLE_API_KEY"] =
os.environ["GEMINI_MODEL"] = "gemini-2.5-flash"

from src.agents.extractor import extract_petition_data
from src.agents.auditor import audit_petition
import logging
logging.basicConfig(level=logging.WARNING)

pdf_dir = r'C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\Petition for the approval of Truing up of accounts for the FYs 2024-25. - KDHPCL'
pdf_files = sorted([os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.endswith('.pdf')])

# Step 1: Extract
state = {
    "petition_pdf_path": pdf_files[0],
    "annexure_pdf_paths": pdf_files[1:],
    "licensee_name": "KDHP",
    "financial_year": "2024-25",
    "original_filenames": [os.path.basename(f) for f in pdf_files],
}
print("Step 1: Extracting from petition...")
result = extract_petition_data(state)
state.update(result)

claimed = state.get("claimed_expenses", {})
print(f"\n--- CLAIMED EXPENSES ---")
for k, v in sorted(claimed.items()):
    if not k.startswith("__") and v != 0.0:
        print(f"  {k}: Rs. {v} L")

# Step 2: Run full deterministic audit
print(f"\nStep 2: Running deterministic audit...")
audit_result = audit_petition(state)
state.update(audit_result)

approved = state.get("approved_expenses", {})

# Print final comparison table
print(f"\n{'='*70}")
print(f"{'Component':<30} {'Claimed':>12} {'Approved':>12} {'Diff':>10}")
print(f"{'='*70}")
total_claimed = 0
total_approved = 0
for k in sorted(claimed.keys()):
    if k.startswith("__") or claimed.get(k, 0) == 0:
        continue
    c = claimed.get(k, 0)
    a = approved.get(k, c)
    diff = round(a - c, 2)
    total_claimed += c
    total_approved += a
    flag = " ***" if abs(diff) > 0.01 else ""
    print(f"  {k:<28} {c:>12.2f} {a:>12.2f} {diff:>10.2f}{flag}")

print(f"{'='*70}")
print(f"  {'TOTAL':<28} {total_claimed:>12.2f} {total_approved:>12.2f} {round(total_approved-total_claimed,2):>10.2f}")

# PPC specific check
ppc_approved = approved.get("power_purchase_cost", 0)
print(f"\n--- PPC CHECK ---")
print(f"  Claimed PPC:  Rs. {claimed.get('power_purchase_cost', 0)} L")
print(f"  Approved PPC: Rs. {ppc_approved} L")
print(f"  Expected:     Rs. 3415.64 L")
print(f"  Match: {abs(ppc_approved - 3415.64) < 1.0}")

# Disallowances
disallowances = state.get("disallowances", [])
if disallowances:
    print(f"\n--- DISALLOWANCES ---")
    for d in disallowances:
        print(f"  {d.get('item', 'Unknown')}: cut Rs. {d.get('amount_cut', 0)} L")
