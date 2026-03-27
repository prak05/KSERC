import logging
from typing import Dict, Any, TypedDict
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from langgraph.graph import StateGraph, START, END

from src.agents.chief_auditor import auditor
from src.gemini_client import generate
from src.config import GEMINI_MODEL

logger = logging.getLogger("truing_up_graph")

COMPONENT_TIMEOUT = 180   # 3 min per component (includes retry waits)
MAX_WORKERS       = 2    # only 2 parallel Gemini calls to avoid 429 rate limits


def extract_narrative(petition_text: str, component: str) -> str:
    """Extract the licensee's justification for a specific cost component."""
    if not petition_text:
        return "No narrative text provided in petition."

    trimmed = petition_text[:8000]

    prompt = f"""You are a legal summarizer reading a KSERC Truing-Up Petition.
Extract ONLY the paragraphs where the licensee justifies their '{component}' expense.
Include any specific contracts, vendors, rates, or reasons mentioned.
If no justification is found, reply: 'No specific justification provided.'

PETITION (excerpt):
{trimmed}
"""
    # Let any exception propagate — don't suppress failures
    result = generate(
        prompt,
        model=GEMINI_MODEL,
        temperature=0.0,
        response_mime_type="text/plain",
    )
    return result.strip()


def process_one_component(
    component: str,
    claimed_val: float,
    petition_text: str,
    myt_expenses: dict,
    deterministic_math: dict,
    analysis_id: str = "",
    max_retries: int = 3,
) -> tuple[str, dict]:
    """
    Process a single expense component.
    Retries up to max_retries times on 429 RESOURCE_EXHAUSTED errors.
    """
    import time as _time

    def _log(msg: str):
        if analysis_id:
            try:
                from src.tools.db import update_progress
                update_progress(analysis_id, "ai_audit", msg)
            except Exception:
                pass
        logger.info(f"[Graph|{component}] {msg}")

    def _is_rate_limit_error(exc: Exception) -> bool:
        """Check if the exception is a 429 RESOURCE_EXHAUSTED error."""
        err_str = str(exc)
        return "429" in err_str or "RESOURCE_EXHAUSTED" in err_str

    for attempt in range(1, max_retries + 1):
        try:
            myt_norm      = myt_expenses.get(component, claimed_val)
            math_approved = deterministic_math.get(component, myt_norm)
            math_result   = {
                "amount": math_approved,
                "status": "Deterministic Calculation",
                "rule_applied": f"Math Engine Limit: {math_approved}",
            }

            if component in ["Employee Cost", "Repairs & Maintenance", "Administration & General"]:
                base_query = f"Regulations regarding {component} operation and maintenance expenses truing up"
            else:
                base_query = f"Regulations regarding {component} capital expenditure true up"

            # Step 1: Narrative extraction
            _log(f"Extracting narrative for '{component}'…")
            licensee_narrative = extract_narrative(petition_text, component)

            # Step 2: RAG legal context
            _log(f"Querying legal precedents for '{component}'…")
            from src.rag.file_search_store import query_regulations
            legal_context = query_regulations(f"{base_query}. Precedent for: {licensee_narrative[:300]}")

            # Step 3: Chief Auditor decision
            _log(f"Chief Auditor analysing '{component}'…")
            decision = auditor.analyze_component(
                component_name=component,
                claimed_lakhs=claimed_val,
                myt_norm_lakhs=myt_norm,
                math_result=math_result,
                legal_context=legal_context,
                licensee_narrative=licensee_narrative,
            )

            result = {
                "claimed":       claimed_val,
                "approved":      decision["amount"],
                "variance":      decision["variance"],
                "justification": decision["justification"],
                "myt_norm":      myt_norm,
            }
            _log(f"✓ '{component}' done — approved=₹{decision['amount']:.2f}L")
            return component, result

        except Exception as e:
            if _is_rate_limit_error(e) and attempt < max_retries:
                wait = 10 * (2 ** (attempt - 1))  # 10s, 20s, 40s
                _log(f"⚠️ '{component}' hit rate limit (attempt {attempt}/{max_retries}). Retrying in {wait}s…")
                _time.sleep(wait)
            else:
                raise  # Non-retryable error or final attempt — let it propagate


