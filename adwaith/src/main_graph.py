"""
KSERC SDL Truing Up — LangGraph Orchestrator
==============================================

Wires the three agents (Extractor → Auditor → Drafter) into a
LangGraph StateGraph with Human-in-the-Loop approval before drafting.

Graph: Extract → Audit → Review (HITL interrupt) → Draft

Usage
-----
    from src.main_graph import run_pipeline

    result = run_pipeline(
        licensee_name="Technopark",
        financial_year="2022-23",
        petition_pdf_path="data/input_petitions/technopark_2022_23.pdf",
    )
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command

from src.state import TruingUpState
from src.agents.extractor import extract_petition_data
from src.agents.auditor import audit_petition
from src.agents.drafter import draft_order

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-30s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
)


# ═══════════════════════════════════════════════════════════════════════
# Node Functions
# ═══════════════════════════════════════════════════════════════════════

def extract_node(state: TruingUpState) -> dict:
    """Node 1: Extract data from the petition PDF."""
    logger.info("═" * 60)
    logger.info("NODE 1: EXTRACTION")
    logger.info("═" * 60)
    return extract_petition_data(state)


def audit_node(state: TruingUpState) -> dict:
    """Node 2: Apply compliance rules and audit the petition."""
    logger.info("═" * 60)
    logger.info("NODE 2: COMPLIANCE AUDIT")
    logger.info("═" * 60)
    return audit_petition(state)


def review_node(state: TruingUpState) -> dict:
    """
    Node 3: Human-in-the-Loop review.

    Pauses execution and displays a summary. Waits for human
    approval or override before proceeding to PDF drafting.
    """
    logger.info("═" * 60)
    logger.info("NODE 3: HUMAN REVIEW (INTERRUPT)")
    logger.info("═" * 60)

    # ── Build summary for human review ─────────────────────────────
    licensee = state["licensee_name"]
    fy = state["financial_year"]
    claimed = state.get("total_claimed_expenditure", 0.0)
    approved = state.get("total_approved_expenditure", 0.0)
    revenue = state.get("total_approved_revenue", 0.0)
    gap_surplus = state.get("final_revenue_gap_surplus", 0.0)
    disallowances = state.get("disallowance_log", [])

    summary_lines = [
        "",
        "┌─────────────────────────────────────────────────────────┐",
        "│            TRUING UP AUDIT SUMMARY                     │",
        "├─────────────────────────────────────────────────────────┤",
        f"│  Licensee:       {licensee:<40}│",
        f"│  Financial Year: {fy:<40}│",
        "├─────────────────────────────────────────────────────────┤",
        f"│  Total Claimed Expenditure:  Rs. {claimed:>12,.2f} Lakhs  │",
        f"│  Total Approved Expenditure: Rs. {approved:>12,.2f} Lakhs  │",
        f"│  Total Approved Revenue:     Rs. {revenue:>12,.2f} Lakhs  │",
        f"│  Revenue Gap/Surplus:        Rs. {gap_surplus:>12,.2f} Lakhs  │",
        "├─────────────────────────────────────────────────────────┤",
        f"│  Disallowances: {len(disallowances)} item(s)                            │",
    ]

    for i, d in enumerate(disallowances, 1):
        item_name = d.get("item", "Unknown")[:35]
        amount = d.get("amount_cut", 0.0)
        summary_lines.append(
            f"│    {i}. {item_name:<35} Rs. {amount:>8,.2f} │"
        )

    summary_lines.extend([
        "└─────────────────────────────────────────────────────────┘",
        "",
    ])

    summary_text = "\n".join(summary_lines)

    # ── Interrupt for human approval ───────────────────────────────
    human_response = interrupt({
        "summary": summary_text,
        "prompt": (
            'Type "Approve" to generate the PDF order, or provide '
            'an override instruction (e.g., "Allow Rs 56 Lakhs for '
            'new Technocity campus").'
        ),
        "total_claimed": claimed,
        "total_approved": approved,
        "total_revenue": revenue,
        "gap_surplus": gap_surplus,
        "disallowance_count": len(disallowances),
    })

    # ── Process human response ─────────────────────────────────────
    if isinstance(human_response, str):
        response_text = human_response.strip()
    elif isinstance(human_response, dict):
        response_text = human_response.get("response", "Approve")
    else:
        response_text = str(human_response)

    if response_text.lower() == "approve":
        logger.info("Human APPROVED the audit. Proceeding to drafting.")
        return {"human_override_notes": None}
    else:
        # Parse override instruction
        logger.info(f"Human override: {response_text}")

        # Simple override parsing — look for amount adjustments
        # Format: "Allow Rs X Lakhs for <item>"
        import re
        match = re.search(
            r"allow\s+rs\.?\s*([\d,.]+)\s*lakhs?\s+for\s+(.+)",
            response_text,
            re.IGNORECASE,
        )

        if match:
            override_amount = float(match.group(1).replace(",", ""))
            override_item = match.group(2).strip()

            # Try to find and update the matching expense
            approved_expenses = dict(state.get("approved_expenses", {}))
            updated = False

            for key, display in {
                "power_purchase_cost": "power purchase",
                "employee_cost": "employee",
                "repair_maintenance": "repair",
                "admin_general": "admin",
                "depreciation": "depreciation",
                "interest_finance": "interest",
                "return_on_nfa": "return on nfa",
                "other_expenses": "other",
            }.items():
                if display in override_item.lower() or key in override_item.lower():
                    approved_expenses[key] = override_amount
                    updated = True
                    logger.info(
                        f"Override applied: {key} set to Rs. {override_amount} Lakhs"
                    )
                    break

            if updated:
                # Recalculate totals
                total_approved = sum(
                    v for k, v in approved_expenses.items()
                    if k != "section3_1_duty"
                )
                from src.tools.normative_math import calculate_revenue_gap_surplus
                gap_result = calculate_revenue_gap_surplus(
                    revenue, total_approved
                )

                return {
                    "approved_expenses": approved_expenses,
                    "total_approved_expenditure": total_approved,
                    "final_revenue_gap_surplus": gap_result["revenue_gap_surplus_rs_lakhs"],
                    "human_override_notes": response_text,
                }

        # If override parsing fails, just record the note
        return {"human_override_notes": response_text}


def draft_node(state: TruingUpState) -> dict:
    """Node 4: Generate the final PDF order."""
    logger.info("═" * 60)
    logger.info("NODE 4: PDF ORDER GENERATION")
    logger.info("═" * 60)
    return draft_order(state)


# ═══════════════════════════════════════════════════════════════════════
# Graph Construction
# ═══════════════════════════════════════════════════════════════════════

def build_graph() -> StateGraph:
    """
    Construct the LangGraph StateGraph:
        START → extract → audit → review → draft → END
    """
    graph = StateGraph(TruingUpState)

    # Add nodes
    graph.add_node("extract", extract_node)
    graph.add_node("audit", audit_node)
    graph.add_node("review", review_node)
    graph.add_node("draft", draft_node)

    # Define edges
    graph.add_edge(START, "extract")
    graph.add_edge("extract", "audit")
    graph.add_edge("audit", "review")
    graph.add_edge("review", "draft")
    graph.add_edge("draft", END)

    return graph


# Compile the graph
graph = build_graph()
compiled_graph = graph.compile()


# ═══════════════════════════════════════════════════════════════════════
# Pipeline Runner
# ═══════════════════════════════════════════════════════════════════════

def run_pipeline(
    licensee_name: str,
    financial_year: str,
    petition_pdf_path: str,
    myt_baseline_norms: Dict[str, float] | None = None,
    accumulated_surplus: float = 0.0,
    thread_id: str = "default",
) -> dict:
    """
    Execute the full Truing-Up pipeline.

    Parameters
    ----------
    licensee_name : str
        One of: Technopark, Infopark, CSEZA, KDHP
    financial_year : str
        e.g. "2022-23"
    petition_pdf_path : str
        Path to the petition PDF file.
    myt_baseline_norms : dict, optional
        MYT-approved baseline norms for O&M comparison.
    accumulated_surplus : float
        Previous accumulated regulatory surplus.
    thread_id : str
        LangGraph thread identifier for persistence.

    Returns
    -------
    dict
        Final state after pipeline completion.
    """
    # Validate licensee
    valid_licensees = ["Technopark", "Infopark", "CSEZA", "KDHP"]
    if licensee_name not in valid_licensees:
        raise ValueError(
            f"Invalid licensee '{licensee_name}'. "
            f"Must be one of: {valid_licensees}"
        )

    # Validate PDF exists
    if not Path(petition_pdf_path).exists():
        raise FileNotFoundError(
            f"Petition PDF not found: {petition_pdf_path}"
        )

    # Build initial state
    initial_state: Dict[str, Any] = {
        "licensee_name": licensee_name,
        "financial_year": financial_year,
        "petition_pdf_path": petition_pdf_path,
        "claimed_expenses": {},
        "claimed_revenues": {},
        "asset_register": [],
        "claimed_distribution_loss_pct": 0.0,
        "target_distribution_loss_pct": 0.0,
        "myt_baseline_norms": myt_baseline_norms or {},
        "approved_expenses": {},
        "disallowance_log": [],
        "total_claimed_expenditure": 0.0,
        "total_approved_expenditure": 0.0,
        "total_claimed_revenue": 0.0,
        "total_approved_revenue": 0.0,
        "final_revenue_gap_surplus": 0.0,
        "accumulated_surplus": accumulated_surplus,
        "imputed_interest_on_surplus": 0.0,
        "human_override_notes": None,
        "output_pdf_path": "",
    }

    config = {"configurable": {"thread_id": thread_id}}

    logger.info(f"Starting pipeline for {licensee_name} FY {financial_year}")
    logger.info(f"PDF: {petition_pdf_path}")

    # Run the graph
    result = compiled_graph.invoke(initial_state, config)

    logger.info("Pipeline complete!")
    if result.get("output_pdf_path"):
        logger.info(f"Output PDF: {result['output_pdf_path']}")

    return result


# ═══════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="KSERC SDL Truing Up — Multi-Agent Pipeline"
    )
    parser.add_argument(
        "--licensee",
        required=True,
        choices=["Technopark", "Infopark", "CSEZA", "KDHP"],
        help="Name of the SDL licensee",
    )
    parser.add_argument(
        "--fy",
        required=True,
        help='Financial year (e.g. "2022-23")',
    )
    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to the petition PDF file",
    )
    parser.add_argument(
        "--surplus",
        type=float,
        default=0.0,
        help="Accumulated regulatory surplus (Rs. Lakhs)",
    )

    args = parser.parse_args()

    result = run_pipeline(
        licensee_name=args.licensee,
        financial_year=args.fy,
        petition_pdf_path=args.pdf,
        accumulated_surplus=args.surplus,
    )

    print("\n" + "═" * 60)
    print("PIPELINE RESULT")
    print("═" * 60)
    print(f"  Licensee:         {result.get('licensee_name')}")
    print(f"  Financial Year:   {result.get('financial_year')}")
    print(f"  Total Claimed:    Rs. {result.get('total_claimed_expenditure', 0):,.2f} Lakhs")
    print(f"  Total Approved:   Rs. {result.get('total_approved_expenditure', 0):,.2f} Lakhs")
    print(f"  Gap/Surplus:      Rs. {result.get('final_revenue_gap_surplus', 0):,.2f} Lakhs")
    print(f"  Output PDF:       {result.get('output_pdf_path', 'N/A')}")
    print("═" * 60)
