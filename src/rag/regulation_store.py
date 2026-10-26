"""
Regulation corpus: extraction, storage and retrieval.

Reference PDFs (tariff regulations, MYT orders, past truing-up orders) are converted to
text once and stored in the ``regulation_extractions`` collection. Questions are answered
from the most relevant passages, ranked with BM25, so a query never ships whole PDFs.
"""

import logging
import math
import re
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from src.cloud import settings
from src.cloud.docstore import client as _db

logger = logging.getLogger("kserc.regulations")

DOCUMENTS_DIR = settings.DOCUMENTS_DIR
COLLECTION = "regulation_extractions"

REFERENCE_DOCS = {
    "regulations": [
        "KSERC_Tariff_Regulations_2021.pdf",
        "First Amendment, 2023.pdf",
        "secondAmendment, 2024.pdf",
        "Third Amendment, 2025.pdf",
        "Kerala Electricity Duty Act, 1963.pdf",
        "Kerala Electricity Duty Rules, 1963.pdf",
        "Interim Tariff Extension Order.pdf",
        "eZT03AJgJSIIRSrBEQ8mHaMu5PA0zuQ3bl7xklKD (1).pdf",  # 2018 Tariff Regulations
    ],
    "myt_orders": [
        "Infopark MYT Order (OP 09 2023).pdf",
        "Technopark MYT Order OP 12 2023.pdf",
        "CSEZA MYT Order 19 1 24.pdf",
        "Kannan Devan Hills Plantations MYT Order 26-11-25.pdf",
        "Master Tariff Order (OP 18 2023).pdf",
    ],
    "past_orders": [
        "Infopark True-Up 2022-23 (OP 82 2023).pdf",
        "Technopark True-Up 2022-23 (OP 84 2023).pdf",
        "Cochin Special Economic Zone Authority FY 2018-19 Truing Up Order.pdf",
        "Cochin Special Economic Zone Authority FY 2019-20 Truing Up Order.pdf",
        "Cochin Special Economic Zone Authority FY 2020-21 Truing Up Order.pdf",
        "Kannan Devan Hills Plantations Company FY 2013-14 Truing Up Order.pdf",
        "Kannan Devan Hills Plantations Company FY 2021-22 Truing Up Order.pdf",
        "Kannan Devan Hills Plantations Company FY 2022-23 Truing Up Order.pdf",
        "KANNADEVAN 2023-24.pdf",
        "2023-24.pdf",
    ],
    "other_licensee_orders": [
        "RUBBERPARK2022-23.pdf",
        "COCHIN PORT 2023-24.pdf",
        "Thrissur Corporation 2023-24.pdf",
        "KINESCO 2023-24.pdf",
        "Smart City2023-24.pdf",
        "TU 23-24_CHAPTERS 1 TO 6 COMBINED_KSEBL.pdf",
    ],
    "other": ["Index.pdf"],
}

_CHUNK_CHARS = 1800
_TOP_K = 40
_SYSTEM = (
    "You are a KSERC (Kerala State Electricity Regulatory Commission) legal expert. "
    "Answer precisely from the reference passages provided, citing clause numbers and order references."
)


# ═══════════════════════════════════════════════════════════════════════
# Extraction & storage
# ═══════════════════════════════════════════════════════════════════════

def _doc_id(filename: str) -> str:
    return re.sub(r"[ .,()]", "_", filename).replace("__", "_")


def extract_and_store_regulation(pdf_path: str, filename: str, category: str) -> dict:
    """Extract a regulation PDF to text (model-assisted OCR for scanned files) and store it."""
    import fitz

    with fitz.open(pdf_path) as doc:
        page_count = doc.page_count
        text = "\n".join(f"\n--- Page {p.number + 1} ---\n{p.get_text('text')}" for p in doc if p.get_text("text").strip())

    method = "pymupdf"
    if len(text) / max(page_count, 1) < 100:  # scanned PDF: let the model read it
        try:
            from src.llm_client import generate_with_pdf

            ocr = generate_with_pdf(
                pdf_path,
                "Extract ALL text content from this PDF. Preserve headings, clause numbers and tables. "
                "Return the text only, no commentary.",
                response_mime_type="text/plain",
            ).strip()
            if len(ocr) > len(text):
                text, method = ocr, "model-ocr"
        except Exception as e:
            logger.warning(f"[RegExtract] OCR fallback failed for {filename}: {e}")

    if not text.strip():
        raise ValueError(f"Failed to extract any text from {filename}")

    doc_id = _doc_id(filename)
    _db().collection(COLLECTION).document(doc_id).set({
        "filename": filename,
        "category": category,
        "content": text,
        "chars": len(text),
        "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "method": method,
        "page_count": page_count,
    })
    _index_cache.clear()
    logger.info(f"[RegExtract] Stored '{filename}' ({len(text):,} chars, {method})")
    return {"doc_id": doc_id, "filename": filename, "category": category,
            "chars": len(text), "method": method, "page_count": page_count}


def list_stored_regulations() -> list:
    out = []
    for snap in _db().collection(COLLECTION).stream():
        d = snap.to_dict()
        out.append({"doc_id": snap.id, "filename": d.get("filename", ""), "category": d.get("category", ""),
                    "chars": d.get("chars", 0), "method": d.get("method", "unknown"),
                    "extracted_at": d.get("extracted_at", "")})
    return sorted(out, key=lambda x: x["category"])


def delete_stored_regulation(doc_id: str) -> bool:
    try:
        _db().collection(COLLECTION).document(doc_id).delete()
        _index_cache.clear()
        return True
    except Exception as e:
        logger.error(f"Failed to delete regulation {doc_id}: {e}")
        return False


