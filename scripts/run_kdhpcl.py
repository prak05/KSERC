"""Submit KDHPCL 2024-25 (all 4 PDFs) and poll for results."""
import requests, time, json, os

BASE = "http://127.0.0.1:8000"
FOLDER = r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\Petition for the approval of Truing up of accounts for the FYs 2024-25. - KDHPCL"

PDF_FILES = [
    "1_Petition.pdf",
    "Annex A1_Electricity Accounts_FY25_Signed.pdf",
    "Annex A_KDHP_Electricity FS_Audit Report Mar 25_Signed.pdf",
    "Annex B_Electricity Audit 2024-25_Audit v6 - with ARR-ERC.pdf",
]

files = []
handles = []
for fname in PDF_FILES:
    path = os.path.join(FOLDER, fname)
    h = open(path, "rb")
    handles.append(h)
    files.append(("files", (fname, h, "application/pdf")))
    print(f"  Adding: {fname}")

print("\nSubmitting KDHPCL 2024-25 ({} files)...".format(len(files)))
r = requests.post(
    f"{BASE}/api/analyze",
    files=files,
    data={"licensee": "KDHP", "financial_year": "2024-25"},
    timeout=600
)
for h in handles:
    h.close()

r.raise_for_status()
aid = r.json().get("analysis_id")
print(f"Submitted — ID: {aid}")

print("\nPolling (every 15s, up to 30 min)...")
for i in range(120):
    time.sleep(15)
    try:
        s = requests.get(f"{BASE}/api/status/{aid}", timeout=300).json()
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
        json.dump(r2, open("results_kdhpcl_2024_25.json", "w"), indent=2, default=str)

        lines = []
        lines.append("=" * 90)
        lines.append(f"KDHPCL FY {r2.get('financial_year', '2024-25')} — Pipeline Results")
        lines.append("=" * 90)
        lines.append("")
        lines.append(f"Total Claimed Expenditure:  Rs. {r2.get('total_claimed_expenditure', 'N/A')} L")
        lines.append(f"Total Approved Expenditure: Rs. {r2.get('total_approved_expenditure', 'N/A')} L")
        lines.append(f"Total Claimed Revenue:      Rs. {r2.get('total_claimed_revenue', 'N/A')} L")
        lines.append(f"Total Approved Revenue:     Rs. {r2.get('total_approved_revenue', 'N/A')} L")
        lines.append(f"Revenue Gap/Surplus:        Rs. {r2.get('final_revenue_gap_surplus', 'N/A')} L")
        lines.append("")
        lines.append("COMPONENT SUMMARY:")
        lines.append(f"{'Component':<40} {'MYT':>8} {'Claimed':>10} {'Approved':>10}  Status")
        lines.append("-" * 90)
        for c in r2.get("components", []):
            n = c["name"][:38]
            myt = str(c.get("proposed_myt", ""))
            cl  = str(c.get("claimed", ""))
            ap  = str(c.get("approved", ""))
            st  = c.get("status", "")
            lines.append(f"  {n:<38} {myt:>8} {cl:>10} {ap:>10}  {st}")

        lines.append("")
        lines.append("DISALLOWANCES:")
        lines.append("-" * 90)
        for d in r2.get("disallowance_log", []):
            cut = d.get("amount_cut", 0)
            if cut and float(str(cut)) > 0:
                lines.append(f"  {d['item'][:55]:<55} Cut: Rs.{float(str(cut)):>9.2f}L")

        out = "\n".join(lines)
        with open("kdhpcl_output.txt", "w", encoding="utf-8") as f:
            f.write(out)
        print("\n\n" + out)
        break
else:
    print("Timed out after 30 minutes!")
