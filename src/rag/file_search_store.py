"""
Gemini File Search Store — replaces the old custom RAG pipeline.

Uses the google-genai Files API to:
1. Upload regulatory/reference PDFs to Gemini's file service
2. Query those files with natural language questions
3. Auto-manage file lifecycle (48h expiry, re-upload on demand)

This replaces: ingestion.py + retriever.py + ChromaDB + BM25 + pickle files
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from src.config import GEMINI_MODEL

logger = logging.getLogger("kserc.file_search")
load_dotenv()

# ═══════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parents[2]
DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", str(BASE_DIR / ".." / "Documents"))).resolve()

# Cache file to track uploaded files (avoids re-uploading)
UPLOAD_CACHE_FILE = BASE_DIR / ".file_upload_cache.json"

# Categories for organizing documents
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
        # Our SDL licensees — truing-up orders
        "Infopark True-Up 2022-23 (OP 82 2023).pdf",
        "Technopark True-Up 2022-23 (OP 84 2023).pdf",
        "Cochin Special Economic Zone Authority FY 2018-19 Truing Up Order.pdf",
        "Cochin Special Economic Zone Authority FY 2019-20 Truing Up Order.pdf",
        "Cochin Special Economic Zone Authority FY 2020-21 Truing Up Order.pdf",
        "Kannan Devan Hills Plantations Company FY 2013-14 Truing Up Order.pdf",
        "Kannan Devan Hills Plantations Company FY 2021-22 Truing Up Order.pdf",
        "Kannan Devan Hills Plantations Company FY 2022-23 Truing Up Order.pdf",
        "KANNADEVAN 2023-24.pdf",   # Own licensee recent order
        "2023-24.pdf",
    ],
    "other_licensee_orders": [
        # Other licensees' truing-up orders — for cross-reference training
        "RUBBERPARK2022-23.pdf",
        "COCHIN PORT 2023-24.pdf",
        "Thrissur Corporation 2023-24.pdf",
        "KINESCO 2023-24.pdf",
        "Smart City2023-24.pdf",
        "TU 23-24_CHAPTERS 1 TO 6 COMBINED_KSEBL.pdf",
    ],
    "other": [
        "Index.pdf",
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# Upload Cache Management
# ═══════════════════════════════════════════════════════════════════════

def _load_upload_cache() -> Dict:
    """Load the upload cache from disk."""
    if UPLOAD_CACHE_FILE.exists():
        try:
            return json.loads(UPLOAD_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"files": {}}


def _save_upload_cache(cache: Dict):
    """Save the upload cache to disk."""
    UPLOAD_CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════
# File Upload & Management
# ═══════════════════════════════════════════════════════════════════════

def upload_reference_documents(
    categories: Optional[List[str]] = None,
    force_reupload: bool = False,
) -> Dict[str, str]:
    """
    Upload reference documents to Gemini's file service.
    
    Args:
        categories: Which categories to upload (None = all).
                    Options: 'regulations', 'myt_orders', 'past_orders', 'other'
        force_reupload: If True, re-upload even if cached.
    
    Returns:
        Dict mapping filename -> file URI
    """
    from src.gemini_client import get_client
    client = get_client()
    
    cache = _load_upload_cache()
    uploaded = cache.get("files", {})
    
    # Determine which files to upload
    files_to_upload = []
    target_categories = categories or list(REFERENCE_DOCS.keys())
    
    for cat in target_categories:
        for filename in REFERENCE_DOCS.get(cat, []):
            filepath = DOCUMENTS_DIR / filename
            if filepath.exists():
                files_to_upload.append((cat, filename, filepath))
            else:
                logger.warning(f"Document not found: {filepath}")
    
    # Also scan for any PDFs in subdirectories (petitions are in subfolders)
    for subdir in DOCUMENTS_DIR.iterdir():
        if subdir.is_dir() and "Petition" in subdir.name:
            for pdf in subdir.glob("*.pdf"):
                files_to_upload.append(("petitions", pdf.name, pdf))
    
    logger.info(f"Found {len(files_to_upload)} documents to process")
    
    # Check which files are already uploaded and still active
    if not force_reupload:
        existing_files = {}
        try:
            for f in client.files.list():
                existing_files[f.display_name] = f
        except Exception as e:
            logger.warning(f"Could not list existing files: {e}")
        
        # Remove files that are already uploaded and active
        filtered = []
        for cat, name, path in files_to_upload:
            if name in existing_files and existing_files[name].state.name == "ACTIVE":
                uploaded[name] = {
                    "uri": existing_files[name].uri,
                    "name": existing_files[name].name,
                    "category": cat,
                    "uploaded_at": cache.get("files", {}).get(name, {}).get("uploaded_at", ""),
                }
                logger.info(f"  ✓ Already uploaded: {name}")
            else:
                filtered.append((cat, name, path))
        files_to_upload = filtered
    
    # Upload new files
    for cat, name, path in files_to_upload:
        try:
            logger.info(f"  ⬆ Uploading: {name} ({path.stat().st_size / 1024:.0f} KB)...")
            
            file_obj = client.files.upload(
                file=str(path),
                config={"display_name": name},
            )
            
            # Wait for processing to complete
            while file_obj.state.name == "PROCESSING":
                time.sleep(2)
                file_obj = client.files.get(name=file_obj.name)
            
            if file_obj.state.name == "ACTIVE":
                uploaded[name] = {
                    "uri": file_obj.uri,
                    "name": file_obj.name,
                    "category": cat,
                    "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
                logger.info(f"  ✓ Uploaded: {name} -> {file_obj.uri}")
            else:
                logger.error(f"  ✗ Upload failed for {name}: state={file_obj.state.name}")
                
        except Exception as e:
            logger.error(f"  ✗ Failed to upload {name}: {e}")
    
    # Save cache
    cache["files"] = uploaded
    cache["last_upload"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _save_upload_cache(cache)
    
    logger.info(f"Total files available: {len(uploaded)}")
    return {name: info["uri"] for name, info in uploaded.items()}


def get_uploaded_files(category: Optional[str] = None) -> Dict[str, str]:
    """
    Get URIs of already-uploaded files, optionally filtered by category.
    
    Returns:
        Dict mapping filename -> file URI
    """
    cache = _load_upload_cache()
    files = cache.get("files", {})
    
    if category:
        files = {k: v for k, v in files.items() if v.get("category") == category}
    
    return {name: info["uri"] for name, info in files.items()}


def ensure_files_uploaded(categories: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Ensure reference documents are uploaded — uploads only if needed.
    This is the main entry point for other modules.
    
    Returns:
        Dict mapping filename -> file URI
    """
    cache = _load_upload_cache()
    existing = cache.get("files", {})
    
    # Quick check: if we have files cached, verify they're still active
    if existing and not categories:
        try:
            from src.gemini_client import get_client
            client = get_client()
            # Check a random file to see if it's still active
            first_file = next(iter(existing.values()))
            test = client.files.get(name=first_file["name"])
            if test.state.name == "ACTIVE":
                logger.info(f"Files cache valid ({len(existing)} files)")
                return {name: info["uri"] for name, info in existing.items()}
        except Exception:
            logger.info("Files cache expired, re-uploading...")
    
    return upload_reference_documents(categories=categories)


