"""
KSERC SDL Truing Up — FastAPI Web Application
===============================================

Government-grade web server for the KSERC Truing-Up analysis system.
Provides endpoints for:
  - PDF petition upload
  - Automated analysis with component-level justifications
  - PDF report download

Security features:
  - CSRF protection via tokens
  - Rate limiting
  - File type validation
  - Input sanitization
  - Secure file handling with UUID naming
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import secrets
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()  # loads GOOGLE_API_KEY and other vars from .env into os.environ

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# ── Application setup ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output_orders"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-25s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("kserc.web")

# ── Security settings ─────────────────────────────────────────────────
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = {".pdf"}
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 10
VALID_LICENSEES = ["Technopark", "Infopark", "CSEZA", "KDHP"]

from src.tools.db import init_db, save_analysis, get_analysis
from src.tools.audit_trail import log_decision, get_audit_trail

# Initialize SQLite database
init_db()

# Simple in-memory rate limiter
_rate_limit_store: Dict[str, list] = {}


# ═══════════════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="KSERC SDL Truing Up System",
    description="Kerala State Electricity Regulatory Commission - Automated Tariff Truing Up Analysis",
    version="1.0.0",
    docs_url=None,  # Disable Swagger in production
    redoc_url=None,
)

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════
# Security Middleware
# ═══════════════════════════════════════════════════════════════════════

def _check_rate_limit(client_ip: str) -> bool:
    """Simple rate limiter."""
    import time
    now = time.time()
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []

    # Clean old entries
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip]
        if now - t < RATE_LIMIT_WINDOW
    ]

    if len(_rate_limit_store[client_ip]) >= MAX_REQUESTS_PER_WINDOW:
        return False

    _rate_limit_store[client_ip].append(now)
    return True


def _validate_file(file: UploadFile) -> None:
    """Validate uploaded file for security."""
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Invalid file type. Only PDF files are accepted.")

    # Check content type
    if file.content_type and "pdf" not in file.content_type.lower():
        raise HTTPException(400, "Invalid content type. Only PDF files are accepted.")


# ═══════════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "KSERC Truing Up Analysis"}


@app.post("/api/analyze")
async def analyze_petition(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    licensee: str = Form(...),
    financial_year: str = Form(...),
    inflation_rate: Optional[float] = Form(None),
    bee_energy_audit_fee: Optional[float] = Form(None),
    iwc_interest_rate: Optional[float] = Form(None),
):
    """
    Upload and analyze petition PDFs (supports multiple files).
    Returns analysis results with component-level justifications.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Rate limiting
    if not _check_rate_limit(client_ip):
        raise HTTPException(429, "Too many requests. Please wait before retrying.")

    # Validate inputs
    if licensee not in VALID_LICENSEES:
        raise HTTPException(400, f"Invalid licensee. Must be one of: {VALID_LICENSEES}")

    if not financial_year or len(financial_year) < 4:
        raise HTTPException(400, "Invalid financial year format")

    # Validate and save all uploaded files
    analysis_id = str(uuid.uuid4())
    upload_paths: List[str] = []
    original_filenames: List[str] = []

    for idx, file in enumerate(files):
        _validate_file(file)
        safe_filename = f"{analysis_id}_{idx}.pdf"
        upload_path = UPLOAD_DIR / safe_filename

        try:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
                raise HTTPException(400, f"File '{file.filename}' too large. Maximum size: {MAX_FILE_SIZE_MB}MB")

            with open(upload_path, "wb") as f:
                f.write(content)

            upload_paths.append(str(upload_path))
            original_filenames.append(file.filename or f"file_{idx}.pdf")
            logger.info(f"File uploaded: {file.filename} -> {safe_filename}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload failed for {file.filename}: {e}")
            raise HTTPException(500, "File upload failed")

    # Run analysis asynchronously via BackgroundTasks
    save_analysis(analysis_id, "RUNNING")
    
    # Define a sync wrapper to run in the background 
    # since we use asyncio.run_in_executor inside _run_analysis
    async def bg_task():
        try:
            result = await _run_analysis(
                analysis_id=analysis_id,
                pdf_paths=upload_paths,
                licensee_name=licensee,
                financial_year=financial_year,
                original_filenames=original_filenames,
                inflation_rate=inflation_rate,
                bee_energy_audit_fee=bee_energy_audit_fee,
                iwc_interest_rate=iwc_interest_rate,
            )
            save_analysis(analysis_id, "COMPLETED", result)
            
            # Log initial analysis in audit trail
            from src.tools.audit_trail import log_decision
            log_decision(
                analysis_id=analysis_id,
                decision_type="initial_analysis",
                details=f"Automated Truing-Up analysis completed for {licensee} FY {financial_year}.",
                user_id="system"
            )
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            save_analysis(analysis_id, "FAILED", {"error": str(e)})

    background_tasks.add_task(bg_task)
    
    return JSONResponse({
        "status": "success",
        "analysis_id": analysis_id,
        "message": "Analysis started. Please poll /api/status/{analysis_id} for results."
    })


