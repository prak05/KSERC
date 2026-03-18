"""
KSERC Truing-Up — Vertex AI Search RAG Layer
=============================================
Module  : vertex_search.py
Purpose : Managed Vertex AI Search (Enterprise Search) integration as
          an alternative to the custom file_search_store.py RAG.

BENEFITS OVER CUSTOM RAG:
  - No custom embedding / chunking code needed
  - Google manages index updates, scaling, and relevance tuning
  - Supports hybrid search (semantic + keyword)
  - Built-in snippet extraction and inline citations

USAGE:
  This module provides a drop-in replacement for PrecedentLookup
  when Vertex AI Search is configured. Falls back to the existing
  file_search_store.py if Vertex AI Search is not configured.

SETUP (one-time, in Google Cloud Console):
  1. Enable "Vertex AI Search" API
  2. Create a Search App (type: Generic / Document)
  3. Upload KSERC order PDFs and regulation documents as a data store
  4. Set VERTEX_SEARCH_APP_ID in .env

ENVIRONMENT VARIABLES:
  VERTEX_SEARCH_APP_ID     : Vertex AI Search App ID
  GCP_PROJECT_ID           : Google Cloud Project ID (already in .env)
  VERTEX_SEARCH_LOCATION   : usually "global" (default)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

# Load .env early so VERTEX_SEARCH_APP_ID etc. are available at module init
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("kserc.vertex_search")

# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────

GCP_PROJECT_ID         = os.getenv("GCP_PROJECT_ID", "kserc-489316")
VERTEX_SEARCH_APP_ID   = os.getenv("VERTEX_SEARCH_APP_ID", "")
VERTEX_SEARCH_LOCATION = os.getenv("VERTEX_SEARCH_LOCATION", "global")
_AVAILABLE: Optional[bool] = None  # Cached availability check


def is_available() -> bool:
    """Check if Vertex AI Search is configured and available."""
    global _AVAILABLE
    if _AVAILABLE is not None:
        return _AVAILABLE

    if not VERTEX_SEARCH_APP_ID:
        logger.info("Vertex AI Search: VERTEX_SEARCH_APP_ID not set — disabled")
        _AVAILABLE = False
        return False

    try:
        from google.cloud import discoveryengine_v1 as discoveryengine  # noqa: F401
        _AVAILABLE = True
        logger.info(
            f"Vertex AI Search: available (app={VERTEX_SEARCH_APP_ID}, "
            f"project={GCP_PROJECT_ID})"
        )
    except ImportError:
        logger.warning(
            "Vertex AI Search: google-cloud-discoveryengine not installed. "
            "Run: pip install google-cloud-discoveryengine"
        )
        _AVAILABLE = False

    return _AVAILABLE


# ─────────────────────────────────────────────────────────────────────
# CORE SEARCH FUNCTION
# ─────────────────────────────────────────────────────────────────────

def search(
    query: str,
    num_results: int = 5,
    filter_expr: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search KSERC regulatory documents using Vertex AI Search.

    Parameters
    ----------
    query       : str  - Natural language query
    num_results : int  - Number of results to return (default 5)
    filter_expr : str  - Optional filter expression
                         e.g. 'category = "order" AND licensee = "KDHP"'

    Returns
    -------
    list of dicts with:
        title, snippet, document_name, relevance_score, source_url
    """
    if not is_available():
        return []

    try:
        import google.auth
        import google.auth.transport.requests
        import requests as _requests

        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        creds.refresh(google.auth.transport.requests.Request())

        hdrs = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        }

        # Use data store path directly — engine-based path returns 404 on new engines
        DATA_STORE_ID = "kserc-regulatory-docs"
        url = (
            f"https://discoveryengine.googleapis.com/v1/projects/{GCP_PROJECT_ID}"
            f"/locations/{VERTEX_SEARCH_LOCATION}/collections/default_collection"
            f"/dataStores/{DATA_STORE_ID}/servingConfigs/default_search:search"
        )

        payload: dict = {"query": query, "pageSize": num_results}
        if filter_expr:
            payload["filter"] = filter_expr

        resp = _requests.post(url, headers=hdrs, json=payload, timeout=10)

        if resp.status_code != 200:
            logger.error(f"Vertex AI Search REST error: {resp.status_code} {resp.text[:200]}")
            return []

        results = []
        for item in resp.json().get("results", []):
            doc = item.get("document", {})
            derived = doc.get("derivedStructData", {})
            snippets = derived.get("snippets", [])
            snippet = ""
            if snippets:
                snippet = snippets[0].get("snippet", "") if isinstance(snippets[0], dict) else str(snippets[0])

            results.append({
                "title": derived.get("title", doc.get("name", "").split("/")[-1]),
                "snippet": snippet,
                "document_name": doc.get("name", ""),
                "relevance_score": item.get("relevanceScore", 0.0),
                "source_url": derived.get("link", ""),
            })

        logger.info(f"Vertex AI Search: '{query[:50]}' → {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"Vertex AI Search error: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────
# SPECIALIZED SEARCH FUNCTIONS
# ─────────────────────────────────────────────────────────────────────

def search_precedents(
    component: str,
    licensee: str = "",
    num_results: int = 5,
) -> List[Dict[str, Any]]:
    """
    Search for KSERC precedent decisions for a specific expense component.

    Parameters
    ----------
    component   : str  - e.g. "employee_cost", "repair_maintenance"
    licensee    : str  - Optional licensee name for targeted search
    num_results : int  - Results to return

    Returns
    -------
    list of precedent search results
    """
    # Build a targeted regulatory query
    component_labels = {
        "employee_cost":    "employee cost salaries",
        "repair_maintenance": "repair maintenance R&M expenses",
        "admin_general":    "administration general expenses A&G",
        "depreciation":     "depreciation fixed assets",
        "power_purchase_cost": "power purchase cost KSEB",
        "return_on_nfa":    "return on net fixed assets RoNFA",
        "interest_long_term": "interest normative loan long term",
    }
    label = component_labels.get(component, component.replace("_", " "))

    if licensee:
        query = f"KSERC {licensee} {label} truing up approved disallowed"
    else:
        query = f"KSERC {label} truing up order approved disallowed regulatory"

    return search(query, num_results=num_results)


def search_regulations(regulation_ref: str, num_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search for specific KSERC regulation text.

    Parameters
    ----------
    regulation_ref : str - e.g. "Regulation 80(3)" or "tariff regulations 2021"
    num_results    : int - Results to return

    Returns
    -------
    list of regulation search results
    """
    query = f"KSERC {regulation_ref} tariff regulations text"
    return search(query, num_results=num_results)


# ─────────────────────────────────────────────────────────────────────
# ENHANCED PRECEDENT LOOKUP (drop-in enrichment for precedent_lookup.py)
# ─────────────────────────────────────────────────────────────────────

def enrich_justification_with_search(
    component: str,
    licensee: str,
    claimed: float,
    approved: float,
    fy: str,
) -> str:
    """
    Enrich a disallowance justification with Vertex AI Search results.
    Returns additional text to append to the existing justification.

    Used by auditor._audit_norm_capped_component() when
    Vertex AI Search is available.
    """
    if not is_available():
        return ""

    results = search_precedents(component, licensee, num_results=2)
    if not results:
        return ""

    snippets = [r["snippet"] for r in results if r.get("snippet")]
    if not snippets:
        return ""

    # Return first useful snippet as additional context
    return f" Reference: {snippets[0][:200]}..."
