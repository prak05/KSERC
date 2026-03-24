"""
Extraction Cache — Cache Gemini Vision extraction results in Firestore.

Caches are keyed by SHA-256 hash of the uploaded PDF file contents.
This avoids re-processing the same PDFs through Gemini Vision on repeat runs.
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def compute_pdf_hash(pdf_paths: List[str]) -> str:
    """Compute a combined SHA-256 hash of all uploaded PDF files."""
    h = hashlib.sha256()
    for pdf_path in sorted(pdf_paths):  # Sort for deterministic hash
        try:
            with open(pdf_path, "rb") as f:
                while chunk := f.read(8192):
                    h.update(chunk)
        except Exception as e:
            logger.error(f"Failed to hash {pdf_path}: {e}")
            return ""
    return h.hexdigest()


def _get_firestore():
    """Get Firestore client (reuses existing initialization from db.py)."""
    try:
        from src.tools.db import get_firestore_client
        return get_firestore_client()
    except Exception:
        # Fallback: initialize directly
        import firebase_admin
        from firebase_admin import firestore
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app()
        return firestore.client()


def get_cached_extraction(pdf_hash: str) -> Optional[Dict]:
    """
    Check if extraction results exist in Firestore cache.
    Returns the cached extraction result dict, or None if not cached.
    """
    if not pdf_hash:
        return None
    
    env = os.environ.get("ENVIRONMENT", "local")
    if env != "production":
        logger.info(f"[Cache] Skipping cache lookup (env={env})")
        return None
    
    try:
        db = _get_firestore()
        doc = db.collection("extraction_cache").document(pdf_hash).get()
        if doc.exists:
            data = doc.to_dict()
            logger.info(f"[Cache] HIT — extraction cache for hash {pdf_hash[:12]}… "
                       f"({len(data.get('claimed_expenses', {}))} expense components)")
            return data
        else:
            logger.info(f"[Cache] MISS — no extraction cache for hash {pdf_hash[:12]}…")
            return None
    except Exception as e:
        logger.error(f"[Cache] Failed to read extraction cache: {e}")
        return None


def save_extraction_cache(pdf_hash: str, result: Dict):
    """Save extraction result to Firestore cache."""
    if not pdf_hash:
        return
    
    env = os.environ.get("ENVIRONMENT", "local")
    if env != "production":
        return
    
    try:
        db = _get_firestore()
        # Store with metadata
        cache_doc = dict(result)  # shallow copy
        cache_doc["_cached_at"] = __import__("datetime").datetime.now().isoformat()
        cache_doc["_hash"] = pdf_hash
        
        db.collection("extraction_cache").document(pdf_hash).set(cache_doc)
        logger.info(f"[Cache] SAVED extraction cache for hash {pdf_hash[:12]}…")
    except Exception as e:
        logger.error(f"[Cache] Failed to save extraction cache: {e}")


def get_cached_deep_extraction(pdf_hash: str) -> Optional[Dict]:
    """Check if deep extraction results exist in cache."""
    if not pdf_hash:
        return None
    
    env = os.environ.get("ENVIRONMENT", "local")
    if env != "production":
        return None
    
    try:
        db = _get_firestore()
        doc = db.collection("deep_extract_cache").document(pdf_hash).get()
        if doc.exists:
            data = doc.to_dict()
            logger.info(f"[Cache] HIT — deep extraction cache for hash {pdf_hash[:12]}…")
            return data
        else:
            logger.info(f"[Cache] MISS — no deep extraction cache for hash {pdf_hash[:12]}…")
            return None
    except Exception as e:
        logger.error(f"[Cache] Failed to read deep extraction cache: {e}")
        return None


def save_deep_extraction_cache(pdf_hash: str, result: Dict):
    """Save deep extraction result to Firestore cache."""
    if not pdf_hash:
        return
    
    env = os.environ.get("ENVIRONMENT", "local")
    if env != "production":
        return
    
    try:
        db = _get_firestore()
        cache_doc = dict(result)
        cache_doc["_cached_at"] = __import__("datetime").datetime.now().isoformat()
        cache_doc["_hash"] = pdf_hash
        
        db.collection("deep_extract_cache").document(pdf_hash).set(cache_doc)
        logger.info(f"[Cache] SAVED deep extraction cache for hash {pdf_hash[:12]}…")
    except Exception as e:
        logger.error(f"[Cache] Failed to save deep extraction cache: {e}")
