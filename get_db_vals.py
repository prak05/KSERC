import sqlite3
import json

conn = sqlite3.connect('kserc_analysis.db')
c = conn.cursor()
c.execute('SELECT claimed_expenses, approved_expenses, total_claimed, total_approved, total_revenue, revenue_surplus FROM analysis_results WHERE licensee="KDHP" AND fy="2024-25" ORDER BY created_at DESC LIMIT 1')
res = c.fetchone()

if res:
    print(f"Total Claimed ARR: Rs. {res[2]} Lakhs")
    print(f"Total Approved ARR: Rs. {res[3]} Lakhs")
    print(f"Total Revenue: Rs. {res[4]} Lakhs")
    print(f"Revenue Surplus: Rs. {res[5]} Lakhs\n")
    print("--- Breakdown ---")
    c_exp = json.loads(res[0])
    a_exp = json.loads(res[1])
    
    all_keys = set(c_exp.keys()).union(a_exp.keys())
    for k in sorted(all_keys):
        print(f"{k.ljust(35)} Claimed: {c_exp.get(k, 0):>8.2f} | Approved: {a_exp.get(k, 0):>8.2f}")
else:
    print("No data found for KDHP 2024-25 in analysis_results")
