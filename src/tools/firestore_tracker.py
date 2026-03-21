"""
firestore_tracker.py
====================
Cross-year Truing-Up Data Persistence for KSERC SDL Auditor.

After each truing-up run, KSERC requires that certain verified data points be
carried forward to the next year's petition review.  This module saves and
loads that data using Firebase Firestore so that the next year's audit can
reference the current year's trued-up values.

Data persisted per licensee per FY
-----------------------------------
  trued_up_om:            dict — approved O&M components (for next year escalation base)
  closing_normative_loan: float — closing normative loan balance (for next year interest calc)
  cumulative_gap_surplus: float — running revenue gap (+) or surplus (-) in lakhs
  capitalised_rm_items:   list  — R&M items directed to be capitalised (GFA additions)
  approved_gfa:           float — approved Gross Fixed Assets at year-end
  consumer_contribution:  float — consumer security deposit balance used in IWC calc
  approved_revenues:      dict  — trued-up revenues for reference
  audit_timestamp:        str   — ISO timestamp of the audit run

Firestore structure
-------------------
  Collection: kserc_truing_up
    Document:  {licensee}_{fy}          (e.g. "KDHP_2022-23")
      Fields:  (all the fields above)

Prerequisites
-------------
  - Firebase Admin SDK: `pip install firebase-admin`
  - Service account JSON at path FIREBASE_SERVICE_ACCOUNT_PATH env var,
    or application-default credentials.
  - Firestore database in the GCP project.

The module degrades gracefully: if Firestore is unavailable, results are
logged and the audit continues without crashing.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Firestore client initialisation (lazy singleton)
# ─────────────────────────────────────────────────────────────────────────────

_db = None          # Firestore client singleton
_init_attempted = False


def _get_firestore():
    """
    Return a Firestore client, initialising Firebase Admin on first call.
    Returns None if Firestore is not configured.
    """
    global _db, _init_attempted
    if _init_attempted:
        return _db
    _init_attempted = True

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        # Try service account JSON first
        sa_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH", "")
        if sa_path and os.path.exists(sa_path):
            cred = credentials.Certificate(sa_path)
            app_name = "kserc_auditor"
            try:
                app = firebase_admin.get_app(app_name)
            except ValueError:
                app = firebase_admin.initialize_app(cred, name=app_name)
            _db = firestore.client(app=app)
            logger.info(f"Firestore initialised with service account: {sa_path}")
        else:
            # Fall back to application-default credentials (Cloud Run / GCE)
            try:
                app = firebase_admin.get_app()
            except ValueError:
                app = firebase_admin.initialize_app()
            _db = firestore.client()
            logger.info("Firestore initialised with application-default credentials")

        return _db

    except ImportError:
        logger.warning(
            "firebase-admin not installed. Firestore cross-year tracking disabled. "
            "Install with: pip install firebase-admin"
        )
        return None
    except Exception as exc:
        logger.warning(f"Firestore init failed: {exc}. Cross-year tracking disabled.")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

COLLECTION = "kserc_truing_up"


def _doc_id(licensee: str, fy: str) -> str:
    """Firestore document ID, e.g. 'KDHP_2022-23'."""
    safe_licensee = licensee.replace(" ", "_").replace("/", "-")
    return f"{safe_licensee}_{fy}"


def save_trued_up_data(
    licensee: str,
    fy: str,
    approved_expenses: Dict[str, float],
    approved_revenues: Dict[str, float],
    disallowances: List[Dict[str, Any]],
    state: Optional[dict] = None,
) -> bool:
    """
    Persist trued-up data to Firestore after an audit run.

    Arguments
    ---------
    licensee          : Human-readable licensee name (e.g. "KDHP")
    fy                : Financial year string (e.g. "2022-23")
    approved_expenses : Dict of component -> approved amount (Lakhs)
    approved_revenues : Dict of revenue component -> approved amount (Lakhs)
    disallowances     : Full disallowance log list
    state             : Full audit state dict (for additional fields)

    Returns True if saved successfully, False otherwise.
    """
    db = _get_firestore()
    if db is None:
        logger.info("Firestore unavailable — cross-year data not saved.")
        return False

    try:
        # ── O&M approvals for next year's escalation base ──────────────────
        trued_up_om = {
            k: round(float(approved_expenses.get(k, 0.0)), 2)
            for k in ("employee_cost", "repair_maintenance", "admin_general")
        }

        # ── Closing normative loan ─────────────────────────────────────────
        closing_normative_loan = 0.0
        if state:
            # Try to get from interest calc results
            closing_normative_loan = float(
                state.get("closing_normative_loan", 0.0) or 0.0
            )

        # ── Revenue gap / surplus ──────────────────────────────────────────
        total_approved_exp = sum(approved_expenses.values())
        total_approved_rev = sum(approved_revenues.values())
        current_gap_surplus = round(total_approved_rev - total_approved_exp, 2)

        # Cumulative: add to previous year's closing balance if available
        prev_data = load_prior_year_data(licensee, fy)
        prev_cumulative = float(
            (prev_data or {}).get("cumulative_gap_surplus", 0.0)
        )
        cumulative_gap_surplus = round(prev_cumulative + current_gap_surplus, 2)

        # ── R&M items directed to be capitalised ──────────────────────────
        capitalised_rm_items = []
        if state:
            one_time_items = state.get("one_time_expenditures", [])
            if isinstance(one_time_items, list):
                capitalised_rm_items = [
                    {
                        "name": item.get("name", ""),
                        "amount": float(item.get("claimed_rs_lakhs", 0.0)),
                        "reason": item.get("classification_reason", ""),
                    }
                    for item in one_time_items
                    if item.get("classification") == "capital"
                ]

        # ── Approved GFA ───────────────────────────────────────────────────
        approved_gfa = 0.0
        if state:
            approved_gfa = float(state.get("approved_gfa", 0.0) or 0.0)
            if approved_gfa == 0.0:
                # Fallback: use gross_fixed_assets from petition data
                approved_gfa = float(state.get("gross_fixed_assets", 0.0) or 0.0)

        # ── Consumer contribution / security deposits ──────────────────────
        consumer_contribution = 0.0
        if state:
            consumer_contribution = float(
                state.get("consumer_security_deposit_balance", 0.0) or 0.0
            )
        payload = {
            "licensee": licensee,
            "financial_year": fy,
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            # O&M base for next year escalation
            "trued_up_om": trued_up_om,
            # Interest on normative loan inputs
            "closing_normative_loan": closing_normative_loan,
            # Revenue gap tracking
            "current_fy_gap_surplus": current_gap_surplus,
            "cumulative_gap_surplus": cumulative_gap_surplus,
            # GFA / capital tracking
            "capitalised_rm_items": capitalised_rm_items,
            "capitalised_rm_total": round(
                sum(x["amount"] for x in capitalised_rm_items), 2
            ),
            "approved_gfa": approved_gfa,
            # IWC inputs
            "consumer_contribution": consumer_contribution,
            # Full approved expense and revenue snapshots
            "approved_expenses_snapshot": {
                k: round(float(v), 2) for k, v in approved_expenses.items()
            },
            "approved_revenues_snapshot": {
                k: round(float(v), 2) for k, v in approved_revenues.items()
            },
        }

        doc_id = _doc_id(licensee, fy)
        db.collection(COLLECTION).document(doc_id).set(payload)
        logger.info(
            f"Firestore: saved cross-year data for {licensee} FY {fy} "
            f"(doc: {COLLECTION}/{doc_id}). "
            f"Gap/Surplus: Rs.{current_gap_surplus:.2f}L | "
            f"Cumulative: Rs.{cumulative_gap_surplus:.2f}L | "
            f"Capitalised R&M: {len(capitalised_rm_items)} items"
        )
        return True

    except Exception as exc:
        logger.error(f"Firestore save failed for {licensee}/{fy}: {exc}")
        return False


def load_prior_year_data(
    licensee: str,
    fy: str,
) -> Optional[Dict[str, Any]]:
    """
    Load the trued-up data from the *prior* financial year for a licensee.

    The prior year is derived by decrementing fy by 1 year.
    e.g. fy="2023-24" -> looks for doc "KDHP_2022-23"

    Returns a dict of the stored data, or None if not found / error.
    """
    db = _get_firestore()
    if db is None:
        return None

    try:
        prior_fy = _decrement_fy(fy)
        if not prior_fy:
            return None
        doc_id = _doc_id(licensee, prior_fy)
        doc = db.collection(COLLECTION).document(doc_id).get()
        if doc.exists:
            data = doc.to_dict()
            logger.info(
                f"Firestore: loaded prior year data for {licensee} FY {prior_fy} "
                f"(doc: {COLLECTION}/{doc_id})"
            )
            return data
        else:
            logger.info(
                f"Firestore: no prior year data for {licensee} FY {prior_fy}"
            )
            return None

    except Exception as exc:
        logger.warning(f"Firestore load failed for {licensee} prior of {fy}: {exc}")
        return None


def load_specific_fy(licensee: str, fy: str) -> Optional[Dict[str, Any]]:
    """Load trued-up data for a specific licensee + FY (not necessarily prior year)."""
    db = _get_firestore()
    if db is None:
        return None
    try:
        doc_id = _doc_id(licensee, fy)
        doc = db.collection(COLLECTION).document(doc_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as exc:
        logger.warning(f"Firestore load_specific_fy failed: {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _decrement_fy(fy: str) -> Optional[str]:
    """
    Given a FY string like "2022-23", return "2021-22".
    Handles formats: "YYYY-YY", "YYYY-YYYY".
    """
    try:
        parts = fy.split("-")
        start_year = int(parts[0])
        prior_start = start_year - 1
        # Reconstruct in the same format
        if len(parts[1]) == 2:
            prior_end = str(prior_start + 1)[-2:]
            return f"{prior_start}-{prior_end}"
        else:
            return f"{prior_start}-{prior_start + 1}"
    except Exception:
        logger.warning(f"Could not decrement FY: {fy!r}")
        return None
