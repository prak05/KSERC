"""
Precedent Extractor — reads past KSERC truing-up orders and extracts
structured data (claimed vs approved amounts, disallowances, reasoning)
into a precedent database JSON.

Also studies the order format/structure for output generation.
"""

import os
import json
import logging
import fitz  # PyMuPDF
from pathlib import Path
from dotenv import load_dotenv
from src.config import GEMINI_MODEL

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("precedent_extractor")

DOCS_DIR = r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents"
OUTPUT_PATH = r"c:\Users\adwai\OneDrive\Desktop\K-Project\kserc_sdl_truing_up\data\precedent_db\precedent_db.json"

# Past truing-up orders to process
TRUING_UP_ORDERS = [
    {
        "file": "Technopark True-Up 2022-23 (OP 84 2023).pdf",
        "licensee": "Technopark",
        "fy": "2022-23",
        "order_ref": "OP 84/2023"
    },
    {
        "file": "Infopark True-Up 2022-23 (OP 82 2023).pdf",
        "licensee": "Infopark",
        "fy": "2022-23",
        "order_ref": "OP 82/2023"
    },
    {
        "file": "Infopark True-Up 2024-25 (OP 59 2025).pdf",
        "licensee": "Infopark",
        "fy": "2024-25",
        "order_ref": "OP 59/2025"
    },
    {
        "file": "Cochin Special Economic Zone Authority FY 2020-21 Truing Up Order.pdf",
        "licensee": "CSEZA",
        "fy": "2020-21",
        "order_ref": "CSEZA TU 2020-21"
    },
    {
        "file": "Cochin Special Economic Zone Authority FY 2019-20 Truing Up Order.pdf",
        "licensee": "CSEZA",
        "fy": "2019-20",
        "order_ref": "CSEZA TU 2019-20"
    },
    {
        "file": "Cochin Special Economic Zone Authority FY 2018-19 Truing Up Order.pdf",
        "licensee": "CSEZA",
        "fy": "2018-19",
        "order_ref": "CSEZA TU 2018-19"
    },
    {
        "file": "Kannan Devan Hills Plantations Company FY 2022-23 Truing Up Order.pdf",
        "licensee": "KDHP",
        "fy": "2022-23",
        "order_ref": "KDHP TU 2022-23"
    },
    {
        "file": "Kannan Devan Hills Plantations Company FY 2021-22 Truing Up Order.pdf",
        "licensee": "KDHP",
        "fy": "2021-22",
        "order_ref": "KDHP TU 2021-22"
    },
    {
        "file": "Kannan Devan Hills Plantations Company FY 2013-14 Truing Up Order.pdf",
        "licensee": "KDHP",
        "fy": "2013-14",
        "order_ref": "KDHP TU 2013-14"
    },
]

EXTRACTION_PROMPT = """You are an expert analyst reading an official KSERC Truing-Up Order.

TASK: Extract ALL financial data from this document into a structured JSON. Read EVERY page carefully.

Return this EXACT JSON schema:

{
    "order_structure": {
        "sections": ["list of main section headings in order, e.g. 'Energy Requirement and Distribution Loss', 'Power Purchase Cost', 'Employee Cost', etc."],
        "has_numbered_paragraphs": true,
        "has_tables": true,
        "total_paragraphs": 68
    },
    "energy_data": {
        "total_energy_purchased_lakh_units": 0.0,
        "energy_sold_lakh_units": 0.0,
        "actual_distribution_loss_pct": 0.0,
        "approved_distribution_loss_pct": 0.0,
        "target_distribution_loss_pct": 0.0
    },
    "claimed_expenses": {
        "power_purchase_cost": 0.0,
        "employee_cost": 0.0,
        "repair_maintenance": 0.0,
        "admin_general": 0.0,
        "depreciation": 0.0,
        "interest_long_term": 0.0,
        "interest_consumer_deposits": 0.0,
        "interest_working_capital": 0.0,
        "carrying_cost": 0.0,
        "return_on_nfa": 0.0,
        "other_debits": 0.0,
        "section3_1_duty": 0.0
    },
    "approved_expenses": {
        "power_purchase_cost": 0.0,
        "employee_cost": 0.0,
        "repair_maintenance": 0.0,
        "admin_general": 0.0,
        "depreciation": 0.0,
        "interest_long_term": 0.0,
        "interest_consumer_deposits": 0.0,
        "interest_working_capital": 0.0,
        "carrying_cost": 0.0,
        "return_on_nfa": 0.0,
        "other_debits": 0.0,
        "section3_1_duty": 0.0
    },
    "claimed_revenues": {
        "revenue_from_sale": 0.0,
        "non_tariff_income": 0.0,
        "wheeling_charges": 0.0,
        "other_revenue": 0.0
    },
    "approved_revenues": {
        "revenue_from_sale": 0.0,
        "non_tariff_income": 0.0,
        "wheeling_charges": 0.0,
        "other_revenue": 0.0
    },
    "capital_structure": {
        "gross_fixed_assets": 0.0,
        "accumulated_depreciation": 0.0,
        "net_fixed_assets": 0.0,
        "consumer_contribution": 0.0,
        "grants_subsidies": 0.0,
        "normative_loan_70pct": 0.0,
        "normative_equity_30pct": 0.0,
        "weighted_avg_interest_rate_pct": 0.0
    },
    "interim_relief": {
        "interim_order_ref": "",
        "interim_amount_lakhs": 0.0,
        "adjusted_in_final": true
    },
    "key_disallowances": [
        {
            "component": "employee_cost",
            "claimed": 0.0,
            "approved": 0.0,
            "kserc_reasoning": "Quote KSERC's exact reasoning for this disallowance from the order text"
        }
    ],
    "final_result": {
        "total_expenditure_claimed": 0.0,
        "total_expenditure_approved": 0.0,
        "total_revenue_approved": 0.0,
        "revenue_gap_surplus": 0.0,
        "cumulative_gap_surplus": 0.0,
        "imputed_interest_on_surplus": 0.0
    }
}

CRITICAL RULES:
1. All amounts are in Rs. Lakhs
2. For key_disallowances, COPY the exact reasoning text from the order — don't summarize
3. If a field is not mentioned, leave it as 0.0 or empty string
4. Look for the main ARR comparison table (usually near the end) — it has both claimed and approved columns
5. Extract capital structure (GFA, depreciation, NFA, grants) from asset tables if present
6. Check for any interim relief/tariff adjustment mentioned
"""


