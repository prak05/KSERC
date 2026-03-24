"""
Centralized Google Gemini client using the google-genai SDK via Vertex AI.

Uses Vertex AI authentication (service account) for higher rate limits
and to leverage GCP billing credits ($300 free trial).

All agents should import from here instead of directly using vertexai.
"""

import os
import logging
from typing import Optional

from dotenv import load_dotenv
from src.config import GEMINI_MODEL

logger = logging.getLogger("kserc.gemini_client")

# Load environment variables
load_dotenv(override=True)

_client = None

def get_client():
    """
    Get or create a singleton google.genai.Client using Vertex AI.
    
    Uses GOOGLE_APPLICATION_CREDENTIALS (service account JSON) for auth.
    Falls back to API key if Vertex AI setup fails.
    """
    global _client
    if _client is not None:
        return _client
    
    try:
        from google import genai
    except ImportError:
        raise ImportError(
            "google-genai is not installed. Run: pip install google-genai"
        )
    
    project_id = os.getenv("GCP_PROJECT_ID", "kserc-trueup-v2")
    location = "asia-south1"  # Closest region to India
    
    # Use Vertex AI as primary (supports response_schema with Pydantic models)
    try:
        _client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
        )
        logger.info(f"Gemini client initialized via Vertex AI (project={project_id}, location={location})")
        return _client
    except Exception as e:
        logger.warning(f"Vertex AI init failed: {e}, falling back to API key")
    
    # Fallback to API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "Neither Vertex AI nor GOOGLE_API_KEY available. "
            "Set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_API_KEY in .env."
        )
    
    _client = genai.Client(api_key=api_key)
    logger.info("Gemini client initialized with API key (fallback)")
    return _client


_api_key_client = None

def get_api_key_client():
    """
    Get a separate API-key-based client for heavy operations like deep extraction.
    
    Uses the GOOGLE_API_KEY from .env. This client has higher rate limits
    compared to Vertex AI and is used for deep table extraction.
    Returns None if no API key is available (caller should fall back to get_client).
    """
    global _api_key_client
    if _api_key_client is not None:
        return _api_key_client
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    
    try:
        from google import genai
        _api_key_client = genai.Client(api_key=api_key)
        logger.info("API key client initialized for deep extraction")
        return _api_key_client
    except Exception as e:
        logger.warning(f"API key client init failed: {e}")
        return None


def get_config(
    temperature: float = 0.0,
    response_mime_type: str = "application/json",
    max_output_tokens: Optional[int] = None,
):
    """
    Create a GenerateContentConfig object.
    
    Replaces the old vertexai GenerationConfig.
    """
    from google.genai import types
    
    kwargs = {
        "temperature": temperature,
        "response_mime_type": response_mime_type,
    }
    if max_output_tokens:
        kwargs["max_output_tokens"] = max_output_tokens
    
    return types.GenerateContentConfig(**kwargs)


def generate(
    prompt: str,
    model: str = GEMINI_MODEL,
    temperature: float = 0.0,
    response_mime_type: str = "application/json",
    response_schema: Optional[type] = None,
    system_instruction: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
) -> str:
    """
    Simple wrapper to generate content with Gemini.
    
    Args:
        response_schema: Optional Pydantic model class for structured output.
    
    Returns the raw response text.
    """
    client = get_client()
    from google.genai import types
    
    config_kwargs = {
        "temperature": temperature,
        "response_mime_type": response_mime_type,
    }
    if response_schema:
        config_kwargs["response_schema"] = response_schema
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    if max_output_tokens:
        config_kwargs["max_output_tokens"] = max_output_tokens
    
    config = types.GenerateContentConfig(**config_kwargs)
    
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    
    return response.text


def generate_with_parts(
    parts: list,
    model: str = GEMINI_MODEL,
    temperature: float = 0.0,
    response_mime_type: str = "application/json",
    response_schema: Optional[type] = None,
    system_instruction: Optional[str] = None,
) -> str:
    """
    Generate content with multimodal parts (text + images/files).
    
    Args:
        response_schema: Optional Pydantic model class for structured output.
    """
    client = get_client()
    from google.genai import types
    
    config_kwargs = {
        "temperature": temperature,
        "response_mime_type": response_mime_type,
    }
    if response_schema:
        config_kwargs["response_schema"] = response_schema
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    
    config = types.GenerateContentConfig(**config_kwargs)
    
    response = client.models.generate_content(
        model=model,
        contents=parts,
        config=config,
    )
    
    return response.text


def generate_with_pdf(
    pdf_path,  # str or List[str] — single path or multiple paths
    prompt: str,
    model: str = GEMINI_MODEL,
    temperature: float = 0.0,
    response_mime_type: str = "application/json",
    system_instruction: Optional[str] = None,
    response_schema = None,
    client = None,  # Optional: pass a specific client (e.g. API key client)
) -> str:
    """
    Generate content by uploading PDF file(s) to Gemini.
    
    Accepts either a single PDF path (str) or a list of PDF paths (List[str]).
    When multiple PDFs are provided, ALL are uploaded and sent together
    in a single Gemini call — enabling cross-referencing between files
    (e.g., main petition + annexures + audit reports).
    
    For Vertex AI: uses inline bytes (Part.from_bytes) instead of Files API.
    For API key fallback: uses Files API upload.
    """
    import time
    from pathlib import Path
    if client is None:
        client = get_client()
    from google.genai import types

    # Normalize to list
    pdf_paths = pdf_path if isinstance(pdf_path, list) else [pdf_path]

    # Build parts with inline bytes (works for both Vertex AI and API key)
    parts = []
    upload_start = time.time()
    
    for path in pdf_paths:
        logger.info(f"Loading PDF: {path}")
        pdf_bytes = Path(path).read_bytes()
        parts.append(types.Part.from_bytes(
            data=pdf_bytes,
            mime_type="application/pdf",
        ))
        logger.info(f"  Loaded: {len(pdf_bytes):,} bytes")
    
    parts.append(types.Part.from_text(text=prompt))
    
    upload_time = time.time() - upload_start
    logger.info(f"{len(pdf_paths)} PDF(s) loaded in {upload_time:.1f}s")

    config_kwargs = {
        "temperature": temperature,
        "response_mime_type": response_mime_type,
    }
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    if response_schema:
        config_kwargs["response_schema"] = response_schema

    config = types.GenerateContentConfig(**config_kwargs)

    gen_start = time.time()
    response = client.models.generate_content(
        model=model,
        contents=parts,
        config=config,
    )
    gen_time = time.time() - gen_start
    logger.info(f"PDF generation completed in {gen_time:.1f}s")

    return response.text


def generate_grounded(
    prompt: str,
    model: str = GEMINI_MODEL,
    temperature: float = 0.3,
    system_instruction: Optional[str] = None,
) -> str:
    """
    Generate content with Google Search grounding enabled.
    
    Gemini will automatically search the web when needed to provide
    factual, up-to-date information with inline citations.
    
    Best for: legal research, regulation lookups, electricity tariff queries.
    """
    client = get_client()
    from google.genai import types

    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    
    config_kwargs = {
        "temperature": temperature,
        "tools": [grounding_tool],
    }
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction

    config = types.GenerateContentConfig(**config_kwargs)

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )

    return response.text


# Project configuration for Document AI
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "kserc-trueup-v2")
DOCUMENT_AI_PROCESSOR_ID = os.getenv("DOCUMENT_AI_PROCESSOR_ID", "")
DOCUMENT_AI_LOCATION = os.getenv("DOCUMENT_AI_LOCATION", "us")