# ═══════════════════════════════════════════════════════════════════════
# Context Caching — reduces cost for repeated regulation queries
# ═══════════════════════════════════════════════════════════════════════

# In-memory cache name (persists for session)
_regulation_cache_name: Optional[str] = None


def create_regulation_cache(
    categories: Optional[List[str]] = None,
    ttl: str = "3600s",
    model: str = GEMINI_MODEL,
) -> Optional[str]:
    """
    Create a Gemini context cache for regulation documents.
    
    This uploads regulation PDFs once and caches them server-side.
    Subsequent queries use cached_content instead of re-sending files,
    saving ~75% on input token costs.
    
    Args:
        categories: Which document categories to cache.
                    Default: ['regulations', 'myt_orders']
        ttl: Time-to-live for the cache (default 1 hour).
        model: Which Gemini model to use (must support caching).
    
    Returns:
        Cache name string, or None if caching failed.
    """
    global _regulation_cache_name
    
    # Return existing cache if still valid
    if _regulation_cache_name:
        try:
            from src.gemini_client import get_client
            client = get_client()
            existing = client.caches.get(name=_regulation_cache_name)
            if existing:
                logger.info(f"Using existing regulation cache: {_regulation_cache_name}")
                return _regulation_cache_name
        except Exception:
            _regulation_cache_name = None
    
    from src.gemini_client import get_client
    from google.genai import types
    
    client = get_client()
    
    # Ensure files are uploaded
    target_categories = categories or ["regulations", "myt_orders"]
    file_uris = ensure_files_uploaded(categories=target_categories)
    
    if not file_uris:
        logger.warning("No files available for caching")
        return None
    
    # Build content parts from uploaded files
    cache_data = _load_upload_cache()
    contents = []
    for filename, uri in file_uris.items():
        file_info = cache_data.get("files", {}).get(filename, {})
        if file_info.get("category") in target_categories:
            contents.append(
                types.Part.from_uri(file_uri=uri, mime_type="application/pdf")
            )
    
    if not contents:
        logger.warning("No matching files found for caching")
        return None
    
    try:
        cache = client.caches.create(
            model=model,
            config=types.CreateCachedContentConfig(
                display_name="kserc_regulations",
                system_instruction=(
                    "You are a KSERC (Kerala State Electricity Regulatory Commission) legal expert. "
                    "You have complete access to the KSERC Tariff Regulations 2021 (with all amendments), "
                    "MYT Orders, and past Truing-Up Orders. Answer questions precisely, "
                    "citing specific clause numbers and order references."
                ),
                contents=contents,
                ttl=ttl,
            ),
        )
        _regulation_cache_name = cache.name
        logger.info(f"Created regulation cache: {cache.name} (TTL: {ttl}, {len(contents)} files)")
        return cache.name
        
    except Exception as e:
        logger.error(f"Failed to create regulation cache: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════
# Query Interface — replaces legal_researcher.query_regulations()
# ═══════════════════════════════════════════════════════════════════════

def query_regulations(
    question: str,
    categories: Optional[List[str]] = None,
    model: str = GEMINI_MODEL,
    use_cache: bool = True,
) -> str:
    """
    Query uploaded reference documents with a natural language question.
    
    This replaces the old legal_researcher.query_regulations() function.
    If a context cache exists, uses it for 75% token savings.
    Otherwise, sends file references inline.
    
    Args:
        question: The regulation/legal question to answer.
        categories: Which document categories to search.
                    Default: ['regulations', 'myt_orders', 'past_orders', 'other_licensee_orders']
        model: Which Gemini model to use.
        use_cache: Whether to try using context caching (default True).
    
    Returns:
        The answer text with citations.
    """
    from src.gemini_client import get_client
    from google.genai import types
    
    client = get_client()
    
    # Try cached path first (cheaper)
    if use_cache:
        cache_name = create_regulation_cache(
            categories=["regulations", "myt_orders"],
            model=model,
        )
        if cache_name:
            try:
                config = types.GenerateContentConfig(
                    cached_content=cache_name,
                    temperature=0.1,
                )
                response = client.models.generate_content(
                    model=model,
                    contents=f"""Based on the KSERC regulations and orders you have access to, 
answer the following question thoroughly.

IMPORTANT:
- Cite specific regulation clause numbers (e.g., "Clause 27 of KSERC Tariff Regulations 2021")
- Reference specific past order numbers and dates when citing precedent
- Include exact amounts from past orders when relevant
- Be precise and complete

QUESTION: {question}""",
                    config=config,
                )
                result = response.text.strip()
                logger.info(f"File Search query answered via cache ({len(result)} chars)")
                return result
            except Exception as e:
                logger.warning(f"Cached query failed, falling back to inline: {e}")
    
    # Fallback: inline file references
    target_categories = categories or ["regulations", "myt_orders", "past_orders", "other_licensee_orders"]
    file_uris = ensure_files_uploaded(categories=target_categories)
    
    if not file_uris:
        logger.warning("No reference documents available for query")
        return "No reference documents available. Please upload documents first."
    
    # Build content parts: file references + question
    parts = []
    
    # Add file references
    cache_data = _load_upload_cache()
    for filename, uri in file_uris.items():
        file_info = cache_data.get("files", {}).get(filename, {})
        file_cat = file_info.get("category", "")
        
        if file_cat in target_categories:
            parts.append(types.Part.from_uri(file_uri=uri, mime_type="application/pdf"))
    
    if not parts:
        return "No matching documents found for the specified categories."
    
    # Add the question
    parts.append(types.Part.from_text(text=f"""You are a KSERC (Kerala State Electricity Regulatory Commission) legal expert.

Based on the uploaded regulatory documents, past orders, and MYT norms, answer the following question thoroughly.

IMPORTANT:
- Cite specific regulation clause numbers (e.g., "Clause 27 of KSERC Tariff Regulations 2021")
- Reference specific past order numbers and dates when citing precedent
- Include exact amounts from past orders when relevant
- Be precise and complete

QUESTION: {question}"""))
    
    # Generate response
    config = types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="text/plain",
    )
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=parts,
            config=config,
        )
        
        result = response.text.strip()
        logger.info(f"File Search query answered ({len(result)} chars)")
        return result
        
    except Exception as e:
        logger.error(f"File Search query failed: {e}")
        return f"Query failed: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════
