# [Purpose] 4-LLM orchestration pipeline for KSERC Saarthi
# [Source] User defined based on project PDFs and requirements
# [Why] Simulates multi-agent regulatory reasoning with separate roles

# [Library] typing - Type hints
# [Why] Clarity and IDE support
from typing import Dict, Any, List

# [Library] httpx - HTTP client
# [Why] Calls Hugging Face Inference chat API
import httpx

# [User Defined] Import settings
# [Source] src/config.py
# [Why] Access HF endpoint/model/token
from src.config import settings

# [User Defined] Import logger
# [Source] src/utils/logger.py
# [Why] Trace pipeline steps
from src.utils.logger import get_logger

# [User Defined] Get logger instance
logger = get_logger(__name__)


def hf_chat(messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 500) -> str:
    """
    [Purpose] Call Hugging Face OpenAI-compatible chat completions
    [Why] Single API provider for all agents
    """
    if not settings.HF_API_TOKEN or not settings.HF_API_MODEL:
        raise RuntimeError("HF_API_TOKEN or HF_API_MODEL not configured")

    headers = {
        "Authorization": f"Bearer {settings.HF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": settings.HF_API_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    response = httpx.post(
        settings.HF_API_URL,
        headers=headers,
        json=payload,
        timeout=settings.LLM_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "").strip()


def build_context_block(rag_snippets: List[Dict[str, Any]]) -> str:
    """
    [Purpose] Convert RAG snippets to a compact context block
    [Why] Keeps prompts compact and traceable
    """
    lines = []
    for s in rag_snippets:
        loc = f"{s.get('source')} p.{s.get('page')}" if s.get("page") else s.get("source")
        lines.append(f"[{loc}] {s.get('text')}")
    return "\n\n".join(lines)


def run_four_agent_pipeline(
    arr_analysis: Dict[str, Any],
    truing_analysis: Dict[str, Any],
    compliance_report: Dict[str, Any],
    rag_snippets: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    [Purpose] Run 4-agent pipeline and return structured outputs
    [Why] Produces final verdict and intermediate reasoning
    """
    context = build_context_block(rag_snippets)

    base_facts = {
        "arr_analysis": arr_analysis,
        "truing_up_analysis": truing_analysis,
        "compliance_report": compliance_report
    }

    # Agent 1: Legal Brain (regulations)
    logger.info("Agent 1: Legal Brain")
    legal_prompt = [
        {"role": "system", "content": "You are the KSERC Legal Brain agent. Extract regulatory rules, cite relevant clauses, and list compliance risks."},
        {"role": "user", "content": f"RAG Context:\n{context}\n\nFacts:\n{base_facts}\n\nReturn:\n- key rules\n- compliance risks\n- citations with source/page."}
    ]
    legal_output = hf_chat(legal_prompt, temperature=0.1, max_tokens=500)

    # Agent 2: Forensic Auditor (inflation/prudence)
    logger.info("Agent 2: Forensic Auditor")
    forensic_prompt = [
        {"role": "system", "content": "You are the KSERC Forensic Auditor agent. Validate expense prudence and inflation adjustments using given context."},
        {"role": "user", "content": f"RAG Context:\n{context}\n\nFacts:\n{base_facts}\n\nReturn:\n- suspicious expenses\n- inflation/prudence checks\n- citations."}
    ]
    forensic_output = hf_chat(forensic_prompt, temperature=0.2, max_tokens=500)

    # Agent 3: Technical Validator (math & deviations)
    logger.info("Agent 3: Technical Validator")
    technical_prompt = [
        {"role": "system", "content": "You are the KSERC Technical Validator agent. Check math consistency and deviations against ARR."},
        {"role": "user", "content": f"Facts:\n{base_facts}\n\nReturn:\n- math inconsistencies\n- top deviations\n- recommended corrections."}
    ]
    technical_output = hf_chat(technical_prompt, temperature=0.2, max_tokens=400)

    # Agent 4: Chief Regulatory Officer (final verdict)
    logger.info("Agent 4: Chief Regulatory Officer")
    verdict_prompt = [
        {"role": "system", "content": "You are the KSERC Chief Regulatory Officer. Produce final verdict on approvals and disallowances. Be decisive and structured."},
        {"role": "user", "content": f"Inputs:\nLegal:\n{legal_output}\n\nForensic:\n{forensic_output}\n\nTechnical:\n{technical_output}\n\nFacts:\n{base_facts}\n\nReturn JSON-like text with:\n- approved_items\n- disallowed_items\n- conditions\n- final_summary (5-7 sentences)."}
    ]
    verdict_output = hf_chat(verdict_prompt, temperature=0.1, max_tokens=700)

    return {
        "legal_brain": legal_output,
        "forensic_auditor": forensic_output,
        "technical_validator": technical_output,
        "chief_regulatory_officer": verdict_output
    }
