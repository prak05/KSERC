"""
KSERC Truing-Up v5 — FastAPI Web Server
=========================================

Wraps the adwaith LangGraph pipeline EXACTLY as-is.
Zero modifications to any pipeline files.

Uses LangGraph's MemorySaver checkpointer to support the
interrupt() / Command resume pattern in review_node.

Endpoints
---------
  POST /analyze          — Start pipeline (PDF + metadata)
  GET  /status/{id}      — Poll status (RUNNING|AWAITING_REVIEW|COMPLETED|FAILED)
  POST /review/{id}      — Resume after HITL interrupt (approve or override)
  GET  /download/{id}    — Download generated PDF order
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# ── Ensure backend/src/ is importable ────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-30s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backend.main")

# ── Import adwaith pipeline EXACTLY as-is ────────────────────────────
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.main_graph import build_graph
from src.state import TruingUpState

# Compile graph WITH checkpointer — required for interrupt/resume
_checkpointer = MemorySaver()
_compiled_graph = build_graph().compile(checkpointer=_checkpointer)

# ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="KSERC Truing-Up v5 Backend",
    description="Adwaith LangGraph pipeline — exact backend",
    version="5.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────
# In-memory job store (keyed by analysis_id = LangGraph thread_id)
# ─────────────────────────────────────────────────────────────────────

class JobRecord:
    def __init__(self, analysis_id: str, licensee: str, fy: str, pdf_path: str):
        self.analysis_id  = analysis_id
        self.licensee     = licensee
        self.fy           = fy
        self.pdf_path     = pdf_path
        self.status       = "RUNNING"     # RUNNING|AWAITING_REVIEW|COMPLETED|FAILED
        self.result: Optional[Dict[str, Any]] = None
        self.review_summary: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None

_jobs: Dict[str, JobRecord] = {}
_jobs_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    response: str   # "Approve" or override text


# ─────────────────────────────────────────────────────────────────────
# Pipeline runner — runs LangGraph in a background thread
# Handles the interrupt() by reading the graph state and pausing
# ─────────────────────────────────────────────────────────────────────

def _run_pipeline(job: JobRecord) -> None:
    thread_id = job.analysis_id
    config = {"configurable": {"thread_id": thread_id}}

    valid_licensees = ["Technopark", "Infopark", "CSEZA", "KDHP"]
    if job.licensee not in valid_licensees:
        job.error = f"Invalid licensee: {job.licensee}"
        job.status = "FAILED"
        return

    initial_state: Dict[str, Any] = {
        "licensee_name":                 job.licensee,
        "financial_year":                job.fy,
        "petition_pdf_path":             job.pdf_path,
        "claimed_expenses":              {},
        "claimed_revenues":              {},
        "asset_register":                [],
        "claimed_distribution_loss_pct": 0.0,
        "target_distribution_loss_pct":  0.0,
        "myt_baseline_norms":            {},
        "approved_expenses":             {},
        "disallowance_log":              [],
        "total_claimed_expenditure":     0.0,
        "total_approved_expenditure":    0.0,
        "total_claimed_revenue":         0.0,
        "total_approved_revenue":        0.0,
        "final_revenue_gap_surplus":     0.0,
        "accumulated_surplus":           0.0,
        "imputed_interest_on_surplus":   0.0,
        "human_override_notes":          None,
        "output_pdf_path":               "",
    }

    try:
        logger.info(f"[{thread_id}] Pipeline starting: {job.licensee} FY {job.fy}")

        # Invoke graph — it will pause at the review_node interrupt()
        result = _compiled_graph.invoke(initial_state, config)

        # Check whether we stopped at an interrupt or completed
        graph_state = _compiled_graph.get_state(config)

        if graph_state.next:
            # Graph is interrupted (HITL gate)
            interrupt_payload = _get_interrupt_payload(graph_state)
            job.review_summary = _build_review_summary(graph_state.values, interrupt_payload)
            job.status = "AWAITING_REVIEW"
            logger.info(f"[{thread_id}] Pipeline AWAITING_REVIEW")
        else:
            # Completed without interruption (should not normally happen)
            job.result = _serialize_state(result)
            job.status = "COMPLETED"
            logger.info(f"[{thread_id}] Pipeline COMPLETED")

    except Exception as exc:
        import traceback
        logger.error(f"[{thread_id}] Pipeline FAILED: {exc}")
        logger.error(traceback.format_exc())
        job.error  = str(exc)
        job.status = "FAILED"
        job.result = {"error": str(exc)}


def _resume_pipeline(job: JobRecord, response: str) -> None:
    """Resume a paused pipeline after human review."""
    thread_id = job.analysis_id
    config    = {"configurable": {"thread_id": thread_id}}

    try:
        logger.info(f"[{thread_id}] Resuming pipeline with response: {response!r}")

        # Resume using LangGraph Command — the exact pattern adwaith expects
        result = _compiled_graph.invoke(
            Command(resume=response),
            config,
        )

        graph_state = _compiled_graph.get_state(config)

        if graph_state.next:
            # Another interrupt (shouldn't happen in this graph)
            interrupt_payload = _get_interrupt_payload(graph_state)
            job.review_summary = _build_review_summary(graph_state.values, interrupt_payload)
            job.status = "AWAITING_REVIEW"
        else:
            job.result = _serialize_state(result)
            job.status = "COMPLETED"
            logger.info(f"[{thread_id}] Pipeline COMPLETED after review")

    except Exception as exc:
        import traceback
        logger.error(f"[{thread_id}] Resume FAILED: {exc}")
        logger.error(traceback.format_exc())
        job.error  = str(exc)
        job.status = "FAILED"
        job.result = {"error": str(exc)}


def _get_interrupt_payload(graph_state) -> dict:
    """Extract the interrupt payload from the paused graph state."""
    try:
        # LangGraph stores interrupts in tasks[0].interrupts
        tasks = getattr(graph_state, "tasks", [])
        if tasks:
            interrupts = getattr(tasks[0], "interrupts", [])
            if interrupts:
                return interrupts[0].value if hasattr(interrupts[0], "value") else {}
    except Exception:
        pass
    return {}


def _build_review_summary(state_values: dict, interrupt_payload: dict) -> dict:
    disallowances = state_values.get("disallowance_log", [])
    return {
        "licensee":       state_values.get("licensee_name", ""),
        "financial_year": state_values.get("financial_year", ""),
        "total_claimed":  state_values.get("total_claimed_expenditure", 0.0),
        "total_approved": state_values.get("total_approved_expenditure", 0.0),
        "total_revenue":  state_values.get("total_approved_revenue", 0.0),
        "gap_surplus":    state_values.get("final_revenue_gap_surplus", 0.0),
        "summary_text":   interrupt_payload.get("summary", ""),
        "prompt":         interrupt_payload.get("prompt", "Type 'Approve' or provide override."),
        "disallowances":  [
            {
                "item":          d.get("item", ""),
                "claimed":       round(float(d.get("claimed", 0)), 2),
                "approved":      round(float(d.get("approved", 0)), 2),
                "amount_cut":    round(float(d.get("amount_cut", 0)), 2),
                "justification": d.get("justification", ""),
            }
            for d in disallowances
        ],
    }


def _serialize_state(state: dict) -> dict:
    """Extract JSON-serialisable fields from the final pipeline state."""
    disallowances = state.get("disallowance_log", [])
    return {
        "licensee_name":              state.get("licensee_name", ""),
        "financial_year":             state.get("financial_year", ""),
        "total_claimed_expenditure":  state.get("total_claimed_expenditure", 0.0),
        "total_approved_expenditure": state.get("total_approved_expenditure", 0.0),
        "total_claimed_revenue":      state.get("total_claimed_revenue", 0.0),
        "total_approved_revenue":     state.get("total_approved_revenue", 0.0),
        "final_revenue_gap_surplus":  state.get("final_revenue_gap_surplus", 0.0),
        "imputed_interest_on_surplus":state.get("imputed_interest_on_surplus", 0.0),
        "human_override_notes":       state.get("human_override_notes"),
        "output_pdf_path":            state.get("output_pdf_path", ""),
        "claimed_expenses":           state.get("claimed_expenses", {}),
        "approved_expenses":          state.get("approved_expenses", {}),
        "claimed_revenues":           state.get("claimed_revenues", {}),
        "approved_revenues":          state.get("approved_revenues", {}),
        "disallowance_log": [
            {
                "item":          d.get("item", ""),
                "claimed":       round(float(d.get("claimed", 0)), 2),
                "approved":      round(float(d.get("approved", 0)), 2),
                "amount_cut":    round(float(d.get("amount_cut", 0)), 2),
                "justification": d.get("justification", ""),
            }
            for d in disallowances
        ],
    }


# ─────────────────────────────────────────────────────────────────────
# HTTP Routes
# ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "5.0.0", "backend": "adwaith-exact"}


@app.post("/analyze")
async def analyze(
    background_tasks: BackgroundTasks,
    pdf: UploadFile = File(...),
    licensee: str = Form(...),
    financial_year: str = Form(...),
    accumulated_surplus: float = Form(0.0),
):
    """Start a pipeline job. Returns { analysis_id }."""
    # Save uploaded PDF
    analysis_id = str(uuid.uuid4())
    upload_dir  = BACKEND_DIR / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = upload_dir / f"{analysis_id}.pdf"
    content  = await pdf.read()
    pdf_path.write_bytes(content)
    logger.info(f"Saved PDF: {pdf_path} ({len(content)//1024} KB)")

    job = JobRecord(
        analysis_id=analysis_id,
        licensee=licensee,
        fy=financial_year,
        pdf_path=str(pdf_path),
    )
    with _jobs_lock:
        _jobs[analysis_id] = job

    thread = threading.Thread(target=_run_pipeline, args=(job,), daemon=True)
    thread.start()

    return {"analysis_id": analysis_id}


@app.get("/status/{analysis_id}")
async def get_status(analysis_id: str):
    """Poll job status."""
    with _jobs_lock:
        job = _jobs.get(analysis_id)
    if not job:
        raise HTTPException(404, f"Analysis '{analysis_id}' not found")

    response: Dict[str, Any] = {"status": job.status}

    if job.status == "AWAITING_REVIEW":
        response["review_summary"] = job.review_summary

    if job.status in ("COMPLETED", "FAILED"):
        response["result"] = job.result

    return response


@app.post("/review/{analysis_id}")
async def submit_review(analysis_id: str, body: ReviewRequest):
    """Submit human approval / override — resumes the adwaith pipeline."""
    with _jobs_lock:
        job = _jobs.get(analysis_id)
    if not job:
        raise HTTPException(404, f"Analysis '{analysis_id}' not found")
    if job.status != "AWAITING_REVIEW":
        raise HTTPException(400, f"Job not awaiting review (status={job.status})")

    job.status = "RUNNING"

    thread = threading.Thread(
        target=_resume_pipeline, args=(job, body.response), daemon=True
    )
    thread.start()

    return {"message": "Review submitted", "analysis_id": analysis_id}


@app.get("/download/{analysis_id}")
async def download_pdf(analysis_id: str):
    """Download the generated PDF order."""
    with _jobs_lock:
        job = _jobs.get(analysis_id)
    if not job or job.status != "COMPLETED":
        raise HTTPException(404, "PDF not ready or job not found")

    pdf_path = job.result.get("output_pdf_path", "")
    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(404, "PDF file not found on disk")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=Path(pdf_path).name,
    )


# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
