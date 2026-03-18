"""
Terminal test for KDHP 2024-25 pipeline with AI path.
"""
import asyncio
import sys
import os
import json
import logging

# Setup
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("test_kdhp_ai")

PDF_DIR = r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\Petition for the approval of Truing up of accounts for the FYs 2024-25. - KDHPCL"
PDF_FILES = [
    os.path.join(PDF_DIR, "1_Petition.pdf"),
    os.path.join(PDF_DIR, "Annex A1_Electricity Accounts_FY25_Signed.pdf"),
    os.path.join(PDF_DIR, "Annex A_KDHP_Electricity FS_Audit Report Mar 25_Signed.pdf"),
    os.path.join(PDF_DIR, "Annex B_Electricity Audit 2024-25_Audit v6 - with ARR-ERC.pdf"),
]

LICENSEE = "KDHP"
FY = "2024-25"

async def main():
    from src.agents.extractor import extract_petition_data
    from src.agents.auditor import audit_petition
    from src.agents.drafter import draft_order
    from src.knowledge.myt_loader import MYTLoader

    # Verify PDFs exist
    for p in PDF_FILES:
        if not os.path.exists(p):
            logger.error(f"PDF not found: {p}")
            return
    logger.info(f"All {len(PDF_FILES)} PDFs found.")

    # Build state
    state = {
        "petition_pdf_path": PDF_FILES[0],
        "petition_pdf_paths": PDF_FILES,
        "licensee_name": LICENSEE,
        "financial_year": FY,
    }

    # Extract text from all PDFs
    import fitz
    all_text = ""
    for pdf_path in PDF_FILES:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            if i >= 50: break
            all_text += page.get_text() + "\n"
        doc.close()
    state["petition_text"] = all_text
    logger.info(f"Extracted {len(all_text):,} chars of text from {len(PDF_FILES)} PDFs")

    # Step 1: Extract
    logger.info("=== STEP 1: EXTRACTION ===")
    loop = asyncio.get_event_loop()
    extraction_result = await loop.run_in_executor(None, extract_petition_data, state)
    state.update(extraction_result)
    logger.info(f"Claimed expenses: {json.dumps(state.get('claimed_expenses', {}), indent=2)}")

    # Step 2: Load MYT norms
    loader = MYTLoader()
    state["myt_baseline_norms"] = loader.load_myt_baselines(LICENSEE, FY)
    state["accumulated_surplus"] = 0.0
    logger.info(f"MYT norms loaded: {json.dumps(state.get('myt_baseline_norms', {}), indent=2)}")

    # Step 3: First deterministic audit
    logger.info("=== STEP 2: DETERMINISTIC AUDIT ===")
    audit_result = await loop.run_in_executor(None, audit_petition, state)
    state.update(audit_result)
    logger.info(f"Approved expenses (deterministic): {json.dumps(state.get('approved_expenses', {}), indent=2)}")

    # Step 4: AI Agentic Audit
    logger.info("=== STEP 3: AI AGENTIC AUDIT ===")
    try:
        from src.workflows.truing_up_graph import run_agentic_audit
        extracted_formatted = {
            "expenses": state.get("claimed_expenses", {}),
            "petition_text": state.get("petition_text", "")
        }
        baselines_formatted = {"expenses": state.get("myt_baseline_norms", {})}
        deterministic_math = state.get("approved_expenses", {})

        ai_raw = await loop.run_in_executor(
            None, run_agentic_audit, extracted_formatted, baselines_formatted, deterministic_math, "test-kdhp"
        )

        approved_exp = {}
        for comp, details in ai_raw.get("expenses", {}).items():
            approved_exp[comp] = {
                "amount": details.get("approved", 0.0),
                "justification": details.get("justification", "No justification provided by AI.")
            }

        ai_insights = {
            "approved_expenses": approved_exp,
            "justifications": {},
            "grants_discovered": {"found": False, "total_lakhs": 0.0, "details": ""},
            "interim_relief": {"found": False, "amount_lakhs": 0.0, "details": ""}
        }
        state["ai_insights"] = ai_insights
        logger.info(f"AI insights: {json.dumps({k: v.get('amount', 'N/A') for k, v in approved_exp.items()}, indent=2)}")
    except Exception as e:
        logger.error(f"AI audit failed: {e}", exc_info=True)
        state["ai_insights"] = {}

    # Step 5: Final audit with AI insights
    logger.info("=== STEP 4: FINAL AUDIT (WITH AI) ===")
    audit_result = await loop.run_in_executor(None, audit_petition, state)
    state.update(audit_result)

    # Print results
    print("\n" + "=" * 70)
    print(f"KDHP 2024-25 FINAL RESULTS (AI PATH)")
    print("=" * 70)
    print(f"Total Claimed Expenditure:  Rs. {state.get('total_claimed_expenditure', 0):,.2f} Lakhs")
    print(f"Total Approved Expenditure: Rs. {state.get('total_approved_expenditure', 0):,.2f} Lakhs")
    print(f"Total Claimed Revenue:      Rs. {state.get('total_claimed_revenue', 0):,.2f} Lakhs")
    print(f"Total Approved Revenue:     Rs. {state.get('total_approved_revenue', 0):,.2f} Lakhs")
    print(f"Revenue Gap/Surplus:        Rs. {state.get('final_revenue_gap_surplus', 0):,.2f} Lakhs")
    print("\nComponent-wise:")
    claimed = state.get("claimed_expenses", {})
    approved = state.get("approved_expenses", {})
    myt = state.get("myt_baseline_norms", {})
    for key in approved:
        c = claimed.get(key, 0)
        a = approved[key]
        m = myt.get(key, 0)
        diff = round(a - c, 2)
        print(f"  {key:35s}  MYT={m:10.2f}  Claimed={c:10.2f}  Approved={a:10.2f}  Var={diff:+10.2f}")

    print(f"\nDisallowances ({len(state.get('disallowance_log', []))}):")
    for d in state.get("disallowance_log", []):
        print(f"  {d['item']}: claimed={d.get('claimed',0):.2f}, approved={d.get('approved',0):.2f}, cut={d.get('amount_cut',0):.2f}")

if __name__ == "__main__":
    asyncio.run(main())
