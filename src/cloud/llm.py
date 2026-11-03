"""
Language-model gateway.

Every agent reaches the model through this module. It exposes a small client with
``client.models.generate_content(model=..., contents=..., config=...)`` returning an
object with ``.text`` — the call shape the agents were built on — and routes it to:

* ``bedrock`` — Claude on Amazon Bedrock via the Anthropic SDK's Mantle client.
  Auth is the ECS task's IAM role (or your local AWS profile); there is no key.
  Refusals are retried on ``LLM_FALLBACK_MODEL`` by the SDK's fallback middleware.
* ``local``   — an OpenAI-compatible model server on this machine (Ollama, LM Studio,
  llama.cpp). PDFs are sent as extracted text.
* ``offline`` — no model. JSON requests get ``{}``; the deterministic rules engine
  still produces the full audit.
"""

import base64
import json
import logging
import re
import time
from pathlib import Path
from typing import Iterable, List, Optional, Union

import requests

from src.cloud import settings
from src.cloud.llm_types import GenerateContentConfig, Part

logger = logging.getLogger("kserc.llm")

# Bedrock request ceiling is 32 MB; keep headroom for base64 growth and prompt text.
_MAX_INLINE_BYTES = 20 * 1024 * 1024
_MAX_PDF_PAGES = 600

ContentLike = Union[str, Part, Iterable[Union[str, Part]]]


class Response:
    def __init__(self, text: str):
        self.text = text


# ═══════════════════════════════════════════════════════════════════════
# Content normalisation
# ═══════════════════════════════════════════════════════════════════════

def _as_parts(contents: ContentLike) -> List[Part]:
    if isinstance(contents, (str, Part)):
        contents = [contents]
    return [Part.from_text(c) if isinstance(c, str) else c for c in contents]


def _pdf_text(data: bytes) -> str:
    import fitz

    with fitz.open(stream=data, filetype="pdf") as doc:
        return "\n".join(f"\n--- Page {p.number + 1} ---\n{p.get_text('text')}" for p in doc)


def _split_pdf(data: bytes) -> List[bytes]:
    """Split a PDF into page ranges that each fit the per-request limits."""
    import fitz

    src = fitz.open(stream=data, filetype="pdf")
    pages = src.page_count
    chunks, start = [], 0
    step = max(1, min(_MAX_PDF_PAGES, int(pages * _MAX_INLINE_BYTES / max(len(data), 1))))
    while start < pages:
        end = min(pages, start + step)
        out = fitz.open()
        out.insert_pdf(src, from_page=start, to_page=end - 1)
        chunks.append(out.tobytes(garbage=3, deflate=True))
        out.close()
        start = end
    src.close()
    return chunks


def _schema_instruction(schema) -> str:
    try:
        if hasattr(schema, "model_json_schema"):
            schema = schema.model_json_schema()
        return "\n\nReturn JSON that conforms to this JSON Schema:\n" + json.dumps(schema, indent=1)
    except Exception:
        return ""


_JSON_RULE = (
    "Respond with a single valid JSON value only — no prose, no markdown code fences."
)


def extract_json_text(text: str) -> str:
    """Strip code fences / leading prose so callers that json.loads() the reply succeed."""
    t = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, re.S)
    if fence:
        return fence.group(1).strip()
    if t[:1] in "{[":
        return t
    m = re.search(r"[\[{].*[\]}]", t, re.S)
    return m.group(0) if m else t


# ═══════════════════════════════════════════════════════════════════════
# Bedrock (Claude)
# ═══════════════════════════════════════════════════════════════════════

_bedrock_client = None


def _bedrock():
    global _bedrock_client
    if _bedrock_client is None:
        from anthropic import AnthropicBedrockMantle, BetaRefusalFallbackMiddleware

        middleware = []
        if settings.LLM_FALLBACK_MODEL:
            middleware.append(BetaRefusalFallbackMiddleware([{"model": settings.LLM_FALLBACK_MODEL}]))
        _bedrock_client = AnthropicBedrockMantle(
            aws_region=settings.BEDROCK_REGION,
            middleware=middleware,
            timeout=900.0,
            max_retries=4,
        )
        logger.info(f"Bedrock client ready (region={settings.BEDROCK_REGION}, model={settings.LLM_MODEL})")
    return _bedrock_client


def _bedrock_blocks(parts: List[Part]) -> list:
    blocks, budget = [], _MAX_INLINE_BYTES
    for p in parts:
        if p.text is not None:
            blocks.append({"type": "text", "text": p.text})
        elif p.mime_type == "application/pdf":
            pieces = [p.data] if len(p.data) <= _MAX_INLINE_BYTES else _split_pdf(p.data)
            for piece in pieces:
                if len(piece) <= budget:
                    blocks.append({"type": "document", "source": {
                        "type": "base64", "media_type": "application/pdf",
                        "data": base64.standard_b64encode(piece).decode()}})
                    budget -= len(piece)
                else:  # over the request ceiling: send the remaining pages as text
                    blocks.append({"type": "text", "text": _pdf_text(piece)})
        elif p.mime_type and p.mime_type.startswith("image/"):
            blocks.append({"type": "image", "source": {
                "type": "base64", "media_type": p.mime_type,
                "data": base64.standard_b64encode(p.data).decode()}})
            budget -= len(p.data)
        elif p.data is not None:
            blocks.append({"type": "text", "text": p.data.decode("utf-8", "replace")})
    # Documents and images read best before the instructions.
    blocks.sort(key=lambda b: b["type"] == "text")
    return blocks


