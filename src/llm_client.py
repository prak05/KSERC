"""
Single entry point for language-model calls. All agents import from here.

The backend (Claude on Amazon Bedrock, a local model server, or offline) is chosen
by ``LLM_PROVIDER`` — see ``src.cloud.llm``.
"""

from src.cloud.llm import (  # noqa: F401
    extract_json_text,
    generate,
    generate_grounded,
    generate_with_parts,
    generate_with_pdf,
    get_client,
)


def get_config(temperature: float = 0.0, response_mime_type: str = "application/json", max_output_tokens=None):
    from src.cloud.llm_types import GenerateContentConfig

    return GenerateContentConfig(temperature=temperature, response_mime_type=response_mime_type,
                                 max_output_tokens=max_output_tokens)