# Google Search Grounding — for real-time legal research
# ═══════════════════════════════════════════════════════════════════════

def query_with_grounding(
    question: str,
    context: str = "",
) -> str:
    """
    Query with Google Search grounding for real-time information.
    
    Uses Google Search to find up-to-date information about:
    - KSERC regulations and amendments
    - Kerala electricity tariff rates
    - CPI/WPI indices for O&M escalation
    - Bank rates for consumer deposit interest
    
    Args:
        question: The question to answer.
        context: Additional context to provide.
    
    Returns:
        The grounded answer with web citations.
    """
    try:
        from src.gemini_client import generate_grounded
        
        full_prompt = f"""You are a KSERC (Kerala State Electricity Regulatory Commission) analyst.

{f'Context: {context}' if context else ''}

Answer the following question using real-time search information.
Cite all sources with URLs when available.

QUESTION: {question}"""
        
        result = generate_grounded(
            full_prompt,
            system_instruction=(
                "You are an expert on Kerala electricity regulation. "
                "Search for and cite official KSERC orders, Government of Kerala notifications, "
                "and RBI bank rates when relevant."
            ),
        )
        logger.info(f"Grounded query answered ({len(result)} chars)")
        return result
        
    except Exception as e:
        logger.error(f"Grounded query failed: {e}")
        return f"Grounded search failed: {str(e)}"


def query_precedent_for_component(
    component_name: str,
    licensee_name: str,
    claimed_amount: float,
    financial_year: str,
) -> str:
    """
    Query for specific precedent on how KSERC handled a component 
    in past truing-up orders.
    
    This is used by the Chief Auditor to understand past decisions.
    Combines file search (past orders) with grounded search (latest amendments).
    """
    question = f"""
    For the component "{component_name}" in a Truing-Up Petition by {licensee_name}
    for FY {financial_year}, the licensee has claimed ₹{claimed_amount:.2f} Lakhs.
    
    1. What does the KSERC Tariff Regulations say about this component?
    2. What was the approved amount for this component in the most recent 
       truing-up orders for {licensee_name} or similar SDL licensees?
    3. What calculation methodology did KSERC apply?
    4. Were there any special circumstances or exceptions granted?
    
    Provide specific clause numbers, order numbers, and amounts.
    """
    
    return query_regulations(question)
