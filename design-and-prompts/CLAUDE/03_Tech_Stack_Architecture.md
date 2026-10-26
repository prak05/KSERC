# KSERC AI Truing-Up Tool — Tech Stack & Architecture Constraints
> **Project:** AI-Based Analytical Tool for Truing Up of Accounts | Work Order No. KSERC/CSO/03-05  
> **Version:** 1.0 | Date: 2026

---

## 1. Non-Negotiable Technology Decisions

This document is the source of truth for all technology choices. The AI coding assistant (Cursor, Claude Code, etc.) must follow these constraints exactly. Never deviate without explicit human approval.

---

## 2. Full Tech Stack

### Frontend
| Layer | Technology | Version | Reason |
|---|---|---|---|
| Framework | **React** | 18.x | Industry standard, rich ecosystem |
| Language | **TypeScript** | 5.x | Type safety for financial calculations |
| Styling | **Tailwind CSS** | 3.x | Rapid, consistent UI |
| UI Components | **shadcn/ui** | Latest | Professional, accessible components |
| Charts | **Recharts** | 2.x | Clean, simple financial charts |
| Icons | **Lucide React** | Latest | Consistent, lightweight |
| PDF Preview | **react-pdf** | Latest | In-browser PDF viewing of orders |
| HTTP Client | **Axios** | Latest | API calls with interceptors |
| State Mgmt | **Zustand** | Latest | Lightweight, no boilerplate |
| Forms | **React Hook Form** | Latest | Validation + performance |
| Tables | **TanStack Table** | v8 | Sortable/filterable financial tables |
| Routing | **React Router** | v6 | Client-side routing |

### Backend
| Layer | Technology | Version | Reason |
|---|---|---|---|
| Language | **Python** | 3.11+ | As specified in prompt.txt. Simple, easy to understand |
| Web Framework | **FastAPI** | 0.110+ | Fast, async, auto-generates API docs |
| Data Processing | **Pandas** | 2.x | Financial calculations & data frames |
| PDF Extraction | **pdfplumber** | Latest | Table extraction from regulatory PDFs |
| PDF Extraction (alt) | **PyMuPDF (fitz)** | Latest | High-fidelity PDF parsing |
| Excel Parsing | **openpyxl** | Latest | Read licensee Excel submissions |
| AI / LLM | **Google Gemini 1.5 Flash** | Latest | Free tier available; document analysis |
| RAG Orchestration | **LlamaIndex** | Latest | Lightweight RAG over regulatory docs |
| Vector Database | **ChromaDB** | Latest | Local, no server needed, free |
| Embeddings | **sentence-transformers** | Latest | Local embedding, free |
| Statistical Analysis | **scipy + numpy** | Latest | Z-score anomaly detection |
| Report Generation | **reportlab** | Latest | Generate PDF truing-up orders |
| Word Reports | **python-docx** | Latest | Generate editable Word drafts |
| Authentication | **FastAPI + JWT** | Latest | Secure staff login |
| ORM | **SQLAlchemy** | 2.x | Database models |

### Database
| Layer | Technology | Reason |
|---|---|---|
| Primary DB | **PostgreSQL** 15 | ACID compliance, reliable for financial data |
| Migrations | **Alembic** | Schema versioning |
| Dev/Test | **SQLite** | For local development only |

