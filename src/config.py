"""
Central configuration for the KSERC Truing-Up Engine.

All AI model settings are centralized here. To upgrade/change the Gemini model,
update GEMINI_MODEL in the .env file — no code changes needed.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Gemini Model ─────────────────────────────────────────────────────────────
# Change this in .env to upgrade the AI model across the entire project.
# Supported: gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash, etc.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