class AgentState(TypedDict):
    petition_data:     Dict[str, Any]
    myt_baselines:     Dict[str, Any]
    results:           Dict[str, Any]
    current_component: str
    analysis_id:       str   # passed through for per-component progress logging


def routing_node(state: AgentState) -> AgentState:
    return state


def component_processing_node(state: AgentState) -> AgentState:
    """
    Process all components IN PARALLEL.
    If ANY component fails or times out, raises immediately with the full error details.
    """
    claimed_expenses   = state["petition_data"].get("expenses", {})
    petition_text      = state["petition_data"].get("petition_text", "")
    myt_expenses       = state["myt_baselines"].get("expenses", {})
    deterministic_math = state.get("deterministic_math", {})
    analysis_id        = state.get("analysis_id", "")

    if not claimed_expenses:
        logger.warning("[Graph] No expenses found in petition_data")
        state["results"] = {"expenses": {}}
        return state

    logger.info(f"[Graph] Starting parallel processing of {len(claimed_expenses)} components "
                f"(workers={MAX_WORKERS}, timeout={COMPONENT_TIMEOUT}s each)")

    final_expenses = {}
    failed = []  # collect all failures before raising

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_comp = {
            executor.submit(
                process_one_component,
                comp, val, petition_text, myt_expenses, deterministic_math, analysis_id,
            ): comp
            for comp, val in claimed_expenses.items()
        }

        for future in as_completed(future_to_comp):
            comp = future_to_comp[future]
            try:
                name, result = future.result(timeout=COMPONENT_TIMEOUT)
                final_expenses[name] = result
                logger.info(f"[Graph] ✓ {name}")
            except FuturesTimeout:
                err = f"TIMEOUT after {COMPONENT_TIMEOUT}s"
                logger.error(f"[Graph] ✗ {comp}: {err}")
                failed.append(f"{comp}: {err}")
            except Exception as e:
                logger.error(f"[Graph] ✗ {comp}: {e}", exc_info=True)
                failed.append(f"{comp}: {e}")

    if failed:
        summary = "; ".join(failed)
        logger.error(f"[Graph] Pipeline FAILED — {len(failed)} component(s) errored: {summary}")
        raise RuntimeError(
            f"Agentic audit failed for {len(failed)} component(s):\n" +
            "\n".join(f"  • {f}" for f in failed)
        )

    logger.info(f"[Graph] All {len(final_expenses)} components resolved successfully")
    state["results"] = {"expenses": final_expenses}
    return state


# ── LangGraph Graph ──────────────────────────────────────────────────
workflow = StateGraph(AgentState)
workflow.add_node("router",    routing_node)
workflow.add_node("processor", component_processing_node)
workflow.add_edge(START,       "router")
workflow.add_edge("router",    "processor")
workflow.add_edge("processor", END)
truing_up_app = workflow.compile()


def run_agentic_audit(
    extracted_data:       Dict[str, Any],
    historical_baselines: Dict[str, Any],
    deterministic_math:   Dict[str, Any] = None,
    analysis_id:          str = "",
) -> Dict[str, Any]:
    """Run the full LangGraph agentic audit pipeline. Raises on any component failure."""
    initial_state = {
        "petition_data":      extracted_data,
        "myt_baselines":      historical_baselines,
        "deterministic_math": deterministic_math or {},
        "results":            {},
        "current_component":  "",
        "analysis_id":        analysis_id,
    }
    logger.info(f"[Agentic] Starting parallel audit for "
                f"{len(extracted_data.get('expenses', {}))} components…")
    final_state = truing_up_app.invoke(initial_state)
    logger.info("[Agentic] Complete.")
    return final_state["results"]
