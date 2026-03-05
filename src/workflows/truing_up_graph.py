import logging
from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, START, END

# Import the specialized agents
from src.agents.calculator import evaluate_om_expense, evaluate_financial_expense
from src.agents.chief_auditor import auditor
from src.gemini_client import generate

logger = logging.getLogger("truing_up_graph")

def extract_narrative(petition_text: str, component: str) -> str:
    """Scans the entire petition and finds the Licensee's narrative justification for a specific line item."""
    if not petition_text:
        return "No narrative text provided in petition."
    
    prompt = f"""You are a legal summarizer. 
Scan this True Up Petition and extract the EXACT paragraphs where the Licensee justifies their '{component}' expense.
If there are specific contracts, vendors, or reasons mentioned (e.g. 'paid to KINFRA'), extract them!
If no specific justification is found, just say 'No specific justification provided.'

PETITION TEXT:
{petition_text}
"""
    try:
        result = generate(
            prompt,
            model="gemini-2.5-flash",
            temperature=0.0,
            response_mime_type="text/plain",
        )
        return result.strip()
    except Exception as e:
        logger.error(f"Flash failed to extract narrative for {component}: {e}")
        return "Failed to extract narrative."

class AgentState(TypedDict):
    petition_data: Dict[str, Any]  # The raw extracted JSON from the Vision Agent
    myt_baselines: Dict[str, Any]  # The historical baselines
    results: Dict[str, Any]        # The final analyzed output
    current_component: str         # The component currently being processed in the loop

def routing_node(state: AgentState) -> AgentState:
    """Initializes processing or ends if all components are done."""
    return state

def component_processing_node(state: AgentState) -> AgentState:
    """Iterates through extracted components and applies RAG + Math + Auditor logic."""
    claimed_expenses = state["petition_data"].get("expenses", {})
    petition_text = state["petition_data"].get("petition_text", "")
    myt_expenses = state["myt_baselines"].get("expenses", {})
    deterministic_math = state.get("deterministic_math", {})
    
    final_expenses = {}
    
    for component, claimed_val in claimed_expenses.items():
        logger.info(f"[Graph] Processing component: {component}")
        
        # 1. Deterministic Bounds (provided by legacy math engine)
        myt_norm = myt_expenses.get(component, claimed_val) # Fallback to claimed if no norm
        math_approved = deterministic_math.get(component, myt_norm)
        
        math_result = {
            "amount": math_approved,
            "status": "Deterministic Calculation",
            "rule_applied": f"Math Engine Calculated Limit: {math_approved}"
        }
        
        if component in ["Employee Cost", "Repairs & Maintenance", "Administration & General"]:
            base_query = f"Regulations regarding {component} operation and maintenance expenses truing up"
        else:
            base_query = f"Regulations regarding {component} capital expenditure true up"
            
        # 2. Context Extraction (Flash): Get the Licensee's Specific Reason
        licensee_narrative = extract_narrative(petition_text, component)
        logger.info(f"[Graph] Licensee Narrative for {component} extracted.")
            
        # 3. Legal Context: Will be replaced by File Search in Phase 2
        # For now, use a placeholder
        legal_context = "Regulation-based legal context. (File Search integration pending - Phase 2)"
        # TODO Phase 2: Replace with File Search query
        # legal_context = file_search_query(targeted_query)
                
        # 4. Chief Auditor Agent: Synthesize Truth
        decision = auditor.analyze_component(
            component_name=component,
            claimed_lakhs=claimed_val,
            myt_norm_lakhs=myt_norm,
            math_result=math_result,
            legal_context=legal_context,
            licensee_narrative=licensee_narrative
        )
        
        final_expenses[component] = {
            "claimed": claimed_val,
            "approved": decision["amount"],
            "variance": decision["variance"],
            "justification": decision["justification"],
            "myt_norm": myt_norm
        }
        
    state["results"] = {"expenses": final_expenses}
    return state

# ---- Define the Graph ----
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("router", routing_node)
workflow.add_node("processor", component_processing_node)

# Add Edges
workflow.add_edge(START, "router")
workflow.add_edge("router", "processor")
workflow.add_edge("processor", END)

# Compile the Graph
truing_up_app = workflow.compile()

def run_agentic_audit(extracted_data: Dict[str, Any], historical_baselines: Dict[str, Any], deterministic_math: Dict[str, Any] = None) -> Dict[str, Any]:
    """Entrypoint function to run the full LangGraph Agentic Pipeline."""
    initial_state = {
        "petition_data": extracted_data,
        "myt_baselines": historical_baselines,
        "deterministic_math": deterministic_math or {},
        "results": {},
        "current_component": ""
    }
    
    logger.info("Starting Agentic RAG Pipeline...")
    final_state = truing_up_app.invoke(initial_state)
    logger.info("Agentic RAG Pipeline complete.")
    
    return final_state["results"]