def _generate_bedrock(parts: List[Part], cfg: GenerateContentConfig) -> str:
    system = cfg.system_instruction or ""
    if cfg.response_mime_type == "application/json":
        system = (system + "\n\n" + _JSON_RULE).strip()
    if cfg.response_schema is not None:
        system += _schema_instruction(cfg.response_schema)

    kwargs = dict(
        model=settings.LLM_MODEL,
        max_tokens=cfg.max_output_tokens or settings.LLM_MAX_TOKENS,
        messages=[{"role": "user", "content": _bedrock_blocks(parts)}],
        output_config={"effort": settings.LLM_EFFORT},
    )
    if system:
        kwargs["system"] = system

    with _bedrock().beta.messages.stream(**kwargs) as stream:
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        raise RuntimeError("The model declined this request (refusal).")
    if message.stop_reason == "max_tokens":
        logger.warning("Model output hit max_tokens; response may be truncated")
    return "".join(b.text for b in message.content if b.type == "text")


# ═══════════════════════════════════════════════════════════════════════
# Local model server (OpenAI-compatible: Ollama, LM Studio, llama.cpp)
# ═══════════════════════════════════════════════════════════════════════

def _generate_local(parts: List[Part], cfg: GenerateContentConfig) -> str:
    content = []
    for p in parts:
        if p.text is not None:
            content.append({"type": "text", "text": p.text})
        elif p.mime_type == "application/pdf":
            content.append({"type": "text", "text": _pdf_text(p.data)})
        elif p.mime_type and p.mime_type.startswith("image/"):
            b64 = base64.standard_b64encode(p.data).decode()
            content.append({"type": "image_url", "image_url": {"url": f"data:{p.mime_type};base64,{b64}"}})

    messages = []
    system = cfg.system_instruction or ""
    if cfg.response_schema is not None:
        system += _schema_instruction(cfg.response_schema)
    if cfg.response_mime_type == "application/json":
        system = (system + "\n\n" + _JSON_RULE).strip()
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": content})

    body = {"model": settings.LOCAL_LLM_MODEL, "messages": messages, "stream": False}
    if cfg.response_mime_type == "application/json":
        body["response_format"] = {"type": "json_object"}
    r = requests.post(f"{settings.LOCAL_LLM_URL.rstrip('/')}/chat/completions", json=body, timeout=1800)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"] or ""


# ═══════════════════════════════════════════════════════════════════════
# Client facade
# ═══════════════════════════════════════════════════════════════════════

class _Models:
    def generate_content(self, model: Optional[str] = None, contents: ContentLike = "",
                         config: Optional[GenerateContentConfig] = None) -> Response:
        cfg = config or GenerateContentConfig()
        parts = _as_parts(contents)
        provider = settings.LLM_PROVIDER
        start = time.time()

        if provider == "offline":
            text = "{}" if cfg.response_mime_type == "application/json" else ""
        elif provider == "bedrock":
            text = _generate_bedrock(parts, cfg)
        elif provider == "local":
            text = _generate_local(parts, cfg)
        else:
            raise ValueError(f"Unknown LLM_PROVIDER '{provider}' (use bedrock, local or offline)")

        if cfg.response_mime_type == "application/json":
            text = extract_json_text(text)
        logger.info(f"[{provider}] generated {len(text):,} chars in {time.time() - start:.1f}s")
        return Response(text)


class Client:
    models = _Models()


_client = Client()


def get_client() -> Client:
    return _client


def _config(temperature, response_mime_type, response_schema, system_instruction, max_output_tokens=None):
    return GenerateContentConfig(
        temperature=temperature,
        response_mime_type=response_mime_type,
        response_schema=response_schema,
        system_instruction=system_instruction,
        max_output_tokens=max_output_tokens,
    )


def generate(prompt: str, model: Optional[str] = None, temperature: float = 0.0,
             response_mime_type: str = "application/json", response_schema=None,
             system_instruction: Optional[str] = None, max_output_tokens: Optional[int] = None) -> str:
    cfg = _config(temperature, response_mime_type, response_schema, system_instruction, max_output_tokens)
    return _client.models.generate_content(contents=prompt, config=cfg).text


def generate_with_parts(parts: list, model: Optional[str] = None, temperature: float = 0.0,
                        response_mime_type: str = "application/json", response_schema=None,
                        system_instruction: Optional[str] = None) -> str:
    cfg = _config(temperature, response_mime_type, response_schema, system_instruction)
    return _client.models.generate_content(contents=parts, config=cfg).text


def generate_with_pdf(pdf_path, prompt: str, model: Optional[str] = None, temperature: float = 0.0,
                      response_mime_type: str = "application/json",
                      system_instruction: Optional[str] = None, response_schema=None, client=None) -> str:
    """Send one or more PDFs plus a prompt in a single request, so the model can cross-reference them."""
    paths = pdf_path if isinstance(pdf_path, list) else [pdf_path]
    parts = [Part.from_bytes(Path(p).read_bytes(), "application/pdf") for p in paths]
    parts.append(Part.from_text(prompt))
    cfg = _config(temperature, response_mime_type, response_schema, system_instruction)
    return (client or _client).models.generate_content(contents=parts, config=cfg).text


def generate_grounded(prompt: str, model: Optional[str] = None, temperature: float = 0.3,
                      system_instruction: Optional[str] = None) -> str:
    """Answer from the regulation corpus (the deployment has no open-web access)."""
    from src.rag.regulation_store import retrieve_context

    context = retrieve_context(prompt)
    full = f"Reference material:\n{context}\n\n{prompt}" if context else prompt
    return generate(full, response_mime_type="text/plain", system_instruction=system_instruction)
