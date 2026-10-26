"""
Extraction Cache — Persistent document store cache for reference document extraction.

Replaces the local .extraction_cache/ directory (which is lost on every ECS Fargate
deployment) with document store-backed persistence.

Strategy: ALWAYS store data as a JSON string in document store to avoid nested entity
limits. document store has a 20-level nesting limit and can't handle arrays-of-objects
well, but our extraction data is deeply nested. Storing as a JSON string bypasses
this limitation entirely.

Cache collections:
  - deep_extract_cache/{hash}     — Petition deep table extraction results
  - order_extract_cache/{hash}    — Past order KSERC decision extraction
  - order_learnings_cache/all     — Combined all-order learnings
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Also keep local fallback for non-production environments
LOCAL_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".extraction_cache"


def _get_store():
    """Shared document store on AWS; locally the JSON files in .extraction_cache are enough."""
    from src.cloud import settings

    if not settings.IS_AWS:
        return None
    try:
        from src.cloud.docstore import client

        return client()
    except Exception as e:
        logger.error(f"[Cache] Cannot open document store: {e}")
        return None


def compute_pdf_hash(pdf_paths) -> str:
    """Compute SHA-256 hash of one or more PDF files."""
    if isinstance(pdf_paths, str):
        pdf_paths = [pdf_paths]
    h = hashlib.sha256()
    for pdf_path in sorted(pdf_paths):
        try:
            with open(pdf_path, "rb") as f:
                while chunk := f.read(8192):
                    h.update(chunk)
        except Exception as e:
            logger.error(f"Failed to hash {pdf_path}: {e}")
            return ""
    return h.hexdigest()[:16]


# ════════════════════════════════════════════════════════════════════════
# Generic get/save with document store + local fallback
# ════════════════════════════════════════════════════════════════════════

def _get_cached(collection: str, key: str) -> Optional[Dict]:
    """Try document store first, then local file fallback."""
    # Try document store
    db = _get_store()
    if db:
        try:
            doc = db.collection(collection).document(key).get()
            if doc.exists:
                raw = doc.to_dict()
                # We always store as JSON string now
                json_str = raw.get("data")
                if json_str:
                    data = json.loads(json_str)
                    logger.info(f"[Cache] HIT (document store) {collection}/{key}")
                    return data
                else:
                    # Legacy format: try to use dict directly
                    raw.pop("_cached_at", None)
                    raw.pop("_format", None)
                    if raw:
                        logger.info(f"[Cache] HIT (document store legacy) {collection}/{key}")
                        return raw
        except Exception as e:
            logger.warning(f"[Cache] document store read failed: {e}")
    
    # Fallback: local file
    local_file = LOCAL_CACHE_DIR / f"{key}.json"
    if local_file.exists():
        try:
            data = json.loads(local_file.read_text(encoding="utf-8"))
            logger.info(f"[Cache] HIT (local) {local_file.name}")
            # Migrate to document store if available
            if db:
                _save_to_store(db, collection, key, data)
            return data
        except Exception as e:
            logger.warning(f"[Cache] Local read failed: {e}")
    
    logger.info(f"[Cache] MISS {collection}/{key}")
    return None


def _save_cached(collection: str, key: str, data: Dict):
    """Save to both document store and local file."""
    # Save to document store
    db = _get_store()
    if db:
        _save_to_store(db, collection, key, data)
    
    # Also save locally as backup
    try:
        LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        local_file = LOCAL_CACHE_DIR / f"{key}.json"
        local_file.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
        logger.info(f"[Cache] SAVED (local) {local_file.name}")
    except Exception as e:
        logger.warning(f"[Cache] Local save failed: {e}")


def _save_to_store(db, collection: str, key: str, data: Dict):
    """
    Save to document store as a JSON string.
    
    We ALWAYS serialize the data as a JSON string to avoid document store's
    nested entity limits (arrays-of-objects, 20-level nesting, etc.).
    """
    import datetime
    try:
        serialized = json.dumps(data, default=str)
        
        # document store doc limit is ~1MB
        if len(serialized) > 950_000:
            logger.warning(
                f"[Cache] Doc too large for document store ({len(serialized)} bytes), "
                f"skipping document store save for {collection}/{key}"
            )
            return
        
        cache_doc = {
            "_cached_at": datetime.datetime.now().isoformat(),
            "_format": "json_string",
            "data": serialized,
        }
        
        db.collection(collection).document(key).set(cache_doc)
        logger.info(f"[Cache] SAVED (document store) {collection}/{key} ({len(serialized)} bytes)")
    except Exception as e:
        logger.error(f"[Cache] document store save failed: {e}")


# ════════════════════════════════════════════════════════════════════════
# Public API — Deep Petition Table Extraction Cache
# ════════════════════════════════════════════════════════════════════════

def get_cached_deep_extraction(pdf_hash: str, licensee: str, fy: str) -> Optional[Dict]:
    key = f"deep_{pdf_hash}_{licensee}_{fy}".replace(" ", "_")
    return _get_cached("deep_extract_cache", key)


def save_deep_extraction_cache(pdf_hash: str, licensee: str, fy: str, result: Dict):
    key = f"deep_{pdf_hash}_{licensee}_{fy}".replace(" ", "_")
    _save_cached("deep_extract_cache", key, result)


# ════════════════════════════════════════════════════════════════════════
# Public API — Past Order KSERC Decision Cache
# ════════════════════════════════════════════════════════════════════════

def get_cached_order_extraction(pdf_hash: str, licensee: str, fy: str) -> Optional[Dict]:
    key = f"order_deep_{pdf_hash}_{licensee}_{fy}".replace(" ", "_")
    return _get_cached("order_extract_cache", key)


def save_order_extraction_cache(pdf_hash: str, licensee: str, fy: str, result: Dict):
    key = f"order_deep_{pdf_hash}_{licensee}_{fy}".replace(" ", "_")
    _save_cached("order_extract_cache", key, result)


# ════════════════════════════════════════════════════════════════════════
# Public API — Combined All-Order Learnings Cache
# ════════════════════════════════════════════════════════════════════════

def get_cached_all_order_learnings() -> Optional[Dict]:
    return _get_cached("order_learnings_cache", "all")


def save_all_order_learnings(data: Dict):
    _save_cached("order_learnings_cache", "all", data)
