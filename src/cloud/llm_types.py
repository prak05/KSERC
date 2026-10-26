"""
Provider-neutral message parts and generation config.

The agents were written against a ``types.Part`` / ``types.GenerateContentConfig``
call shape. These classes keep that shape so the extraction, audit and drafting
logic is unchanged, while the backend (Bedrock or a local server) is chosen in
``src.cloud.llm``.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Part:
    text: Optional[str] = None
    data: Optional[bytes] = None
    mime_type: Optional[str] = None

    @classmethod
    def from_text(cls, text: str) -> "Part":
        return cls(text=text)

    @classmethod
    def from_bytes(cls, data: bytes, mime_type: str) -> "Part":
        return cls(data=data, mime_type=mime_type)


class GenerateContentConfig:
    """``temperature`` is accepted for call-site compatibility; current Claude models don't take it."""

    def __init__(self, temperature=None, response_mime_type=None, response_schema=None,
                 system_instruction=None, max_output_tokens=None, **extra):
        self.temperature = temperature
        self.response_mime_type = response_mime_type
        self.response_schema = response_schema
        self.system_instruction = system_instruction
        self.max_output_tokens = max_output_tokens
        self.extra = extra
