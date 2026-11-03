"""
KSERC Order Builder — Pre-Render Validators
=============================================

Validates the order JSON before HTML rendering.
Returns a list of error strings; empty list = valid.
"""

from __future__ import annotations
from typing import Any


REQUIRED_SECTIONS = [
    "energy_sales", "distribution_loss", "ppc",
    "employee_cost", "rm_expense", "ag_expense",
    "depreciation", "arr_gap",
]

REQUIRED_VALUES = [
    "fy", "licensee_name",
    "claimed_ppc", "approved_ppc",
    "actual_loss_pct", "target_loss_pct",
    "total_claimed_expenditure", "total_approved_expenditure",
    "total_approved_revenue",
]


def validate_order_json(order_json: dict) -> list[str]:
    """
    Run all pre-render checks on the order JSON.
    Returns a list of error strings (empty = valid).
    """
    errors: list[str] = []
    errors.extend(_check_required_sections(order_json))
    errors.extend(_check_duplicate_sections(order_json))
    errors.extend(_check_required_values(order_json))
    errors.extend(_check_paragraph_sequence(order_json))
    errors.extend(_check_arr_arithmetic(order_json))
    return errors


def _check_required_sections(order_json: dict) -> list[str]:
    """Ensure all required sections are present."""
    present = {s["id"] for s in order_json.get("sections", [])}
    errors = []
    for req in REQUIRED_SECTIONS:
        if req not in present:
            errors.append(f"Missing required section: {req}")
    return errors


def _check_duplicate_sections(order_json: dict) -> list[str]:
    """No duplicate section IDs allowed."""
    ids = [s["id"] for s in order_json.get("sections", [])]
    if len(ids) != len(set(ids)):
        dupes = [sid for sid in ids if ids.count(sid) > 1]
        return [f"Duplicate section IDs found: {set(dupes)}"]
    return []


def _check_required_values(order_json: dict) -> list[str]:
    """Required values store keys must be present."""
    values = order_json.get("values", {})
    errors = []
    for key in REQUIRED_VALUES:
        if key not in values:
            errors.append(f"Missing required value: {key}")
    return errors


def _check_paragraph_sequence(order_json: dict) -> list[str]:
    """Paragraph seq values must be strictly increasing with no gaps."""
    all_paras = []
    for block_key in ["introduction", "hearing"]:
        block = order_json.get(block_key, {})
        all_paras.extend(block.get("paragraphs", []))
    for section in order_json.get("sections", []):
        all_paras.extend(section.get("paragraphs", []))

    if not all_paras:
        return []

    errors = []
    expected = all_paras[0].get("seq", 1)
    for p in all_paras:
        seq = p.get("seq", 0)
        if seq != expected:
            errors.append(
                f"Paragraph seq gap: expected {expected}, got {seq}"
            )
            expected = seq  # resync to avoid cascade of errors
        expected += 1

    return errors


def _check_arr_arithmetic(order_json: dict) -> list[str]:
    """
    ARR (expenditure - revenue = gap) must be arithmetically consistent.
    Tolerance: ±0.10 Lakhs.
    """
    values = order_json.get("values", {})
    try:
        approved_arr = float(values.get("total_approved_expenditure", 0))
        approved_revenue = float(values.get("total_approved_revenue", 0))
        computed_gap = approved_revenue - approved_arr
        stated_gap = float(values.get("revenue_gap", computed_gap))
        if abs(computed_gap - stated_gap) > 0.10:
            return [
                f"ARR arithmetic mismatch: computed gap {computed_gap:.2f} "
                f"vs stated {stated_gap:.2f}"
            ]
    except (ValueError, TypeError):
        pass
    return []
