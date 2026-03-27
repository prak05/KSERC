"""
KSERC Truing-Up — Anomaly Detection Agent
==========================================
Module  : anomaly_detector.py
Purpose : Flags suspicious patterns in extracted petition data BEFORE
          the rule-based auditor runs, giving it context for edge cases.

WHAT IT DOES:
  Gemini is given the complete extracted financial data and asked to
  reason about year-over-year changes, internal consistency, and
  regulatory red flags. It produces structured anomaly flags with
  severity levels that get stored in state["anomaly_flags"].

INTEGRATION:
  Runs as a new LangGraph node between deep_extract and audit.
  The auditor reads state["anomaly_flags"] to enrich its reasoning.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List
from src.config import GEMINI_MODEL

logger = logging.getLogger("kserc.anomaly_detector")

# ─────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are a senior regulatory auditor at Kerala State Electricity Regulatory
Commission (KSERC). You are reviewing a truing-up petition before formal
audit begins. Your job is to flag anomalies, inconsistencies, and red flags
in the extracted petition data.

WHAT TO LOOK FOR:
1. YEAR-OVER-YEAR SPIKES: Any expense increasing by >20% without explanation
2. INTERNAL INCONSISTENCY: Claimed values that don't add up or contradict each other
3. REGULATORY RED FLAGS: Items that KSERC has historically always disallowed
4. MISSING DATA: Critical fields that are zero or missing but should have values
5. SUSPICIOUS PATTERNS: Very round numbers, identical claims across years, etc.

SEVERITY LEVELS:
- HIGH: Likely signals a material error or deliberate overstatement — must review before audit
- MEDIUM: Warrants closer scrutiny — check against precedent
- LOW: Note for the order but unlikely to be material

Respond with a JSON array of anomaly flags. Each flag must have:
  component, severity (HIGH/MEDIUM/LOW), flag (description), suggested_action

If no anomalies, return an empty array [].
"""

_USER_PROMPT = """
Review the following extracted petition data for {licensee} FY {fy}
and flag any anomalies or red flags.

CLAIMED EXPENSES (Rs. Lakhs):
{claimed_expenses}

MYT NORMS (Rs. Lakhs):
{myt_norms}

ENERGY DATA:
{energy_data}

CAPITAL STRUCTURE:
{capital_structure}

R&M LINE ITEMS (if any):
{rm_items}

Return ONLY a valid JSON array. Example:
[
  {{
    "component": "employee_cost",
    "severity": "HIGH",
    "flag": "Employee cost jumped 45% year-over-year with no wage revision claimed",
    "suggested_action": "Request detailed employee cost breakup and ask if pay revision occurred"
  }}
]
"""


# ─────────────────────────────────────────────────────────────────────
# MAIN DETECTION FUNCTION
# ─────────────────────────────────────────────────────────────────────

def detect_anomalies(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Detect anomalies in extracted petition data.

    Reads from state, writes anomaly_flags and merges into clarification_items.

    Parameters
    ----------
    state : TruingUpState dict

    Returns
    -------
    dict with keys: anomaly_flags, clarification_items (partial)
    """
    licensee = state.get("licensee_name", "Unknown")
    fy = state.get("financial_year", "Unknown")

    logger.info("═" * 60)
    logger.info("ANOMALY DETECTION NODE")
    logger.info(f"Licensee: {licensee}  FY: {fy}")
    logger.info("═" * 60)

    claimed = state.get("claimed_expenses", {})
    myt_norms = state.get("myt_baseline_norms", {})
    detailed = state.get("detailed_tables", {})
    rm_items = state.get("rm_line_items", [])

    energy_data = {
        "energy_input_lakh_units": state.get("energy_input_lakh_units", 0),
        "energy_sales_lakh_units": state.get("energy_sales_lakh_units", 0),
        "actual_loss_lakh_units": state.get("actual_loss_lakh_units", 0),
        "claimed_distribution_loss_pct": state.get("claimed_distribution_loss_pct", 0),
    }

    capital_structure = detailed.get("capital_structure", {})

    try:
        from src.gemini_client import generate

        prompt = _USER_PROMPT.format(
            licensee=licensee,
            fy=fy,
            claimed_expenses=json.dumps(claimed, indent=2),
            myt_norms=json.dumps(myt_norms, indent=2),
            energy_data=json.dumps(energy_data, indent=2),
            capital_structure=json.dumps(capital_structure, indent=2),
            rm_items=json.dumps(rm_items[:10], indent=2) if rm_items else "None provided",
        )

        raw = generate(
            prompt=prompt,
            model=GEMINI_MODEL,
            temperature=0.1,
            response_mime_type="application/json",
            system_instruction=_SYSTEM_PROMPT,
            max_output_tokens=2048,
        )

        anomaly_flags = json.loads(raw)
        if not isinstance(anomaly_flags, list):
            anomaly_flags = []

        # Log summary
        high_count = sum(1 for f in anomaly_flags if f.get("severity") == "HIGH")
        med_count  = sum(1 for f in anomaly_flags if f.get("severity") == "MEDIUM")
        logger.info(
            f"Anomaly Detection: {len(anomaly_flags)} flags found "
            f"({high_count} HIGH, {med_count} MEDIUM)"
        )
        for flag in anomaly_flags:
            logger.info(
                f"  [{flag.get('severity','?')}] {flag.get('component','?')}: "
                f"{flag.get('flag','')[:80]}"
            )

    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        anomaly_flags = []

    # Build clarification items from HIGH anomalies
    clarification_items: List[Dict[str, Any]] = list(
        state.get("clarification_items", [])
    )
    for flag in anomaly_flags:
        if flag.get("severity") == "HIGH":
            clarification_items.append({
                "source": "anomaly_detector",
                "item": flag.get("component", "Unknown"),
                "amount": 0.0,
                "query": flag.get("suggested_action", flag.get("flag", "")),
            })

    return {
        "anomaly_flags": anomaly_flags,
        "clarification_items": clarification_items,
    }
