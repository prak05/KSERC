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
    system_instruction: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
) -> str:
    """
    Simple wrapper to generate content with Gemini.
    
    Returns the raw response text.
    
    Usage:
        from src.gemini_client import generate
        result = generate("Extract data from...", model="gemini-2.5-pro")
    """
    client = get_client()
    from google.genai import types
    
    config_kwargs = {
        "temperature": temperature,
        "response_mime_type": response_mime_type,
    }
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
    system_instruction: Optional[str] = None,
) -> str:
    """
    Generate content with multimodal parts (text + images/files).
    
    Replaces the old vertexai Part.from_data pattern.
    
    Usage:
        from google.genai import types
        parts = [
            types.Part.from_text("Analyze this image"),
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        ]
        result = generate_with_parts(parts, model="gemini-2.5-pro")
    """
    client = get_client()
    from google.genai import types
    
    config_kwargs = {
        "temperature": temperature,
        "response_mime_type": response_mime_type,
    }
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    
    config = types.GenerateContentConfig(**config_kwargs)
    
    response = client.models.generate_content(
        model=model,
        contents=parts,
        config=config,
    )
    
    return response.text


# Project configuration for Document AI
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "kserc-489315")
DOCUMENT_AI_PROCESSOR_ID = os.getenv("DOCUMENT_AI_PROCESSOR_ID", "")
DOCUMENT_AI_LOCATION = os.getenv("DOCUMENT_AI_LOCATION", "us")
