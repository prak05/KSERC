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


# ─────────────────────────────────────────────────────────────────────────────
# Interest & Finance — Prior Year Data Loader
# ─────────────────────────────────────────────────────────────────────────────

INTEREST_COLLECTION = "kserc_interest_finance"


def load_interest_prior_data(
    licensee: str,
    fy: str,
) -> Dict[str, Any]:
    """
    Load the 10 prior-year values needed by the interest finance engine.

    Looks in BOTH the main kserc_truing_up collection AND the dedicated
    kserc_interest_finance collection. The interest collection takes priority.

    Returns dict with 10 keys (missing values default to 0/empty, with warnings).
    Always returns a dict, never None — callers don't need to check for None.

    Values returned:
        1. normative_loan_closing_balance     (float)
        2. cumulative_position_amount         (float, absolute value)
        3. cumulative_position_type           (str, "GAP" or "SURPLUS")
        4. security_deposit_closing_balance   (float)
        5. approved_depreciation              (float)
        6. surplus_funded_additions_list       (list of dicts)
        7. litigation_bg_status               (dict: active, court_ref)
        8. sbi_eblr_april1                    (float)
        9. sbi_retail_td_april1               (float)
       10. approved_revenue_previous_year     (float)
    """
    defaults = {
        "normative_loan_closing_balance": 0.0,
        "cumulative_position_amount": 0.0,
        "cumulative_position_type": "GAP",
        "security_deposit_closing_balance": 0.0,
        "approved_depreciation": 0.0,
        "surplus_funded_additions_list": [],
        "litigation_bg_status": {"active": False, "court_reference": ""},
        "sbi_eblr_april1": 0.0,
        "sbi_retail_td_april1": 0.0,
        "approved_revenue_previous_year": 0.0,
    }

    missing_fields = []

    # Load from both collections
    db = _get_firestore()
    if db is None:
        logger.warning("Firestore unavailable — using all defaults for interest prior data")
        return {**defaults, "missing_fields": list(defaults.keys()), "source": "defaults"}

    prior_fy = _decrement_fy(fy)
    if not prior_fy:
        return {**defaults, "missing_fields": list(defaults.keys()), "source": "defaults"}

    result = dict(defaults)

    try:
        # Try interest-specific collection first
        interest_doc_id = _doc_id(licensee, prior_fy)
        interest_doc = db.collection(INTEREST_COLLECTION).document(interest_doc_id).get()
        interest_data = interest_doc.to_dict() if interest_doc.exists else {}

        # Also load from main collection
        main_doc = db.collection(COLLECTION).document(interest_doc_id).get()
        main_data = main_doc.to_dict() if main_doc.exists else {}

        # Map fields — interest collection overrides main collection where available
        # 1. Normative loan closing
        val = interest_data.get("normative_loan_closing") or main_data.get("closing_normative_loan")
        if val is not None:
            result["normative_loan_closing_balance"] = float(val)
        else:
            missing_fields.append("normative_loan_closing_balance")

        # 2 & 3. Cumulative position
        cum_amount = interest_data.get("cumulative_position_amount") or abs(main_data.get("cumulative_gap_surplus", 0.0))
        cum_type = interest_data.get("cumulative_position_type")
        if cum_type is None:
            # Infer from main collection: positive = surplus, negative = gap
            raw = main_data.get("cumulative_gap_surplus", 0.0)
            cum_type = "SURPLUS" if raw > 0 else "GAP"
            cum_amount = abs(raw)
        result["cumulative_position_amount"] = float(cum_amount)
        result["cumulative_position_type"] = cum_type

        # 4. Security deposit closing
        val = interest_data.get("security_deposit_closing") or main_data.get("consumer_contribution")
        if val is not None:
            result["security_deposit_closing_balance"] = float(val)
        else:
            missing_fields.append("security_deposit_closing_balance")

        # 5. Approved depreciation
        val = interest_data.get("approved_depreciation")
        if val is None:
            expenses_snap = main_data.get("approved_expenses_snapshot", {})
            val = expenses_snap.get("depreciation")
        if val is not None:
            result["approved_depreciation"] = float(val)
        else:
            missing_fields.append("approved_depreciation")

        # 6. Surplus-funded additions list
        val = interest_data.get("surplus_funded_additions_list")
        if isinstance(val, list):
            result["surplus_funded_additions_list"] = val
        # Otherwise keep empty list default

        # 7. Litigation BG status
        val = interest_data.get("litigation_bg_status")
        if isinstance(val, dict):
            result["litigation_bg_status"] = val

        # 8 & 9. Rates
        for rate_key in ("sbi_eblr_april1", "sbi_retail_td_april1"):
            val = interest_data.get(rate_key)
            if val is not None:
                result[rate_key] = float(val)
            else:
                missing_fields.append(rate_key)

        # 10. Approved revenue previous year
        val = interest_data.get("approved_revenue_previous_year")
        if val is None:
            rev_snap = main_data.get("approved_revenues_snapshot", {})
            val = sum(rev_snap.values()) if rev_snap else None
        if val is not None:
            result["approved_revenue_previous_year"] = float(val)
        else:
            missing_fields.append("approved_revenue_previous_year")

        result["missing_fields"] = missing_fields
        result["source"] = "firestore"

        if missing_fields:
            logger.warning(
                f"Interest prior data for {licensee} FY {prior_fy}: "
                f"missing fields: {missing_fields}"
            )
        else:
            logger.info(
                f"Interest prior data loaded for {licensee} FY {prior_fy}: all 10 values present"
            )

        return result

    except Exception as exc:
        logger.error(f"Failed to load interest prior data: {exc}")
        return {**defaults, "missing_fields": list(defaults.keys()), "source": "error"}