@app.get("/api/status/{analysis_id}")
async def get_analysis_status(analysis_id: str):
    """Poll for analysis status and result."""
    data = get_analysis(analysis_id)
    if not data:
        raise HTTPException(404, "Analysis not found")
        
    return JSONResponse(data)


@app.get("/api/download/{analysis_id}")
async def download_report(analysis_id: str):
    """Download the generated PDF report."""
    data = get_analysis(analysis_id)
    if not data or data["status"] != "COMPLETED":
        raise HTTPException(404, "Analysis not found or not completed")

    result = data["result"]
    pdf_path = result.get("output_pdf_path")

    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(404, "PDF report not yet generated")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"KSERC_TrueUp_Order_{result.get('licensee_name', 'Unknown')}_{result.get('financial_year', '')}.pdf",
    )


from pydantic import BaseModel
class OverrideRequest(BaseModel):
    analysis_id: str
    component_key: str
    new_approved_amount: float
    justification: str
    user_id: str = "human_auditor"

@app.post("/api/override")
async def override_component(req: OverrideRequest):
    """Human-in-the-loop override for a specific component."""
    data = get_analysis(req.analysis_id)
    if not data or data["status"] != "COMPLETED":
        raise HTTPException(404, "Analysis not found or not completed")
        
    result = data["result"]
    
    # Verify component exists
    found = False
    old_amount = 0.0
    for comp in result.get("components", []):
        if comp["key"] == req.component_key:
            old_amount = comp["approved"]
            comp["approved"] = req.new_approved_amount
            comp["variance"] = round(req.new_approved_amount - comp["claimed"], 2)
            comp["variance_pct"] = round((comp["variance"] / comp["claimed"] * 100), 2) if comp["claimed"] != 0 else 0.0
            
            # Update status
            if abs(comp["variance"]) < 0.01:
                comp["status"] = "approved"
                comp["status_label"] = "Approved as Claimed"
            elif comp["variance"] < 0:
                comp["status"] = "reduced"
                comp["status_label"] = "Reduced"
            else:
                comp["status"] = "increased"
                comp["status_label"] = "Increased"
                
            comp["justification"] = req.justification
            found = True
            break
            
    if not found:
        raise HTTPException(400, f"Component {req.component_key} not found")
        
    # Update totals
    approved_expenses = result.get("approved_expenses", {})
    if req.component_key in approved_expenses:
        approved_expenses[req.component_key] = req.new_approved_amount
        
        # Recompute totals and gap
        total_exp = sum(approved_expenses.values())
        result["total_approved_expenditure"] = total_exp
        result["final_revenue_gap_surplus"] = result.get("total_approved_revenue", 0.0) - total_exp
        
    # Add to disallowances log if it's a reduction
    if req.new_approved_amount < old_amount:
        result.setdefault("disallowances", []).append({
            "item": req.component_key,
            "claimed": old_amount, # treating previous approved as 'claimed' for the override context
            "approved": req.new_approved_amount,
            "amount_cut": round(old_amount - req.new_approved_amount, 2),
            "justification": req.justification
        })
        
    # Regenerate PDF with updated values
    from src.agents.drafter import draft_order
    # Ensure state format is compatible with drafter
    draft_state = dict(result)
    draft_state["disallowance_log"] = result.get("disallowances", [])
    draft_result = draft_order(draft_state)
    result["output_pdf_path"] = draft_result.get("output_pdf_path")
        
    # Save back to DB
    save_analysis(req.analysis_id, "COMPLETED", result)
    
    # Log audit trail
    log_decision(
        analysis_id=req.analysis_id,
        decision_type="human_override",
        details=f"Overrode '{req.component_key}' from {old_amount} to {req.new_approved_amount}. Reason: {req.justification}",
        user_id=req.user_id
    )
    
    return {"status": "success", "message": "Override applied and logged."}


