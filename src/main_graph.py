"""
KSERC SDL Truing Up — LangGraph Orchestrator
==============================================

Wires all agents into a LangGraph StateGraph with Human-in-the-Loop.

Enhanced Pipeline (Phase 2):
  Extract → [DeepExtract ∥ MYTExtract] → AnomalyDetect → Audit
         → Review (HITL) → Draft → Clarification → Validate → END

New AI Nodes:
  • anomaly_detect : Gemini flags suspicious patterns pre-audit
  • clarification  : Auto-generates KSERC query letters
  • validate       : Peer-reviews the drafted order for quality
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
from src.agents.myt_norm_extractor import myt_extract_node
from src.agents.deep_table_extractor import deep_extract_node
from src.agents.anomaly_detector import detect_anomalies
from src.tools.clarification_generator import clarification_node as _clarification_node
from src.agents.order_validator import validate_drafted_order

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


def myt_extract(state: TruingUpState) -> dict:
    """Node 1.5: Cross-Licensee Learning & Norm Extraction.
    
    Studies ALL past orders (every licensee), regulations, amendments,
    and the petition's Annex B to learn KSERC methodology and extract benchmarks.
    """
    logger.info("═" * 60)
    logger.info("NODE 1.5: CROSS-LICENSEE LEARNING & NORM EXTRACTION")
    logger.info("Studying ALL past orders, regulations, and amendments...")
    logger.info("═" * 60)
    return myt_extract_node(state)


def deep_extract(state: TruingUpState) -> dict:
    """Node 1.6: Deep Table Extraction.
    
    Extracts ALL tables from the petition PDF (not just ARR summary).
    Phase-wise PPC, employee breakdowns, R&M details, GFA schedules,
    escalation factors, loan details, licensee justifications, etc.
    """
    logger.info("═" * 60)
    logger.info("NODE 1.6: DEEP TABLE EXTRACTION")
    logger.info("Extracting ALL tables from petition PDF...")
    logger.info("═" * 60)
    return deep_extract_node(state)


def audit_node(state: TruingUpState) -> dict:
    """Node 2: Apply compliance rules and audit the petition."""
    logger.info("═" * 60)
    logger.info("NODE 2: COMPLIANCE AUDIT")
    logger.info("═" * 60)
    return audit_petition(state)


def anomaly_detect_node(state: TruingUpState) -> dict:
    """
    Node 2a: AI Anomaly Detection (runs after extraction, before audit).

    Gemini reviews all extracted financial data and flags:
    - Year-over-year spikes in any expense
    - Internal inconsistencies between tables
    - Regulatory red flags (items KSERC always disallows)
    - Missing or suspicious data
    Results stored in state["anomaly_flags"] for the auditor to use.
    """
    logger.info("═" * 60)
    logger.info("NODE 2a: AI ANOMALY DETECTION")
    logger.info("═" * 60)
    return detect_anomalies(state)


def clarification_letter_node(state: TruingUpState) -> dict:
    """
    Node 4b: Auto-generate KSERC clarification query letter.

    Merges clarification items from:
    - R&M Classifier (items too vague to classify)
    - Anomaly Detector (HIGH severity flags needing licensee response)
    Generates a formal KSERC query letter and saves it to output_orders/.
    """
    logger.info("═" * 60)
    logger.info("NODE 4b: CLARIFICATION LETTER GENERATION")
    logger.info("═" * 60)
    return _clarification_node(state)


def validate_node(state: TruingUpState) -> dict:
    """
    Node 5: Order Quality Validation.

    Gemini reviews the drafted order as a peer reviewer:
    - Completeness: every claimed item addressed
    - Legal soundness: correct regulation citations
    - Arithmetic consistency
    - KSERC language quality
    - Internal contradictions
    Results in state["order_validation_result"].
    """
    logger.info("═" * 60)
    logger.info("NODE 5: ORDER QUALITY VALIDATION")
    logger.info("═" * 60)
    return validate_drafted_order(state)


# Global flag for auto-approve mode (set by CLI --auto-approve)
_AUTO_APPROVE = False

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

    # ── Auto-approve or interrupt for human approval ───────────────
    if _AUTO_APPROVE:
        logger.info("AUTO-APPROVE: Skipping human review, proceeding to draft.")
        logger.info(summary_text)
        return {"human_override_notes": None}

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
    Construct the full enhanced LangGraph StateGraph:

    START → extract
          → [deep_extract ∥ myt_extract]   (fan-out)
          → anomaly_detect                  (fan-in, NEW)
          → audit
          → review  (HITL interrupt)
          → draft
          → clarification                   (NEW)
          → validate                        (NEW)
          → END
    """
    graph = StateGraph(TruingUpState)

    # ── Register all nodes ────────────────────────────────────────────
    graph.add_node("extract",       extract_node)
    graph.add_node("deep_extract",  deep_extract)
    graph.add_node("myt_extract",   myt_extract)
    graph.add_node("anomaly_detect", anomaly_detect_node)  # NEW
    graph.add_node("audit",         audit_node)
    graph.add_node("review",        review_node)
    graph.add_node("draft",         draft_node)
    graph.add_node("clarification", clarification_letter_node)  # NEW
    graph.add_node("validate",      validate_node)             # NEW

    # ── Define edges ──────────────────────────────────────────────────
    graph.add_edge(START, "extract")

    # Fan-out: parallel extraction
    graph.add_edge("extract", "deep_extract")
    graph.add_edge("extract", "myt_extract")

    # Fan-in with anomaly detection (NEW: anomaly runs after both extractors)
    graph.add_edge("deep_extract", "anomaly_detect")
    graph.add_edge("myt_extract",  "anomaly_detect")

    # Audit reads anomaly flags from state
    graph.add_edge("anomaly_detect", "audit")

    # HITL review and drafting
    graph.add_edge("audit",   "review")
    graph.add_edge("review",  "draft")

    # Post-draft: clarification letter + quality validation
    graph.add_edge("draft",         "clarification")  # NEW
    graph.add_edge("clarification", "validate")        # NEW
    graph.add_edge("validate",      END)               # NEW (was draft → END)

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
        Path to a petition PDF file OR a folder containing petition + annexures.
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

    # Resolve input — handles both single PDF and folder
    from src.petition_resolver import resolve_petition_input
    resolved = resolve_petition_input(petition_pdf_path)
    
    main_pdf = resolved["main_petition"]
    annexures = resolved["annexures"]
    
    logger.info(f"Input type: {resolved['input_type']}")
    logger.info(f"Main petition: {main_pdf}")
    if annexures:
        logger.info(f"Annexures: {len(annexures)} files")
        for a in annexures:
            logger.info(f"  → {Path(a).name}")

    # Build initial state
    initial_state: Dict[str, Any] = {
        "licensee_name": licensee_name,
        "financial_year": financial_year,
        "petition_pdf_path": main_pdf,
        "petition_input_path": petition_pdf_path,
        "annexure_pdf_paths": annexures,
        "petition_text": "",
        "claimed_expenses": {},
        "claimed_revenues": {},
        "asset_register": [],
        "claimed_distribution_loss_pct": 0.0,
        "target_distribution_loss_pct": 0.0,
        "myt_baseline_norms": myt_baseline_norms or {},
        "kserc_methodology_rules": {},
        "ai_insights": {},
        "detailed_tables": {},
        # Phase 2 new fields ──────────────────────────────
        "rm_line_items": [],
        "rm_classification_result": {},
        "anomaly_flags": [],
        "clarification_items": [],
        "order_validation_result": {},
        "energy_sales_lakh_units": 0.0,
        # ───────────────────────────────────────
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
        "clarification_pdf_path": None,
    }

    config = {"configurable": {"thread_id": thread_id}}

    logger.info(f"Starting pipeline for {licensee_name} FY {financial_year}")
    logger.info(f"Input: {petition_pdf_path}")

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
        help="Path to the petition PDF file OR folder containing petition + annexures",
    )
    parser.add_argument(
        "--surplus",
        type=float,
        default=0.0,
        help="Accumulated regulatory surplus (Rs. Lakhs)",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        default=False,
        help="Skip human review and auto-approve the audit",
    )

    args = parser.parse_args()

    # Set auto-approve mode
    if args.auto_approve:
        import sys
        sys.modules[__name__]._AUTO_APPROVE = True

    result = run_pipeline(
        licensee_name=args.licensee,
        financial_year=args.fy,
        petition_pdf_path=args.pdf,
        accumulated_surplus=args.surplus,
    )

    print("\n" + "=" * 60)
    print("PIPELINE RESULT")
    print("=" * 60)
    print(f"  Licensee:         {result.get('licensee_name')}")
    print(f"  Financial Year:   {result.get('financial_year')}")
    print(f"  Total Claimed:    Rs. {result.get('total_claimed_expenditure', 0):,.2f} Lakhs")
    print(f"  Total Approved:   Rs. {result.get('total_approved_expenditure', 0):,.2f} Lakhs")
    print(f"  Gap/Surplus:      Rs. {result.get('final_revenue_gap_surplus', 0):,.2f} Lakhs")
    print(f"  Output PDF:       {result.get('output_pdf_path', 'N/A')}")
    # Phase 2 outputs
    anomaly_count = len(result.get('anomaly_flags', []))
    high_anomalies = sum(1 for f in result.get('anomaly_flags', []) if f.get('severity') == 'HIGH')
    clarif_path   = result.get('clarification_pdf_path', None)
    val_result    = result.get('order_validation_result', {})
    val_passed    = val_result.get('passed', 'N/A')
    val_score     = val_result.get('confidence_score', 0)
    print(f"  Anomalies:        {anomaly_count} total ({high_anomalies} HIGH)")
    print(f"  Clarification:    {clarif_path or 'None (no items)'}")
    print(f"  Order Validation: {'PASSED' if val_passed else 'ISSUES FOUND'} (score={val_score:.2f})")
    print("=" * 60)
