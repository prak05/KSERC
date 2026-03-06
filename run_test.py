"""
Streamlined test: Extract → Audit → Draft PDF (skips slow Agentic RAG step).
Focuses on testing the new Gemini Markdown-to-PDF drafter.
"""
import asyncio
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-25s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test")

async def main():
    pdf_path = r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\info 2024-25.pdf"
    licensee = "Infopark"
    fy = "2024-25"

    state = {
        "petition_pdf_path": pdf_path,
        "licensee_name": licensee,
        "financial_year": fy,
    }

    # ── Step 0: Extract petition text for context ──
    logger.info("Extracting petition text with PyMuPDF...")
    import fitz
    doc = fitz.open(pdf_path)
    text = ""
    for i, page in enumerate(doc):
        if i >= 50: break
        text += page.get_text() + "\n"
    doc.close()
    state["petition_text"] = text
    logger.info(f"Extracted {len(text)} chars of petition text")

    # ── Step 1: Extract financial data ──
    logger.info("Running extractor...")
    t0 = time.time()
    from src.agents.extractor import extract_petition_data
    loop = asyncio.get_event_loop()
    extraction_result = await loop.run_in_executor(None, extract_petition_data, state)
    state.update(extraction_result)
    logger.info(f"Extraction done in {time.time()-t0:.1f}s")
    logger.info(f"  Claimed expenses: {state.get('claimed_expenses', {})}")

    # ── Step 2: Deterministic Audit ──
    logger.info("Running deterministic audit...")
    t0 = time.time()
    from src.knowledge.myt_loader import MYTLoader
    loader = MYTLoader()
    state["myt_baseline_norms"] = loader.load_myt_baselines(licensee, fy)
    state["accumulated_surplus"] = 0.0

    from src.agents.auditor import audit_petition
    audit_result = await loop.run_in_executor(None, audit_petition, state)
    state.update(audit_result)
    logger.info(f"Audit done in {time.time()-t0:.1f}s")
    logger.info(f"  Approved expenses: {state.get('approved_expenses', {})}")
    logger.info(f"  Total Claimed: {state.get('total_claimed_expenditure', 0):.2f}")
    logger.info(f"  Total Approved: {state.get('total_approved_expenditure', 0):.2f}")
    logger.info(f"  Revenue Gap/Surplus: {state.get('final_revenue_gap_surplus', 0):.2f}")

    # ── Step 3: Draft PDF (Gemini Markdown → xhtml2pdf) ──
    logger.info("Drafting PDF with Gemini 2.5 Pro (this takes 2-4 minutes)...")
    t0 = time.time()
    import traceback
    try:
        from src.agents.drafter import draft_order
        draft_result = await loop.run_in_executor(None, draft_order, state)
        state.update(draft_result)
        logger.info(f"Drafting done in {time.time()-t0:.1f}s")

        pdf_path = state.get("output_pdf_path", "")
        logger.info(f"\n{'='*60}")
        logger.info(f"PDF generated at: {pdf_path}")
        logger.info(f"{'='*60}")
    except Exception as e:
        logger.error(f"Draft failed: {e}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    asyncio.run(main())