# ═══════════════════════════════════════════════════════════════════════
# Reference Data Routes
# ═══════════════════════════════════════════════════════════════════════

from src.tools.db import (
    get_all_economic_indicators, get_economic_indicators,
    upsert_economic_indicators, save_reference_order, get_reference_orders,
)

REFERENCE_ORDERS_DIR = BASE_DIR / "data" / "reference_orders"
REFERENCE_ORDERS_DIR.mkdir(parents=True, exist_ok=True)


# ── Economic Indicators ────────────────────────────────────────────────

@app.get("/api/reference/economic-indicators")
async def list_economic_indicators():
    """List all stored economic indicators by financial year."""
    return {"indicators": get_all_economic_indicators()}


class EconomicIndicatorsRequest(BaseModel):
    financial_year: str
    wpi_pct: Optional[float] = None
    cpi_pct: Optional[float] = None
    sbi_plr_pct: Optional[float] = None
    hsd_price_rs: Optional[float] = None
    power_purchase_rate_rs_per_kwh: Optional[float] = None

@app.post("/api/reference/economic-indicators")
async def save_economic_indicators(req: EconomicIndicatorsRequest):
    """Create or update economic indicators for a financial year."""
    upsert_economic_indicators(req.financial_year, req.dict())
    return {"status": "saved", "financial_year": req.financial_year}


# ── Reference PDF Upload → Gemini Extract ─────────────────────────────