### Infrastructure (Prototype / Demo Phase)
| Component | Technology | Reason |
|---|---|---|
| Containerization | **Docker + Docker Compose** | One-command setup for demo |
| WSGI/ASGI | **Uvicorn** | FastAPI production server |
| Reverse Proxy | **Nginx** | Static files + API routing |
| File Storage | **Local filesystem** | Prototype phase; upgrade to MinIO for prod |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER (KSERC Staff)                    │
│              React + TypeScript + Tailwind CSS               │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend                           │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Auth Layer  │  │  Upload API  │  │  Analysis API     │  │
│  │  (JWT)       │  │  (PDF/Excel) │  │  (Truing-Up)      │  │
│  └─────────────┘  └──────┬───────┘  └────────┬─────────┘  │
│                           │                   │             │
│  ┌────────────────────────▼───────────────────▼──────────┐ │
│  │              CORE ANALYSIS ENGINE (Python)             │ │
│  │                                                        │ │
│  │  1. Document Ingestion (pdfplumber / PyMuPDF)          │ │
│  │  2. Data Extraction (Pandas DataFrames)                │ │
│  │  3. Rule Engine (Regulatory Logic, Symbolic Checks)    │ │
│  │  4. AI Reasoning (LlamaIndex RAG + Gemini 1.5 Flash)  │ │
│  │  5. Anomaly Detection (scipy Z-score, regression)      │ │
│  │  6. Report Generator (reportlab / python-docx)         │ │
│  └──────────────────────────────────┬─────────────────────┘ │
│                                     │                        │
│  ┌──────────────────────────────────▼─────────────────────┐ │
│  │          KNOWLEDGE BASE (ChromaDB + Embeddings)         │ │
│  │                                                         │ │
│  │  • KSERC Tariff Regulations 2003–2026                  │ │
│  │  • Past Truing-Up Orders (all 4 licensees)             │ │
│  │  • ARR Orders                                           │ │
│  │  • Regulatory Circulars                                 │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │     PostgreSQL DB        │
              │  • Users                │
              │  • Licensee Data        │
              │  • Analysis Results     │
              │  • Historical Orders    │
              │  • Audit Logs           │
              └─────────────────────────┘
```

---

## 4. AI Architecture Detail — The "Brain"

### Strategy: LiR3AG (Lightweight Rerank Reasoning for RAG)
Based on research findings, a simple RAG alone is insufficient for regulatory financial validation. We use a **Neuro-Symbolic** approach:

```
Uploaded Document (PDF)
        │
        ▼
[INGESTION LAYER]
  pdfplumber → extract text + tables
  pandas → structure into DataFrames
  Store extracted data in PostgreSQL
        │
        ▼
[RETRIEVAL LAYER]
  Query: "What is the normative O&M cap for Infopark 2024-25?"
  LlamaIndex → vector search over ChromaDB
  Returns: Relevant regulation clauses + past orders
        │
        ▼
[REASONING LAYER — PARALLEL DRAFTS]
  Draft A: O&M normative check (Employee + R&M + A&G)
  Draft B: Power purchase & BST compliance check
  Draft C: Asset capitalisation & depreciation check
  Gemini 1.5 Flash → generates reasoning for each draft
        │
        ▼
[SYMBOLIC SOLVER — THE LOGIC GUARD]
  Python rules engine (deterministic, no hallucination):
  Rule 1: if actual_OM > (normative_OM * (1 + escalation_rate)) → DISALLOW excess
  Rule 2: Section_3_1_duty → ALWAYS_REJECT
  Rule 3: CSR_expenses → ALWAYS_REJECT
  Rule 4: if actual_dist_loss < target → calculate efficiency_gain → allow 2/3 savings
  Rule 5: interest_on_surplus = cumulative_surplus * SBI_retail_deposit_rate
        │
        ▼
[OUTPUT]
  Approved amount per line item
  Reasoning text (citing regulation clause + past order)
  Confidence score
  Final Revenue Gap / Surplus
