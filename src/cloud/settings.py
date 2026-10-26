"""
Runtime settings for the cloud layer.

One switch decides where everything runs:

    CLOUD=local   SQLite + local folders + a local model server (default)
    CLOUD=aws     DynamoDB + S3 + Textract + Amazon Bedrock

On AWS no keys are configured anywhere: every service is reached through the
IAM role attached to the ECS task.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]

CLOUD = os.getenv("CLOUD", "local").strip().lower()
IS_AWS = CLOUD == "aws"

# ── AWS ──────────────────────────────────────────────────────────────────────
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", AWS_REGION)  # model access can live in another region
DOCS_BUCKET = os.getenv("DOCS_BUCKET", "")
DOCS_PREFIX = os.getenv("DOCS_PREFIX", "documents/")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "kserc-truing-up")

# ── Language model ───────────────────────────────────────────────────────────
#   bedrock  Claude on Amazon Bedrock (AWS default)
#   local    any OpenAI-compatible server on this machine, e.g. Ollama (local default)
#   offline  no model; LLM-assisted steps return empty JSON and the
#            deterministic rules engine carries the analysis
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "bedrock" if IS_AWS else "local").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "anthropic.claude-opus-5-5")
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "anthropic.claude-opus-4-8")
LLM_EFFORT = os.getenv("LLM_EFFORT", "high")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "64000"))
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "qwen2.5:14b")

# ── Local storage ────────────────────────────────────────────────────────────
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data"))).resolve()
LOCAL_DB_PATH = Path(os.getenv("LOCAL_DB_PATH", str(DATA_DIR / "store.sqlite3"))).resolve()
DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", str(BASE_DIR / "documents"))).resolve()
