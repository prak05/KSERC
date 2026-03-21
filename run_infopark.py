"""Submit info 2024-25.pdf and poll for results."""
import requests, time, json

BASE = "http://127.0.0.1:8000"
PDF_PATH = r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\info 2024-25.pdf"

with open(PDF_PATH, "rb") as f:
    print("Submitting info 2024-25.pdf...")
    r = requests.post(
        f"{BASE}/api/analyze",
        files=[("files", ("info 2024-25.pdf", f, "application/pdf"))],
        data={"licensee": "Infopark", "financial_year": "2024-25"},
        timeout=120
    )
    r.raise_for_status()
    aid = r.json().get("analysis_id")
    print(f"Submitted — ID: {aid}")

print("\nPolling (every 15s, up to 30 min)...")
for i in range(120):
    time.sleep(15)
    try:
        s = requests.get(f"{BASE}/api/status/{aid}", timeout=120).json()
    except Exception as e:
        print(f"[{(i+1)*15:4d}s] timeout/error: {e}")
        continue
    status = s.get("status", "")
    prog = s.get("progress", [])
    last = prog[-1] if prog else {}
    stage = last.get("stage", "")
    msg = last.get("message", "")[:70]
    print(f"[{(i+1)*15:4d}s] {status:12s} | {stage:20s} — {msg}")
    
    if status in ("COMPLETED", "FAILED"):
        r2 = s.get("result", {})
        json.dump(r2, open("results_infopark_2024_25.json", "w"), indent=2, default=str)
        
        lines = []
        lines.append("=" * 70)
        lines.append(f"Infopark FY {r2.get('financial_year', '2024-25')} — Pipeline Results")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Total Claimed Expenditure:  Rs. {r2.get('total_claimed_expenditure', 'N/A')} L")
        lines.append(f"Total Approved Expenditure: Rs. {r2.get('total_approved_expenditure', 'N/A')} L")
        lines.append(f"Total Claimed Revenue:      Rs. {r2.get('total_claimed_revenue', 'N/A')} L")
        lines.append(f"Total Approved Revenue:     Rs. {r2.get('total_approved_revenue', 'N/A')} L")
        lines.append(f"Revenue Gap/Surplus:        Rs. {r2.get('final_revenue_gap_surplus', 'N/A')} L")
        lines.append("")
        lines.append("COMPONENT SUMMARY:")
        lines.append(f"{'Component':<38} {'MYT':>8} {'Claimed':>10} {'Approved':>10} {'Status'}")
        lines.append("-" * 90)
        for c in r2.get("components", []):
            n = c["name"][:36]
            myt = str(c.get("proposed_myt", ""))
            cl = str(c.get("claimed", ""))
            ap = str(c.get("approved", ""))
            st = c.get("status", "")
            lines.append(f"  {n:<36} {myt:>8} {cl:>10} {ap:>10}  {st}")

        lines.append("")
        lines.append("DISALLOWANCES:")
        lines.append("-" * 70)
        for d in r2.get("disallowance_log", []):
            cut = d.get("amount_cut", 0)
            if cut and float(str(cut)) > 0:
                lines.append(f"  {d['item'][:50]:<50} Cut: Rs.{float(str(cut)):>8.2f}L")

        out = "\n".join(lines)
        with open("infopark_output.txt", "w", encoding="utf-8") as f:
            f.write(out)
        print("\n\n" + out)
        break
else:
    print("Timed out after 30 minutes!")