def _render_pdf_pages(pdf_path: str, max_pages: int = 35, dpi: int = 200):
    """Render PDF pages as PNG images."""
    doc = fitz.open(pdf_path)
    images = []
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    for i in range(min(len(doc), max_pages)):
        pix = doc[i].get_pixmap(matrix=matrix)
        images.append(pix.tobytes("png"))
        logger.info(f"  Rendered page {i+1}/{min(len(doc), max_pages)}")
    doc.close()
    return images


def extract_from_order(order_info: dict) -> dict:
    """Extract structured data from a single truing-up order PDF using Gemini Vision."""
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
    import re

    filepath = os.path.join(DOCS_DIR, order_info["file"])
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        return {}

    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {order_info['file']}")
    logger.info(f"Licensee: {order_info['licensee']} | FY: {order_info['fy']}")
    logger.info(f"{'='*60}")

    # Render pages
    images = _render_pdf_pages(filepath)
    logger.info(f"Rendered {len(images)} pages")

    # Set up Vertex AI
    key_path = os.path.abspath("vertex_sa.json")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
    vertexai.init(project="triple-cab-488111-f5", location="us-central1")

    # Build parts
    parts = [Part.from_text(text=EXTRACTION_PROMPT)]
    for png_bytes in images:
        parts.append(Part.from_data(data=png_bytes, mime_type="image/png"))

    model = GenerativeModel(
        GEMINI_MODEL,
        system_instruction=(
            "You are an expert KSERC financial data analyst. "
            "Extract exact numbers from the truing-up order. All amounts in Rs. Lakhs. "
            "Return ONLY valid JSON. No markdown."
        )
    )

    try:
        response = model.generate_content(
            contents=parts,
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=0.0,
            )
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        data = json.loads(raw)
        
        # Add metadata
        data["_meta"] = {
            "licensee": order_info["licensee"],
            "fy": order_info["fy"],
            "order_ref": order_info["order_ref"],
            "source_file": order_info["file"],
            "pages_processed": len(images)
        }

        logger.info(f"✅ Extracted successfully!")
        
        # Log key numbers
        ae = data.get("approved_expenses", {})
        total_approved = sum(v for v in ae.values() if isinstance(v, (int, float)))
        logger.info(f"   Total approved expenditure: Rs. {total_approved:.2f} Lakhs")
        
        fr = data.get("final_result", {})
        logger.info(f"   Revenue gap/surplus: Rs. {fr.get('revenue_gap_surplus', 0):.2f} Lakhs")
        
        kd = data.get("key_disallowances", [])
        logger.info(f"   Key disallowances: {len(kd)}")
        for d in kd:
            logger.info(f"     - {d.get('component')}: claimed {d.get('claimed')}, approved {d.get('approved')}")

        return data

    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        return {}


def build_precedent_db():
    """Build the complete precedent database from all past orders."""
    precedent_db = {}

    for order_info in TRUING_UP_ORDERS:
        data = extract_from_order(order_info)
        if not data:
            continue

        licensee = order_info["licensee"]
        fy = order_info["fy"]

        if licensee not in precedent_db:
            precedent_db[licensee] = {}

        precedent_db[licensee][fy] = data

    # Save
    output_dir = os.path.dirname(OUTPUT_PATH)
    os.makedirs(output_dir, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(precedent_db, f, indent=2, ensure_ascii=False)

    logger.info(f"\n{'='*60}")
    logger.info(f"Precedent DB saved to: {OUTPUT_PATH}")
    logger.info(f"Licensees: {list(precedent_db.keys())}")
    for lic, fys in precedent_db.items():
        logger.info(f"  {lic}: {list(fys.keys())}")
    logger.info(f"{'='*60}")

    return precedent_db


def extract_single_order(order_index: int = 0):
    """Extract from a single order for testing."""
    order_info = TRUING_UP_ORDERS[order_index]
    data = extract_from_order(order_info)
    
    if data:
        # Save to temp location for review
        temp_path = os.path.join(os.path.dirname(OUTPUT_PATH), f"test_{order_info['licensee']}_{order_info['fy']}.json")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Test output saved to: {temp_path}")
    
    return data


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Build full precedent DB
        build_precedent_db()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test with first order
        idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        extract_single_order(idx)
    else:
        print("Usage:")
        print("  python precedent_extractor.py --test [index]  # Test single order")
        print("  python precedent_extractor.py --all           # Build full DB")
        print(f"\nAvailable orders ({len(TRUING_UP_ORDERS)}):")
        for i, o in enumerate(TRUING_UP_ORDERS):
            print(f"  [{i}] {o['licensee']} FY {o['fy']} — {o['file']}")
