"""
Centralized Google Gemini client using the google-genai SDK.

All agents should import from here instead of directly using vertexai.
Uses API key authentication (from .env) — no service account needed for Gemini.
"""

import os
import logging
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger("kserc.gemini_client")

# Load environment variables
load_dotenv()

_client = None

def get_client():
    """
    Get or create a singleton google.genai.Client.
    
    Uses GOOGLE_API_KEY from .env for authentication.
    This replaces the old vertexai.init() + GenerativeModel pattern.
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
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not found in environment. "
            "Set it in .env or as an environment variable."
        )
    
    _client = genai.Client(api_key=api_key)
    logger.info("Gemini client initialized with API key")
    return _client


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
    model: str = "gemini-2.5-pro",
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
    model: str = "gemini-2.5-pro",
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
    model: str = "gemini-2.5-pro",
    temperature: float = 0.0,
    response_mime_type: str = "application/json",
    system_instruction: Optional[str] = None,
    response_schema = None,
) -> str:
    """
    Generate content by uploading PDF file(s) to Gemini.
    
    Accepts either a single PDF path (str) or a list of PDF paths (List[str]).
    When multiple PDFs are provided, ALL are uploaded and sent together
    in a single Gemini call — enabling cross-referencing between files
    (e.g., main petition + annexures + audit reports).
    
    Uses Gemini Files API: client.files.upload() for each PDF,
    then passes all file references + prompt in one generate_content call.
    """
    import time
    client = get_client()
    from google.genai import types

    # Normalize to list
    pdf_paths = pdf_path if isinstance(pdf_path, list) else [pdf_path]

    # Upload all PDF files to Gemini Files API
    uploaded_files = []
    upload_start = time.time()
    
    for path in pdf_paths:
        logger.info(f"Uploading PDF to Gemini Files API: {path}")
        uploaded = client.files.upload(
            file=path,
            config=types.UploadFileConfig(
                mime_type="application/pdf",
            ),
        )
        uploaded_files.append(uploaded)
        logger.info(f"  Uploaded: {uploaded.name}")
    
    upload_time = time.time() - upload_start
    logger.info(f"{len(uploaded_files)} PDF(s) uploaded in {upload_time:.1f}s")

    # Build parts: all file references first, then the prompt
    parts = []
    for uf in uploaded_files:
        parts.append(types.Part.from_uri(
            file_uri=uf.uri,
            mime_type="application/pdf",
        ))
    parts.append(types.Part.from_text(text=prompt))

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

    # Clean up uploaded files (best effort)
    for uf in uploaded_files:
        try:
            client.files.delete(name=uf.name)
        except Exception:
            pass  # Non-critical — files auto-expire after 48h

    return response.text


def generate_grounded(
    prompt: str,
    model: str = "gemini-2.5-pro",
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
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "kserc-489315")
DOCUMENT_AI_PROCESSOR_ID = os.getenv("DOCUMENT_AI_PROCESSOR_ID", "")
DOCUMENT_AI_LOCATION = os.getenv("DOCUMENT_AI_LOCATION", "us")