def ensure_files_uploaded(categories: Optional[List[str]] = None) -> Dict[str, str]:
    """Extract any reference PDF present in DOCUMENTS_DIR that is not yet in the store."""
    stored = {r["filename"] for r in list_stored_regulations()}
    available = {}
    for cat in categories or REFERENCE_DOCS:
        for name in REFERENCE_DOCS.get(cat, []):
            path = DOCUMENTS_DIR / name
            if name in stored:
                available[name] = _doc_id(name)
            elif path.exists():
                try:
                    available[name] = extract_and_store_regulation(str(path), name, cat)["doc_id"]
                except Exception as e:
                    logger.warning(f"Could not extract {name}: {e}")
    return available


upload_reference_documents = ensure_files_uploaded


def get_uploaded_files(category: Optional[str] = None) -> Dict[str, str]:
    return {r["filename"]: r["doc_id"] for r in list_stored_regulations()
            if category is None or r["category"] == category}


# ═══════════════════════════════════════════════════════════════════════
# Retrieval (BM25)
# ═══════════════════════════════════════════════════════════════════════

_TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)*")
_index_cache: Dict[tuple, dict] = {}


def _tokens(text: str) -> List[str]:
    return _TOKEN.findall(text.lower())


def _build_index(categories: tuple) -> dict:
    if categories in _index_cache:
        return _index_cache[categories]
    chunks = []
    for snap in _db().collection(COLLECTION).stream():
        d = snap.to_dict()
        if d.get("category") not in categories:
            continue
        content = d.get("content", "")
        for i in range(0, len(content), _CHUNK_CHARS):
            body = content[i:i + _CHUNK_CHARS]
            chunks.append({"file": d.get("filename", ""), "text": body, "tf": Counter(_tokens(body))})
    df = Counter(t for c in chunks for t in c["tf"])
    avg = sum(sum(c["tf"].values()) for c in chunks) / max(len(chunks), 1)
    index = {"chunks": chunks, "df": df, "n": len(chunks), "avg": avg or 1}
    _index_cache[categories] = index
    return index


def _search(question: str, categories: tuple, k: int = _TOP_K) -> List[dict]:
    idx = _build_index(categories)
    if not idx["n"]:
        return []
    q = set(_tokens(question))
    k1, b = 1.5, 0.75
    scored = []
    for c in idx["chunks"]:
        length = sum(c["tf"].values())
        s = 0.0
        for t in q:
            f = c["tf"].get(t)
            if f:
                idf = math.log(1 + (idx["n"] - idx["df"][t] + 0.5) / (idx["df"][t] + 0.5))
                s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * length / idx["avg"]))
        if s > 0:
            scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:k]]


def retrieve_context(question: str, categories: Optional[List[str]] = None, k: int = _TOP_K) -> str:
    cats = tuple(categories or ["regulations", "myt_orders", "past_orders"])
    hits = _search(question, cats, k)
    return "\n\n".join(f"[{h['file']}]\n{h['text']}" for h in hits)


def query_regulations(question: str, categories: Optional[List[str]] = None, model: Optional[str] = None,
                      use_cache: bool = True) -> str:
    """Answer a regulatory question from the most relevant passages of the stored corpus."""
    from src.llm_client import generate

    cats = categories or ["regulations", "myt_orders"]
    if not list_stored_regulations():
        ensure_files_uploaded(cats)
    context = retrieve_context(question, cats)
    if not context:
        return "No reference documents available. Upload regulations under Reference Data first."

    prompt = (f"Reference passages:\n\n{context}\n\n"
              "Answer the question thoroughly. Cite specific regulation clause numbers, "
              "past order numbers and dates, and exact amounts where relevant.\n\n"
              f"QUESTION: {question}")
    try:
        return generate(prompt, response_mime_type="text/plain", system_instruction=_SYSTEM).strip()
    except Exception as e:
        logger.error(f"Failed to query regulations: {e}")
        return f"Error querying regulations: {e}"


def answer_question(question: str) -> dict:
    """Analyst Q&A: answer from the corpus and list the documents the passages came from."""
    cats = ["regulations", "myt_orders", "past_orders", "other_licensee_orders"]
    if not list_stored_regulations():
        ensure_files_uploaded(cats)
    hits = _search(question, tuple(cats), _TOP_K)
    sources = list(dict.fromkeys(h["file"] for h in hits))
    return {"answer": query_regulations(question, categories=cats), "sources": sources}


def create_regulation_cache(*_, **__) -> Optional[str]:
    """Kept for compatibility: retrieval replaces server-side context caches."""
    return None


def query_with_grounding(question: str, context: str = "") -> str:
    return query_regulations(f"{context}\n\n{question}" if context else question,
                             categories=["regulations", "myt_orders", "past_orders"])


def query_precedent_for_component(component_name: str, licensee_name: str,
                                  claimed_amount: float, financial_year: str) -> str:
    question = (
        f'For the component "{component_name}" in a Truing-Up Petition by {licensee_name} for FY '
        f"{financial_year}, the licensee has claimed ₹{claimed_amount:.2f} Lakhs.\n"
        "1. What do the KSERC Tariff Regulations say about this component?\n"
        f"2. What amount was approved for it in the most recent truing-up orders for {licensee_name} "
        "or similar SDL licensees?\n3. What calculation methodology did KSERC apply?\n"
        "4. Were any special circumstances or exceptions granted?\n"
        "Provide clause numbers, order numbers and amounts."
    )
    return query_regulations(question, categories=["regulations", "myt_orders", "past_orders"])
