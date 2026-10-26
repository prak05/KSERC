"""
Central configuration for the KSERC Truing-Up Engine.

The model is set with ``LLM_MODEL`` (default: Claude Opus 5.5 on Amazon Bedrock).
Change it in ``.env`` — no code changes needed. See ``src/cloud/settings.py`` for
every runtime switch.
"""

from src.cloud.settings import LLM_MODEL  # noqa: F401
