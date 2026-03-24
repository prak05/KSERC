"""
Firestore-backed database layer for KSERC Truing-Up Engine.

Replaces the previous SQLite implementation with Google Firestore
for persistent cloud storage on Cloud Run.

Collections:
  - analyses/{analysis_id}        → status, result, progress
  - economic_indicators/{fy}      → WPI, CPI, SBI PLR, etc.
  - reference_orders/{order_id}   → order metadata
  - myt_norms/{licensee}/years/{fy} → MYT baseline norms per year
  - precedent_db/{licensee}/years/{fy} → precedent data per year
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger("kserc.db")

# ── Firestore client (lazy singleton) ────────────────────────────────────

_firestore_client = None


def _get_db():
    """Get or create Firestore client. Uses firebase-admin for auth."""
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        # Check if already initialized
        try:
            app = firebase_admin.get_app()
        except ValueError:
            # Not initialized yet — use service account or default credentials
            sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if sa_path and os.path.exists(sa_path):
                cred = credentials.Certificate(sa_path)
                app = firebase_admin.initialize_app(cred, {
                    "projectId": os.getenv("GCP_PROJECT_ID", "kserc-trueup-v2"),
                })
            else:
                # Default credentials (Cloud Run uses attached service account)
                app = firebase_admin.initialize_app(options={
                    "projectId": os.getenv("GCP_PROJECT_ID", "kserc-trueup-v2"),
                })

        _firestore_client = firestore.client()
        logger.info("Firestore client initialized successfully")
        return _firestore_client

    except Exception as e:
        logger.error(f"Failed to initialize Firestore: {e}")
        raise


# ── Init (no-op for Firestore — collections auto-create) ────────────────

def init_db():
    """Initialize database connection. For Firestore, just verify connectivity."""
    try:
        db = _get_db()
        logger.info("Firestore connection verified")
    except Exception as e:
        logger.warning(f"Firestore init check failed: {e}")


# ── Analysis Results ─────────────────────────────────────────────────────

def save_analysis(analysis_id: str, status: str, result: dict = None):
    """Save or update an analysis result."""
    db = _get_db()
    doc_ref = db.collection("analyses").document(analysis_id)

    data = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    if result is not None:
        data["result_json"] = json.dumps(result, default=str)

    # Use merge to avoid overwriting progress_log when updating status
    doc_ref.set(data, merge=True)


def get_analysis(analysis_id: str) -> Optional[dict]:
    """Get analysis status and result."""
    db = _get_db()
    doc = db.collection("analyses").document(analysis_id).get()

    if not doc.exists:
        return None

    data = doc.to_dict()
    result_json = data.get("result_json")
    progress_log = data.get("progress_log")
    # Parse progress_log — ArrayUnion stores entries as JSON strings in a list
    progress = []
    if isinstance(progress_log, list):
        for entry in progress_log:
            if isinstance(entry, str):
                try:
                    progress.append(json.loads(entry))
                except (json.JSONDecodeError, TypeError):
                    progress.append({"msg": entry})
            elif isinstance(entry, dict):
                progress.append(entry)
    elif isinstance(progress_log, str):
        try:
            progress = json.loads(progress_log)
        except (json.JSONDecodeError, TypeError):
            progress = []

    return {
        "status": data.get("status", "UNKNOWN"),
        "result": json.loads(result_json) if result_json else None,
        "progress": progress,
    }


def update_progress(analysis_id: str, stage: str, message: str):
    """Append a timestamped progress entry. Thread-safe via Firestore transactions."""
    from google.cloud.firestore_v1 import ArrayUnion

    ts = datetime.utcnow().strftime("%H:%M:%S")
    entry = {"ts": ts, "stage": stage, "msg": message}

    db = _get_db()
    doc_ref = db.collection("analyses").document(analysis_id)

    # Use ArrayUnion for atomic append
    doc_ref.update({"progress_log": ArrayUnion([json.dumps(entry)])})


# ── Economic Indicators ──────────────────────────────────────────────────

def get_all_economic_indicators() -> list:
    """Get all economic indicators, ordered by financial year descending."""
    db = _get_db()
    docs = db.collection("economic_indicators").order_by(
        "financial_year", direction="DESCENDING"
    ).stream()

    return [doc.to_dict() for doc in docs]


def get_economic_indicators(financial_year: str) -> dict:
    """Get economic indicators for a specific FY."""
    db = _get_db()
    doc = db.collection("economic_indicators").document(financial_year).get()
    if doc.exists:
        data = doc.to_dict()
        return {
            "wpi_pct": data.get("wpi_pct"),
            "cpi_pct": data.get("cpi_pct"),
            "sbi_plr_pct": data.get("sbi_plr_pct"),
            "hsd_price_rs": data.get("hsd_price_rs"),
            "power_purchase_rate_rs_per_kwh": data.get("power_purchase_rate_rs_per_kwh"),
        }
    return {}


def upsert_economic_indicators(financial_year: str, data: dict):
    """Insert or update economic indicators for a FY."""
    db = _get_db()
    doc_data = {
        "financial_year": financial_year,
        "wpi_pct": data.get("wpi_pct"),
        "cpi_pct": data.get("cpi_pct"),
        "sbi_plr_pct": data.get("sbi_plr_pct"),
        "hsd_price_rs": data.get("hsd_price_rs"),
        "power_purchase_rate_rs_per_kwh": data.get("power_purchase_rate_rs_per_kwh"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    db.collection("economic_indicators").document(financial_year).set(doc_data, merge=True)


# ── Reference Orders ────────────────────────────────────────────────────

def save_reference_order(order_id: str, order_type: str, licensee: str,
                         financial_year: str, order_number: str, file_path: str):
    """Save reference order metadata."""
    db = _get_db()
    db.collection("reference_orders").document(order_id).set({
        "order_type": order_type,
        "licensee": licensee,
        "financial_year": financial_year,
        "order_number": order_number,
        "file_path": file_path,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })


def get_reference_orders(order_type: str = None) -> list:
    """Get reference orders, optionally filtered by type."""
    db = _get_db()
    query = db.collection("reference_orders")

    if order_type:
        query = query.where("order_type", "==", order_type)

    query = query.order_by("uploaded_at", direction="DESCENDING")
    return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]


# ── MYT Norms ────────────────────────────────────────────────────────────

def get_myt_norms_override(licensee_name: str, financial_year: str) -> dict:
    """Get MYT norm overrides from Firestore."""
    db = _get_db()
    doc = (db.collection("myt_norms")
           .document(licensee_name)
           .collection("years")
           .document(financial_year)
           .get())

    if doc.exists:
        data = doc.to_dict()
        # Return just the norms, not metadata
        norms = {k: v for k, v in data.items() if k not in ("updated_at", "source")}
        return norms
    return {}


def save_myt_norms(licensee_name: str, financial_year: str, norms: dict, source: str = "manual"):
    """Save MYT norms to Firestore."""
    db = _get_db()
    doc_data = {
        **norms,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }
    (db.collection("myt_norms")
     .document(licensee_name)
     .collection("years")
     .document(financial_year)
     .set(doc_data, merge=True))
    logger.info(f"Saved MYT norms for {licensee_name} FY {financial_year} (source={source})")


def get_all_myt_norms(licensee_name: str) -> dict:
    """Get all MYT norms for a licensee (all FYs)."""
    db = _get_db()
    docs = (db.collection("myt_norms")
            .document(licensee_name)
            .collection("years")
            .stream())

    result = {}
    for doc in docs:
        data = doc.to_dict()
        norms = {k: v for k, v in data.items() if k not in ("updated_at", "source")}
        result[doc.id] = norms
    return result


# ── Precedent DB ─────────────────────────────────────────────────────────

def save_precedent(licensee_name: str, financial_year: str, data: dict):
    """Save precedent data to Firestore."""
    db = _get_db()
    doc_data = {
        **data,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    (db.collection("precedent_db")
     .document(licensee_name)
     .collection("years")
     .document(financial_year)
     .set(doc_data))


def get_precedent(licensee_name: str, financial_year: str) -> dict:
    """Get precedent data for a specific licensee and FY."""
    db = _get_db()
    doc = (db.collection("precedent_db")
           .document(licensee_name)
           .collection("years")
           .document(financial_year)
           .get())
    return doc.to_dict() if doc.exists else {}


def get_all_precedents(licensee_name: str) -> dict:
    """Get all precedent data for a licensee."""
    db = _get_db()
    docs = (db.collection("precedent_db")
            .document(licensee_name)
            .collection("years")
            .stream())
    return {doc.id: doc.to_dict() for doc in docs}
