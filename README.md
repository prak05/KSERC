# KSERC Truing-Up Engine

You are reviewing a truing-up petition for the **Kerala State Electricity Regulatory Commission**. A licensee (Technopark, Infopark, CSEZA or KDHP) has filed its actual costs for a financial year; the Commission must check every head of expenditure against the Tariff Regulations and the MYT order, disallow what the rules don't permit, and issue a reasoned order.

This engine does that work end to end. It reads the petition PDFs, extracts the ARR tables, audits each component with deterministic regulatory formulas (the model never does the arithmetic), pauses for an officer to rule on one-time R&M items, and drafts a 30-page order in the Commission's format — exportable as PDF or Word.

It runs entirely on your machine with no keys, or on AWS with one command.

---

### 1. VISUAL SYSTEM & DESIGN SPECS

*   **Palette (monochrome foundation + one accent):**
    *   Canvas `#08090A`, raised surfaces `#0F1011` / `#141516`.
    *   Hairline structure: 1px borders `#1F2023`, strong `#2A2B2F`.
    *   Text `#F7F8F8`, secondary `#8A8F98`, tertiary `#5C6068`.
    *   The single accent — indigo `#5E6AD2` — marks only the active route, focus, the primary action and progress (under 5% of the screen).
    *   Data states use muted tones and appear only on data: approved `#4CB782`, review `#D9A441`, disallowed `#D25E5E`.
*   **Typography:** heavy display headings with tight tracking; every amount, clause number and log line in a monospace face with tabular figures; 10–11px uppercase mono micro-labels. All fonts are self-hosted — the UI makes no request to any font CDN.
*   **Layout attitude:** a Linear-style workspace — fixed sidebar, ⌘K command palette, dense aligned tables — opened by an asymmetric editorial hero where a massive title sits against microscopic case metadata and deliberate negative space.

---

### 2. SYSTEM ARCHITECTURE

```
            ┌──────────────── React UI (Vite) ─────────────────┐
            │ Upload · Results · Order drafter · Analyst ·     │
            │ History · Calculator · Benchmarks · Regulations  │
            └───────────────────────┬──────────────────────────┘
                                    │ /api
                       ┌────────────▼─────────────┐
                       │  FastAPI  (app.py)       │
                       │  LangGraph pipeline:     │
                       │  extract → deep tables → │
                       │  MYT norms → anomalies → │
                       │  audit → R&M review →    │
                       │  draft → clarify → verify│
                       └────────────┬─────────────┘
                                    │ src/cloud  (CLOUD = local | aws)
      ┌───────────────┬─────────────┼───────────────┬───────────────────┐
      │ Model         │ Tables      │ Document store│ Files             │
 local│ Ollama / LM   │ PyMuPDF     │ SQLite        │ documents/        │
      │ Studio /      │             │               │                   │
      │ offline       │             │               │                   │
 aws  │ Claude on     │ Textract    │ DynamoDB      │ S3                │
      │ Bedrock       │             │ (+S3 spill)   │                   │
      └───────────────┴─────────────┴───────────────┴───────────────────┘
```

*   **Frame 1 — Intake:** petition PDFs plus the year's rates (inflation, SBI EBLR, deposit rates, BEE fee). Files are validated, size-capped and stored under random IDs.
*   **Frame 2 — Extraction:** page images go to the model for the ARR table; Textract (AWS) or PyMuPDF (local) supplies the structured tables as a cross-check; results are cached by PDF hash.
*   **Frame 3 — Audit engine:** `src/tools/normative_math.py`, the depreciation engine (90% cap, grant-funded assets), the interest & finance engine (normative loan, IWC, security deposit interest) and the PPC cross-check (APPC × energy input) compute every approved figure. The model only classifies and explains.
*   **Frame 4 — Regulation corpus:** 29 reference PDFs (tariff regulations and amendments, MYT orders, past truing-up orders) are converted to text once; questions retrieve the most relevant passages with BM25 instead of shipping whole PDFs.
*   **Frame 5 — Order:** JSON order model → Jinja templates → HTML → WeasyPrint PDF, or DOCX for editing in Word.

