import sys, json
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from src.tools.db import get_precedent

p = get_precedent('KDHP', '2023-24')

# Check approved_expenses - should have values
ae = p.get('approved_expenses', {})
print('=== APPROVED EXPENSES (totals) ===')
for k, v in sorted(ae.items()):
    if v and float(v) > 0:
        print(f'  {k}: {v}')

print('\n=== RM APPROVED LINE ITEMS ===')
rm = p.get('rm_line_items', {})
for k, v in sorted(rm.items()):
    print(f'  {k}: {v}')

print('\n=== AG APPROVED LINE ITEMS ===')
ag = p.get('ag_line_items', {})
for k, v in sorted(ag.items()):
    print(f'  {k}: {v}')

print('\n=== RM CLAIMED LINE ITEMS ===')
rmc = p.get('rm_claimed_line_items', {})
for k, v in sorted(rmc.items()):
    print(f'  {k}: {v}')

print('\n=== AG CLAIMED LINE ITEMS ===')
agc = p.get('ag_claimed_line_items', {})
for k, v in sorted(agc.items()):
    print(f'  {k}: {v}')

print('\n=== TOTAL APPROVED ===')
print(f"total_approved_expenditure: {p.get('total_approved_expenditure', 'MISSING')}")
print(f"total_approved_revenue: {p.get('total_approved_revenue', 'MISSING')}")
print(f"revenue_gap_surplus: {p.get('revenue_gap_surplus', 'MISSING')}")