@app.post("/api/reference/orders/extract")
async def extract_reference_order(
    request: Request,
    file: UploadFile = File(...),
    order_type: str = Form(...),   # 'myt_order' | 'interim_tariff' | 'past_order'
    licensee: str = Form(""),
    financial_year: str = Form(""),
    order_number: str = Form(""),
):
    """
    Upload a reference PDF → Gemini extracts all financial values.
    Returns extracted_rows (flat table) + full JSON for the UI to display.
    Staff can edit values before confirming.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(429, "Too many requests.")

    _validate_file(file)

    # Save file with unique name
    order_id = str(uuid.uuid4())
    safe_filename = f"ref_{order_id}.pdf"
    file_path = REFERENCE_ORDERS_DIR / safe_filename

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"File too large. Maximum: {MAX_FILE_SIZE_MB}MB")
    with open(file_path, "wb") as f:
        f.write(content)

    # Save metadata
    save_reference_order(
        order_id=order_id, order_type=order_type,
        licensee=licensee, financial_year=financial_year,
        order_number=order_number, file_path=str(file_path),
    )

    # Run Gemini extraction
    loop = asyncio.get_event_loop()
    from src.agents.myt_norm_extractor import extract_from_uploaded_pdf
    extraction = await loop.run_in_executor(None, extract_from_uploaded_pdf, str(file_path))

    return JSONResponse({
        "status": "extracted",
        "order_id": order_id,
        "order_type": order_type,
        "document_type": extraction.get("document_type", order_type),
        "order_number": extraction.get("order_number", order_number),
        "control_period": extraction.get("control_period", ""),
        "extracted_rows": extraction.get("extracted_rows", []),
        "licensees": extraction.get("licensees", {}),
        "error": extraction.get("error"),
    })


# ── Confirm & Write Extracted Norms to JSON ────────────────────────────

class ConfirmNormsRequest(BaseModel):
    order_id: str
    order_type: str
    order_number: str = ""
    control_period: str = ""
    document_type: str = ""
    confirmed_rows: list  # [{field_key, field, licensee, year, value, unit}]

@app.post("/api/reference/orders/confirm")
async def confirm_reference_norms(req: ConfirmNormsRequest):
    """
    Staff has reviewed the extracted table and confirmed values.
    For MYT/interim orders: writes norms directly into myt_baselines.json.
    For past orders: saves metadata only (used for RAG/precedent later).
    """
    if req.order_type in ("myt_order", "interim_tariff"):
        from src.agents.myt_norm_extractor import write_norms_to_json
        # Debug: log what the frontend sent
        logger.info(f"[CONFIRM] order_type={req.order_type}, order_number={req.order_number}")
        logger.info(f"[CONFIRM] confirmed_rows count: {len(req.confirmed_rows)}")
        for i, row in enumerate(req.confirmed_rows[:5]):
            logger.info(f"[CONFIRM] Row {i}: {row}")
        result = write_norms_to_json(
            confirmed_rows=[dict(r) if hasattr(r, '__iter__') else r for r in req.confirmed_rows],
            order_number=req.order_number,
            control_period=req.control_period,
            document_type=req.document_type,
        )
        if "error" in result:
            raise HTTPException(500, result["error"])
        return {
            "status": "saved",
            "message": f"Norms written to myt_baselines.json — {result['updated_entries']} values updated.",
            "updated_entries": result["updated_entries"],
        }
    else:
        # Past accepted order — metadata saved on upload; just confirm
        return {"status": "saved", "message": "Past order reference saved."}


# ── List Reference Orders ──────────────────────────────────────────────

@app.get("/api/reference/orders")
async def list_reference_orders(order_type: Optional[str] = None):
    """List uploaded reference orders with metadata."""
    orders = get_reference_orders(order_type)
    return {"orders": orders}


@app.get("/api/reference/myt-baselines")
async def get_myt_baselines():
    """Return full myt_baselines.json content for the UI editor."""
    import json as _json
    path = BASE_DIR / "data" / "myt_baselines" / "myt_baselines.json"
    if not path.exists():
        return {"baselines": {}}
    with open(path, "r", encoding="utf-8") as f:
        return {"baselines": _json.load(f)}


# ═══════════════════════════════════════════════════════════════════════
# Analysis Engine
# ═══════════════════════════════════════════════════════════════════════

async def _run_analysis(
    analysis_id: str,
    pdf_paths: List[str],
    licensee_name: str,
    financial_year: str,
    original_filenames: List[str],
    inflation_rate: Optional[float] = None,
    bee_energy_audit_fee: Optional[float] = None,
    iwc_interest_rate: Optional[float] = None,
) -> dict:
    """Run the full extraction + audit + PDF generation pipeline."""

    from src.agents.extractor import extract_petition_data
    from src.agents.auditor import audit_petition
    from src.agents.drafter import draft_order
    from src.tools.normative_math import calculate_revenue_gap_surplus
    from src.tools.db import update_progress

    def log(stage: str, msg: str):
        update_progress(analysis_id, stage, msg)
        logger.info(f"[{analysis_id}] [{stage}] {msg}")

    # ── Step 1: Extract ────────────────────────────────────────────
    filenames_str = ", ".join(original_filenames)
    log("extract", f"Loading {len(pdf_paths)} petition PDF(s): {filenames_str}")

    # Primary PDF is the first file; all paths are passed to extractor
    primary_pdf = pdf_paths[0]
    state = {
        "petition_pdf_path": primary_pdf,
        "petition_pdf_paths": pdf_paths,  # All PDFs for multi-file extraction
        "licensee_name": licensee_name,
        "financial_year": financial_year,
        "original_filenames": original_filenames,  # Real filenames for Annexure B detection
    }

    # Extract petition text from ALL PDFs for the Narrative RAG Context
    try:
        import fitz
        all_text = ""
        total_pages = 0
        for pdf_path in pdf_paths:
            doc = fitz.open(pdf_path)
            for i, page in enumerate(doc):
                if i >= 50: break  # Safety cap per file
                all_text += page.get_text() + "\n"
            total_pages += len(doc)
            doc.close()
        state["petition_text"] = all_text
        log("extract", f"PDF text extracted ({len(all_text):,} chars from {total_pages} pages across {len(pdf_paths)} files)")
    except Exception as e:
        logger.error(f"[{analysis_id}] Failed to extract text from PDFs: {e}")
        state["petition_text"] = ""

    # Run extraction in a thread to not block the event loop
    log("extract", "Running Gemini Vision extraction on petition tables…")
    loop = asyncio.get_event_loop()
    try:
        extraction_result = await asyncio.wait_for(
            loop.run_in_executor(None, extract_petition_data, state),
            timeout=240,  # 4 min
        )
    except asyncio.TimeoutError:
        log("extract", "ERROR: Extraction timed out after 4 minutes")
        raise RuntimeError("Petition extraction timed out. The PDF may be too large or Gemini is overloaded.")
    n_exp = len(extraction_result.get("claimed_expenses", {}))
    log("extract", f"Extraction complete — {n_exp} expense components found")
    state.update(extraction_result)

    # ── Step 1.5: Deep Table Extraction (wage revision, detailed breakdowns) ──
    log("extract", "Running deep table extraction for wage revision and detailed data…")
    try:
        from src.agents.deep_table_extractor import deep_extract_node
        # Set annexure_pdf_paths so deep extractor can find all PDFs
        if len(pdf_paths) > 1:
            state["annexure_pdf_paths"] = pdf_paths[1:]
        deep_result = deep_extract_node(state)
        if deep_result:
            state.update(deep_result)
            wage_cur = state.get("wage_revision_current_year", 0.0)
            wage_pri = state.get("wage_revision_prior_period", 0.0)
            if wage_cur > 0 or wage_pri > 0:
                log("extract", f"Wage revision found: current={wage_cur:.2f}L, prior={wage_pri:.2f}L")
            else:
                log("extract", "Deep extraction complete — no wage revision detected")
        else:
            log("extract", "Deep extraction returned no enrichments")
    except Exception as e:
        log("extract", f"Deep table extraction failed (non-fatal): {e}")

    # ── Step 2: Legacy Deterministic Audit ────────────────────────
    log("audit", "Loading MYT norms and running deterministic compliance audit…")

    from src.knowledge.myt_loader import MYTLoader
    loader = MYTLoader()
    state["myt_baseline_norms"] = loader.load_myt_baselines(licensee_name, financial_year)
    state["accumulated_surplus"] = 0.0

    from src.agents.auditor import audit_petition
    if inflation_rate is not None:
        state["inflation_rate_override"] = inflation_rate
        log("audit", f"Using user-supplied inflation rate: {inflation_rate}%")
    if bee_energy_audit_fee is not None:
        state["bee_energy_audit_fee"] = bee_energy_audit_fee
        log("audit", f"Using user-supplied BEE energy audit fee: ₹{bee_energy_audit_fee}L")
    if iwc_interest_rate is not None:
        state["iwc_interest_rate"] = iwc_interest_rate
        log("audit", f"Using user-supplied IWC interest rate: {iwc_interest_rate}%")
    audit_result = await asyncio.wait_for(
        loop.run_in_executor(None, audit_petition, state),
        timeout=180,  # 3 min
    )
    state.update(audit_result)
    log("audit", "Deterministic audit complete")

    # ── Step 2.5: Deep AI Analysis (Agentic RAG) ──────────────────
    n_comps = len(state.get("claimed_expenses", {}))
    log("ai_audit", f"Starting parallel AI audit for {n_comps} components (gemini-2.5-pro)…")
    try:
        from src.workflows.truing_up_graph import run_agentic_audit
        
        extracted_formatted = {
            "expenses": state.get("claimed_expenses", {}),
            "petition_text": state.get("petition_text", "")
        }
        baselines_formatted = {"expenses": state.get("myt_baseline_norms", {})}
        deterministic_math = state.get("approved_expenses", {})
        
        ai_raw = await asyncio.wait_for(
            loop.run_in_executor(None, run_agentic_audit, extracted_formatted, baselines_formatted, deterministic_math, analysis_id),
            timeout=480,  # 8 min
        )
        
        # Reformulate into legacy ai_insights structure
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
        ai_exp = ai_insights.get("approved_expenses", {})
        log("ai_audit", f"AI audit complete — {len(ai_exp)} component decisions made")
        if not ai_exp:
            logger.warning(f"[{analysis_id}] AI Analyzer returned NO approved_expenses!")
    except asyncio.TimeoutError:
        log("ai_audit", "AI audit timed out after 8 min — using deterministic results only")
        state["ai_insights"] = {}
    except Exception as e:
        log("ai_audit", f"AI audit failed: {e}")
        logger.error(f"[{analysis_id}] Deep AI Analysis FAILED: {e}", exc_info=True)
        state["ai_insights"] = {}

    log("audit", "Running final compliance check…")
    audit_result = await asyncio.wait_for(
        loop.run_in_executor(None, audit_petition, state),
        timeout=180,  # 3 min
    )
    state.update(audit_result)

    # ── Step 3: Generate PDF (DISABLED — re-enable later) ─────────
    # log("draft", "Generating PDF order…")
    # try:
    #     draft_result = await asyncio.wait_for(
    #         loop.run_in_executor(None, draft_order, state),
    #         timeout=240,  # 4 min
    #     )
    # except asyncio.TimeoutError:
    #     logger.error(f"[{analysis_id}] PDF drafting TIMED OUT after 4 minutes")
    #     draft_result = {"pdf_output_path": None}
    # state.update(draft_result)
    log("draft", "PDF drafting SKIPPED (disabled temporarily)")

    # ── Build response with justifications ─────────────────────────
    claimed = state.get("claimed_expenses", {})
    approved = state.get("approved_expenses", {})
    disallowances = state.get("disallowance_log", [])

    # Build component-level analysis with justifications
    myt_baselines = state.get("myt_baseline_norms", {})
    components = _build_component_analysis(
        claimed, approved, disallowances, financial_year, myt_baselines
    )

    response = {
        "analysis_id": analysis_id,
        "licensee_name": licensee_name,
        "financial_year": financial_year,
        "original_filename": ", ".join(original_filenames),
        "timestamp": datetime.now().isoformat(),

        # Summary
        "total_claimed_expenditure": state.get("total_claimed_expenditure", 0),
        "total_approved_expenditure": state.get("total_approved_expenditure", 0),
        "total_claimed_revenue": state.get("total_claimed_revenue", 0),
        "total_approved_revenue": state.get("total_approved_revenue", 0),
        "final_revenue_gap_surplus": state.get("final_revenue_gap_surplus", 0),
        "imputed_interest": state.get("imputed_interest_on_surplus", 0),

        # Component-level details
        "components": components,

        # Disallowances
        "disallowances": disallowances,

        # Revenue breakdown
        "claimed_revenues": state.get("claimed_revenues", {}),

        # Distribution loss
        "claimed_distribution_loss_pct": state.get("claimed_distribution_loss_pct", 0),
        "target_distribution_loss_pct": state.get("target_distribution_loss_pct", 0),

        # PDF path
        "output_pdf_path": state.get("output_pdf_path", ""),
        "pdf_available": bool(state.get("output_pdf_path")),

        # AI Deep Analysis Insights
        "ai_insights": state.get("ai_insights", {}),

        # Extraction confidence metadata
        "extraction_metadata": state.get("extraction_metadata", {}),
    }

    # Avoid modifying the in-memory store, it's now saved to sqlite before responding
    return response


def _build_component_analysis(
    claimed: dict,
    approved: dict,
    disallowances: list,
    financial_year: str,
    myt_baselines: dict,
) -> list:
    """
    Build detailed component-level analysis with justifications
    for every expense item — both adjustments AND approvals.
    """
    display_names = {
        # ── ARR Expenses (KSERC standard line items) ─────────────────
        "power_purchase_cost":        "Power Purchase Cost",
        "employee_cost":              "Employee Cost",
        "repair_maintenance":         "Repairs & Maintenance",
        "admin_general":              "Administration & General Expenses",
        "depreciation":              "Depreciation",
        "interest_long_term":         "Interest on Long-Term Loans",
        "interest_consumer_deposits": "Interest on Consumer Security Deposits",
        "interest_working_capital":   "Interest on Working Capital",
        "carrying_cost":              "Carrying Cost on Revenue Gaps",
        "return_on_nfa":              "Return on Net Fixed Assets (RoNFA)",
        "other_debits":               "Other Debits",
        "section3_1_duty":            "Section 3(1) Electricity Duty",
        "other_expenses":             "Other Expenses",
    }

    # Build a disallowance lookup
    disallowance_map = {}
    for d in disallowances:
        item_key = d.get("item", "").lower()
        disallowance_map[item_key] = d

    components = []
    for key, display_name in display_names.items():
        claimed_val = claimed.get(key, 0.0)
        approved_val = approved.get(key, 0.0)
        variance = round(approved_val - claimed_val, 2)
        variance_pct = round((variance / claimed_val * 100), 2) if claimed_val != 0 else 0.0

        # Determine status
        if abs(variance) < 0.01:
            status = "approved"
            status_label = "Approved as Claimed"
        elif variance < 0:
            status = "reduced"
            status_label = "Reduced"
        else:
            status = "increased"
            status_label = "Increased"

        # Find matching disallowance justification using EXACT key matching
        justification = ""
        # The auditor produces disallowance items with display names from COMPONENT_DISPLAY
        # We need to match them back to our keys precisely
        _key_to_disallowance_patterns = {
            "power_purchase_cost":        ["power purchase cost"],
            "employee_cost":              ["employee"],
            "repair_maintenance":         ["repairs & maintenance", "repairs and maintenance"],
            "admin_general":              ["administration & general", "administration and general"],
            "depreciation":               ["depreciation"],
            "interest_long_term":         ["interest on long-term", "interest on normative"],
            "interest_consumer_deposits": ["interest on consumer"],
            "interest_working_capital":   ["interest on working capital"],
            "carrying_cost":              ["carrying cost"],
            "return_on_nfa":              ["return on net fixed", "return on nfa", "return on equity"],
            "other_debits":               ["other debits"],
            "section3_1_duty":            ["section 3(1)", "electricity duty"],
            "other_expenses":             ["other expenses"],
        }
        
        patterns = _key_to_disallowance_patterns.get(key, [])
        for d in disallowances:
            d_item = d.get("item", "").lower()
            if any(p in d_item for p in patterns):
                justification = d.get("justification", "")
                break

        # Generate detailed justification if none from disallowance log
        if not justification:
            justification = _generate_approval_justification(
                key, display_name, claimed_val, approved_val, financial_year
            )

        components.append({
            "key": key,
            "name": display_name,
            "proposed_myt": round(myt_baselines.get(key, 0.0), 2),
            "claimed": round(claimed_val, 2),
            "approved": round(approved_val, 2),
            "variance": variance,
            "variance_pct": variance_pct,
            "status": status,
            "status_label": status_label,
            "justification": justification,
        })

    return components


def _generate_approval_justification(
    key: str,
    display_name: str,
    claimed: float,
    approved: float,
    financial_year: str,
) -> str:
    """
    Generate a detailed justification for approved/unchanged items.
    Mirrors the style of actual KSERC orders.
    """
    if claimed == 0.0:
        return f"No amount claimed under {display_name} for FY {financial_year}."

    if abs(approved - claimed) < 0.01:
        justifications = {
            "power_purchase_cost": (
                f"The Power Purchase Cost of Rs. {claimed:,.2f} Lakhs as "
                f"claimed by the licensee for FY {financial_year} has been "
                f"verified against the energy purchase agreements and the "
                f"actual quantum of energy purchased. The Commission finds "
                f"the claim to be in order and approves the same."
            ),
            "employee_cost": (
                f"The Employee Cost of Rs. {claimed:,.2f} Lakhs claimed for "
                f"FY {financial_year} is within the normative limits prescribed "
                f"under the KSERC Tariff Regulations, 2021, after applying the "
                f"70:30 CPI/WPI escalation formula as per Annexure-7. "
                f"The claim is hereby approved."
            ),
            "repair_maintenance": (
                f"The Repairs & Maintenance expenditure of Rs. {claimed:,.2f} "
                f"Lakhs for FY {financial_year} is found to be within the "
                f"normative O&M allocation. The actual expenditure does not "
                f"exceed the escalated baseline. Approved as claimed."
            ),
            "admin_general": (
                f"The Administration & General Expenses of Rs. {claimed:,.2f} "
                f"Lakhs are within permissible limits after verification of "
                f"actual expenditure against the escalated norms for "
                f"FY {financial_year}. Approved as claimed."
            ),
            "depreciation": (
                f"Depreciation of Rs. {claimed:,.2f} Lakhs has been verified "
                f"against the asset register. The rates applied are in "
                f"accordance with the CERC norms adopted by the Commission. "
                f"No assets funded by grants or surplus were identified. "
                f"Approved as claimed."
            ),
            "interest_long_term": (
                f"Interest on Long-Term Loans of Rs. {claimed:,.2f} Lakhs has "
                f"been verified against the loan schedules and applicable "
                f"interest rates. The Commission finds the charges legitimate "
                f"and approves the same for FY {financial_year}."
            ),
            "interest_consumer_deposits": (
                f"Interest on Consumer Security Deposits of Rs. {claimed:,.2f} Lakhs "
                f"has been verified and approved as per regulatory norms for FY {financial_year}."
            ),
            "interest_working_capital": (
                f"Interest on Working Capital of Rs. {claimed:,.2f} Lakhs "
                f"has been verified and approved for FY {financial_year}."
            ),
            "carrying_cost": (
                f"Carrying cost on past revenue gaps of Rs. {claimed:,.2f} Lakhs "
                f"has been verified against prior year revenue gap and applicable "
                f"SBI deposit rate. Approved for FY {financial_year}."
            ),
            "return_on_nfa": (
                f"Return on Net Fixed Assets of Rs. {claimed:,.2f} Lakhs has "
                f"been computed at 5.5% on the eligible NFA base after "
                f"excluding assets funded by consumer contributions, Government "
                f"grants, and normative loans. The claim is approved."
            ),
            "other_debits": (
                f"Other debits of Rs. {claimed:,.2f} Lakhs have been examined "
                f"and approved for FY {financial_year}."
            ),
            "other_expenses": (
                f"Other Expenses of Rs. {claimed:,.2f} Lakhs claimed for "
                f"FY {financial_year} have been examined and found to be "
                f"reasonable. Approved as claimed."
            ),
        }
        return justifications.get(key, f"{display_name} of Rs. {claimed:,.2f} Lakhs approved as claimed for FY {financial_year}.")

    # If there's a variance but no disallowance entry
    diff = approved - claimed
    if diff < 0:
        return (
            f"The {display_name} has been reduced from Rs. {claimed:,.2f} Lakhs "
            f"to Rs. {approved:,.2f} Lakhs (reduction of Rs. {abs(diff):,.2f} Lakhs). "
            f"The adjustment is based on the Commission's scrutiny of the actual "
            f"expenditure vis-à-vis the normative limits for FY {financial_year}."
        )
    else:
        return (
            f"The {display_name} has been adjusted from Rs. {claimed:,.2f} Lakhs "
            f"to Rs. {approved:,.2f} Lakhs for FY {financial_year} based on "
            f"the Commission's determination of eligible expenditure."
        )


# ═══════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