**AWS deployment** (`infra/aws`, 28 resources): VPC with two public subnets → Application Load Balancer (900 s idle timeout, optional HTTPS) → ECS Fargate (2 vCPU / 4 GB) → Bedrock, Textract, DynamoDB (on-demand, PITR), S3 (private, versioned, encrypted). The task's IAM role is the only credential; it is scoped to one bucket, one table and one Bedrock region.

---

### 3. BEHAVIOUR & MOTION

*   **Choreographed entry:** structural borders fade in (500 ms) → the hero title glides up 16 px while fading in (150 ms delay, `cubic-bezier(0.16, 1, 0.3, 1)`) → working panels wipe in (300 ms delay).
*   **Easing:** macro moves — opening panels, drawers, view changes — 500 ms `cubic-bezier(0.16,1,0.3,1)`; micro-interactions 200 ms `cubic-bezier(0.25,1,0.5,1)`. Views cross-fade; nothing blinks out. `prefers-reduced-motion` is respected.
*   **Primary action:** an off-white block that inverts on hover with a vertical text slide.
*   **Audit terminal:** while a petition is analysed, pipeline stages stream in as monospace log lines with stage tags, an elapsed timer and a thin indigo progress line.
*   **Human in the loop:** when claimed R&M exceeds the MYT norm the pipeline pauses; the officer selects one-time items under Regulation 80(3) and the run resumes. Any component can be overridden later with a recorded justification.
*   **Merged from earlier versions:** Analyst Q&A grounded in the corpus with cited sources (v3/v6), case history (v4), Word export (v3), quick calculator and historical benchmarks (v2), live audit terminal (v6).

---

### 4. RUN & OUTPUT REQUIREMENTS

**Local — no cloud, no keys**

```bash
make setup      # Python venv, UI packages, .env from .env.example
make run        # UI + API on http://localhost:8000
make up         # or Docker: app + Ollama on http://localhost:8080
make test       # 99 tests, model-free
```

`LLM_PROVIDER` chooses the model: `local` (Ollama, LM Studio, llama.cpp — default `qwen2.5:14b`), `bedrock`, or `offline` (rules engine only). A sample petition is in `documents/sample-petitions/`.

**AWS — one command**

```bash
make plan-aws REGION=ap-south-1     # review
make deploy-aws REGION=ap-south-1   # provision → build & push → sync corpus → roll out
make destroy-aws REGION=ap-south-1
```

Before the first deploy, enable model access for Claude in Amazon Bedrock for the region you deploy to (or set `bedrock_region`). Restrict `allowed_cidrs` to the Commission's network and set `certificate_arn` for HTTPS — see [`docs/deployment.md`](docs/deployment.md).

**Configuration** — `.env` (see `.env.example`):

| Variable | Default | |
|---|---|---|
| `CLOUD` | `local` | `aws` switches storage to DynamoDB + S3 and tables to Textract |
| `LLM_PROVIDER` | `local` (`bedrock` on AWS) | `local` · `bedrock` · `offline` |
| `LLM_MODEL` | `anthropic.claude-opus-5-5` | Bedrock model; `LLM_FALLBACK_MODEL` handles refusals |
| `LLM_EFFORT` | `high` | model effort for extraction and drafting |
| `AWS_REGION` / `BEDROCK_REGION` | `ap-south-1` | app region / model region |

**Outputs** — generated orders land in `output_orders/` (samples for Infopark, KDHP and Technopark FY 2024-25 are included); downloads: `GET /api/download/{id}` (PDF), `GET /api/export-docx/{id}` (Word). Full route list: [`docs/api_reference.md`](docs/api_reference.md).

**Known gaps** — `KSERC_Tariff_Regulations_2021.pdf` is not in the corpus (add it under Regulations); two legacy tests are marked expected-fail because they predate the March 2026 PPC and ARR-scanner rules. Version history: [`VERSIONS.md`](VERSIONS.md).
