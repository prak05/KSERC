# [Purpose] Remote RAG index operations (Cloudflare Worker + R2)
# [Source] User defined integration for offloading indexing
# [Why] Prevents local indexing from exhausting memory/CPU

# [Library] typing - Type hints
# [Why] Improves clarity and IDE support
from typing import Dict, Any, List, Optional

# [Library] httpx - HTTP client for remote indexing service
# [Why] Required for Cloudflare Worker calls
import httpx

# [User Defined] Import configuration settings
# [Source] src/config.py
# [Why] Access remote base URL and auth token
from src.config import settings


def _build_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if settings.RAG_REMOTE_TOKEN:
        headers["Authorization"] = f"Bearer {settings.RAG_REMOTE_TOKEN}"
    return headers


async def remote_index_seed() -> Dict[str, Any]:
    """
    [Purpose] Trigger remote seed indexing on Cloudflare Worker
    [Why] Moves heavy PDF parsing off the local machine
    """
    if not settings.RAG_REMOTE_BASE_URL:
        raise ValueError("RAG_REMOTE_BASE_URL not set")
    url = f"{settings.RAG_REMOTE_BASE_URL}/rag/index-seed"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, headers=_build_headers())
        response.raise_for_status()
        return response.json()


async def remote_upload_files(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    [Purpose] Upload files to remote indexer
    [Why] Offloads indexing to Cloudflare Worker
    """
    if not settings.RAG_REMOTE_BASE_URL:
        raise ValueError("RAG_REMOTE_BASE_URL not set")
    url = f"{settings.RAG_REMOTE_BASE_URL}/rag/upload"
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, headers=_build_headers(), files=files)
        response.raise_for_status()
        return response.json()


async def fetch_remote_index() -> Dict[str, Any]:
    """
    [Purpose] Fetch latest RAG index from Cloudflare Worker
    [Why] Keeps backend retrieval in sync with remote index
    """
    if not settings.RAG_REMOTE_BASE_URL:
        raise ValueError("RAG_REMOTE_BASE_URL not set")
    url = f"{settings.RAG_REMOTE_BASE_URL}/rag/index"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url, headers=_build_headers())
        response.raise_for_status()
        return response.json()