def save_interest_finance_data(
    licensee: str,
    fy: str,
    interest_result: Dict[str, Any],
    rates: Dict[str, float],
) -> bool:
    """
    Save interest & finance calculation results to Firestore.

    Saves to dedicated kserc_interest_finance collection with full schema
    per spec Part 8 for cross-year reference by next year's engine.

    Parameters
    ----------
    licensee : str
    fy : str
    interest_result : dict
        Full output from interest_finance_engine.process_interest_finance()
    rates : dict
        Keys: eblr, retail_td, supply_code_sd

    Returns True if saved, False otherwise.
    """
    db = _get_firestore()
    if db is None:
        logger.info("Firestore unavailable — interest finance data not saved.")
        return False

    try:
        # Extract key closing values for next year
        comp_b = interest_result.get("component_b", {})
        comp_d = interest_result.get("component_d", {})
        comp_e = interest_result.get("component_e", {})
        comp_g = interest_result.get("component_g", {})

        payload = {
            "licensee": licensee,
            "financial_year": fy,
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),

            # Key closing balances for next year
            "normative_loan_closing": comp_b.get("closing_balance", 0.0),
            "security_deposit_closing": comp_d.get("opening_balance", 0.0),
            "approved_depreciation": comp_b.get("repayment_depreciation", 0.0),

            # Cumulative position
            "cumulative_position_amount": interest_result.get("cumulative_position_amount", 0.0),
            "cumulative_position_type": interest_result.get("cumulative_position_type", "GAP"),

            # Surplus-funded additions (list for multi-year tracking)
            "surplus_funded_additions_list": interest_result.get("surplus_funded_additions_list", []),

            # Litigation BG status
            "litigation_bg_status": comp_e.get("litigation_bg_status", {"active": False, "court_reference": ""}),

            # Rates used (for reference and auto-fill next year)
            "sbi_eblr_april1": rates.get("eblr", 0.0),
            "sbi_retail_td_april1": rates.get("retail_td", 0.0),

            # Revenue (for next year WC receivables)
            "approved_revenue_previous_year": interest_result.get("approved_revenue_total", 0.0),

            # Bank charges breakdown (for audit trail)
            "bank_charges_breakdown": comp_e.get("items", []),

            # Component totals snapshot
            "component_totals": {
                "A_actual_loan_interest": interest_result.get("component_a", {}).get("interest_rs_lakhs", 0.0),
                "B_normative_loan_interest": comp_b.get("interest_rs_lakhs", 0.0),
                "C_working_capital_interest": interest_result.get("component_c", {}).get("interest_rs_lakhs", 0.0),
                "D_security_deposit_interest": comp_d.get("interest_rs_lakhs", 0.0),
                "E_bank_charges": comp_e.get("total_approved", 0.0),
                "F_carrying_cost": interest_result.get("component_f", {}).get("carrying_cost_rs_lakhs", 0.0),
                "G_notional_surplus_interest": comp_g.get("notional_amount", 0.0),
            },
            "total_approved_interest_expense": interest_result.get("total_approved_interest_expense", 0.0),
            "is_provisional": interest_result.get("is_provisional", False),
        }

        doc_id = _doc_id(licensee, fy)
        db.collection(INTEREST_COLLECTION).document(doc_id).set(payload)
        logger.info(
            f"Firestore: saved interest finance data for {licensee} FY {fy} "
            f"(doc: {INTEREST_COLLECTION}/{doc_id})"
        )
        return True

    except Exception as exc:
        logger.error(f"Firestore interest save failed for {licensee}/{fy}: {exc}")
        return False