```

### Why Google Gemini 1.5 Flash (Free Tier)?
Per the prompt requirement for a **free tier API**:
- Gemini 1.5 Flash: 1 million tokens free per month (Google AI Studio)
- Sufficient for prototype demonstration
- Can be swapped for Mistral-7B local deployment in production (for data privacy)

---

## 5. Coding Standards & Constraints

### Python Backend
```python
# MANDATORY: Every function must have a docstring
def calculate_revenue_gap(approved_arr: float, actual_revenue: float) -> float:
    """
    Calculates the revenue gap as the difference between approved ARR and actual revenue.
    A positive result means a deficit (gap); negative means a surplus.
    
    Formula: Revenue Gap = Approved ARR - Actual Revenue
    Reference: KSERC Truing-Up methodology, consistent with past orders.
    
    Args:
        approved_arr: The Commission-approved Aggregate Revenue Requirement (in Lakhs)
        actual_revenue: The actual revenue realized by the licensee (in Lakhs)
    
    Returns:
        Revenue gap in Lakhs. Positive = gap, Negative = surplus.
    """
    # Subtract actual revenue from approved ARR to find the gap
    gap = approved_arr - actual_revenue
    return gap  # Returns gap; positive = licensee is owed money, negative = excess collected
```

### Mandatory Rules for AI Coding Assistant
1. **Every line of Python must have an inline comment** — as requested in prompt.txt
2. **Never use placeholder data** — all values must come from actual uploaded documents or the embedded historical data
3. **Financial values in Lakhs** — always use ₹ Lakh as the base unit (matching KSERC orders)
4. **No hallucination** — AI reasoning must cite the specific clause or historical order it references
5. **TypeScript strict mode** — `"strict": true` in `tsconfig.json`
6. **No `any` types in TypeScript** — always define proper interfaces
7. **Environment variables** — all API keys in `.env`, never hardcoded

### File Structure
```
kserc-truing-up/
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Route-level page components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── store/           # Zustand state stores
│   │   ├── types/           # TypeScript interfaces
│   │   ├── utils/           # Helper functions
│   │   └── api/             # Axios API client functions
│   ├── public/
│   └── tailwind.config.ts
│
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entry point
│   │   ├── routers/         # API route handlers
│   │   │   ├── auth.py      # Login / JWT
│   │   │   ├── upload.py    # Document upload endpoints
│   │   │   ├── analysis.py  # Analysis trigger & results
│   │   │   └── reports.py   # Report generation
│   │   ├── services/        # Business logic
│   │   │   ├── ingestion.py    # PDF/Excel extraction
│   │   │   ├── rule_engine.py  # Symbolic regulatory rules
│   │   │   ├── rag_engine.py   # LlamaIndex + Gemini RAG
│   │   │   ├── calculator.py   # Revenue gap, O&M, AT&C formulas
│   │   │   └── report_gen.py   # PDF/Word report generation
│   │   ├── models/          # SQLAlchemy DB models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   └── knowledge_base/  # KSERC regulation PDFs for RAG
│   │       ├── tariff_regs_2021.pdf
│   │       ├── tariff_regs_2014.pdf
│   │       └── past_orders/
│   │           ├── infopark_2020_21.pdf
│   │           ├── technopark_2020_21.pdf
│   │           └── ...
│   ├── requirements.txt
│   └── alembic/             # DB migrations
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 6. Environment Variables (.env.example)

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/kserc_truingup

# AI API
GEMINI_API_KEY=your_google_gemini_api_key_here   # Free tier from Google AI Studio

# JWT Security
SECRET_KEY=your_secret_key_here_min_32_chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480  # 8 hour sessions for work day

# File Storage
UPLOAD_DIR=./uploaded_documents
REPORT_OUTPUT_DIR=./generated_reports

# App Config
APP_NAME=KSERC AI Truing-Up Tool
ENVIRONMENT=development  # or production
```

---

## 7. Banned Technologies (Do Not Use)

| Technology | Reason for Ban |
|---|---|
| `localStorage` / `sessionStorage` | Financial data must not persist client-side |
| `eval()` | Security risk |
| `pickle` for financial data | Not human-readable, audit trail risk |
| Any paid LLM API without approval | Cost constraint for prototype |
| `pandas.read_csv` on untrusted uploads | Must validate file type first |
| Inline styles in React | Use Tailwind only |
| `console.log` in production builds | Use structured logging |
