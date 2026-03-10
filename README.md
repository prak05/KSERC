# KSERC SDL Truing-Up Analysis System

An AI-powered tool that reads KSERC (Kerala State Electricity Regulatory Commission) truing-up 
petitions submitted by Special Distribution Licensees (SDLs), audits them against MYT 
(Multi-Year Tariff) approved norms, and generates a draft KSERC order in PDF format.

---

## What It Does

Given a petition PDF from an SDL (Infopark, Technopark, CSEZA/KSEZ, KDHP) for any year 
in the MYT control period (2022-27), the system:

1. **Extracts** all claimed expenses, revenues, energy data, and distribution loss from the PDF using Gemini Vision AI
2. **Audits** the petition against KSERC-approved MYT norms (escalation rates, loss targets, APPC)
3. **Applies** KSERC Regulation 73(3) for symmetric treatment of distribution loss efficiency gains and losses
4. **Drafts** a complete KSERC truing-up order in the official format as a PDF

---

## System Architecture

```
petition PDF
     │
     ▼
┌─────────────┐    Gemini Vision     ┌────────────────────┐
│  extractor  │ ─────────────────►  │ claimed_expenses   │
│    .py      │                     │ energy_input       │
│             │                     │ energy_purchased   │
│  (PDF →     │                     │ actual_loss        │
│   JSON)     │                     │ appc_rs_per_unit   │
└─────────────┘                     └────────────────────┘
                                             │
                    ┌────────────────────────┘
                    │
                    ▼
        ┌──────────────────┐
        │ myt_baselines    │  ← MYT Order norms (expense
        │    .json         │    ceilings, loss targets,
        │                  │    escalation rates)
        └──────────────────┘
                    │
                    ▼
┌─────────────┐
│  auditor    │  Computes:
│    .py      │  • approved_loss = energy_input × target% / 100
│             │  • PPC = claimed ± efficiency gain/loss (Reg 73(3))
│  (Audit +  │  • Each expense: min(claimed, MYT_norm × escalation)
│   Compute) │  • ARR = Σ approved expenses - revenue
└─────────────┘
        │
        ▼
┌─────────────┐    Gemini text      ┌──────────────────┐
│  drafter    │ ─────────────────►  │  PDF order       │
│    .py      │    generation       │  (KSERC format)  │
└─────────────┘                     └──────────────────┘
```

### Supporting Agents

| Agent | File | Role |
|---|---|---|
| MYT Norm Extractor | `myt_norm_extractor.py` | Reads MYT order PDFs with Gemini to populate `myt_baselines.json` |
| Deep Table Extractor | `deep_table_extractor.py` | Fallback extraction using structured table parsing |
| Chief Auditor | `chief_auditor.py` | Orchestrates multi-component audit |
| Analyzer | `analyzer.py` | Post-audit analysis and variance reporting |

---

## Key Concepts

### What Is a Truing-Up Petition?
At the end of each financial year, each SDL submits a petition to KSERC claiming reimbursement 
for their actual costs. KSERC audits the claimed costs against the MYT-approved norms and 
issues a truing-up order approving or adjusting each line item.

### Distribution Loss Regulation (Reg 73(3))
If the SDL's actual distribution loss is **lower** than the MYT target (efficiency gain), 
KSERC shares the savings symmetrically:
```
efficiency_gain_units = approved_loss_units - actual_loss_units
savings_to_SDL        = efficiency_gain_units × APPC / 2
```
If actual loss is **higher** than target (inefficiency), the SDL bears the extra cost.

### Power Purchase Cost (PPC) Audit
```
APPC          = Total PPC (Rs Lakhs) ÷ Energy Purchased (Lakh units)   [from petition]
approved_loss = Energy Input (Lakh units) × Target Loss% ÷ 100          [computed]
actual_loss   = extracted from petition Energy Balance table             [from petition]
efficiency_gain = approved_loss - actual_loss                            [if positive]
approved_PPC  = claimed_PPC + (efficiency_gain × APPC)                  [KSERC formula]
```

### Where Values Come From

| Value | Source | File |
|---|---|---|
| Claimed costs | Gemini reads petition PDF | `extractor.py` |
| Energy purchased from KSEB | Gemini reads Power Purchase table | `extractor.py` |
| Total energy input to system | Gemini reads Energy Balance table | `extractor.py` |
| Actual distribution loss units | Gemini reads Energy Balance table | `extractor.py` |
| APPC (Rs/unit) | Gemini reads Power Purchase table | `extractor.py` |
| MYT expense ceilings | `myt_baselines.json` | regulatory constant |
| Target distribution loss % | `myt_baselines.json` | regulatory constant |
| Approved distribution loss units | Computed: `energy_input × target%` | `auditor.py` |
| PPC efficiency gain/loss | Computed: Reg 73(3) formula | `auditor.py` |

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ (for the React frontend)
- A Google Cloud project with Gemini API access

### 1. Clone and install dependencies
```bash
git clone <repo-url>
cd kserc_sdl_truing_up
pip install -r requirements.txt
```

### 2. Configure environment variables
Copy `.env.example` to `.env` and fill in:
```env
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_CLOUD_PROJECT=your_gcp_project_id
VERTEX_AI_REGION=us-central1
DOCUMENT_AI_PROCESSOR_ID=your_processor_id   # optional
```

### 3. Prepare MYT norms
The MYT baselines for all licensees (Technopark, Infopark, CSEZA, KDHP) are in:
```
data/myt_baselines/myt_baselines.json
```
These are pre-populated from KSERC MYT Orders (OP 09-12/2023). Do not modify unless you 
have a new MYT Order from KSERC.

### 4. Install and start the frontend (optional)
```bash
cd frontend
npm install
npm run dev
```

---

## Running the System

### Option 1: Web UI
```bash
# Start the Flask backend
python app.py

# In another terminal, start the React frontend
cd frontend && npm run dev
```
Open http://localhost:5173, upload a petition PDF, select the licensee and year, click Analyze.

### Option 2: Command-line test
Edit `run_test.py` to point to your petition PDF, then:
```bash
python run_test.py
```
Output PDF is saved to `output_orders/`.

### Option 3: Python API
```python
from src.main_graph import run_pipeline

result = run_pipeline(
    licensee_name="Infopark",
    financial_year="2024-25",
    petition_pdf_path="path/to/petition.pdf",
)
print(result["approved_arr"])
```

---

## Adding a New Petition

1. Place the petition PDF in `data/input_petitions/` (or upload via web UI)
2. Select the licensee name and financial year in the UI
3. Run the pipeline — Gemini extracts everything from the PDF automatically
4. Review the generated PDF order in `output_orders/`

---

## Adding a New Licensee

1. Obtain the licensee's KSERC MYT Order PDF
2. Add an entry to `data/myt_baselines/myt_baselines.json`:
```json
"NewLicensee": {
  "control_period": "2022-2027",
  "myt_order": "OP No.XX/2023",
  "escalation_rates": { "2024-25": 4.84, ... },
  "baselines": {
    "2024-25": {
      "power_purchase_cost": 0.0,
      "employee_cost": 0.0,
      "target_distribution_loss_pct": 5.0,
      "avg_power_purchase_cost_rs_per_kwh": 7.0,
      ...
    }
  }
}
```
3. Add a name alias in `auditor.py` → `DEFAULT_TARGET_DIST_LOSS` for fuzzy name matching

---

## Extraction Cache

Gemini API calls are expensive and slow. The system caches extraction results in `.extraction_cache/`.  
To force a fresh extraction (e.g., after fixing the Gemini prompt), delete the cache file:
```bash
Remove-Item .extraction_cache\*.json   # Windows PowerShell
rm .extraction_cache/*.json            # Linux/macOS
```

---

## Project Structure

```
kserc_sdl_truing_up/
├── app.py                      # Flask REST API backend
├── run_test.py                 # CLI test script
├── requirements.txt
├── RULES.md                    # Development rules (read this before editing code)
│
├── src/
│   ├── main_graph.py           # LangGraph pipeline orchestrator
│   ├── state.py                # Shared state schema
│   ├── gemini_client.py        # Gemini Vision API wrapper
│   ├── agents/
│   │   ├── extractor.py        # PDF → structured JSON (Gemini Vision)
│   │   ├── auditor.py          # Apply MYT norms, compute approved values
│   │   ├── drafter.py          # Generate PDF order (Gemini text + HTML)
│   │   ├── myt_norm_extractor.py   # Extract norms from MYT Order PDFs
│   │   └── deep_table_extractor.py # Fallback table extraction
│   └── rag/                    # Vector search on historical orders
│
├── data/
│   ├── myt_baselines/
│   │   └── myt_baselines.json  # MYT-approved norms per licensee per year
│   ├── input_petitions/        # Input PDFs
│   ├── historical_orders/      # Past KSERC orders for RAG context
│   └── regulations/            # KSERC Tariff Regulations
│
├── frontend/                   # React + Vite web UI
├── output_orders/              # Generated PDF orders
└── docs/                       # Additional documentation
```

---

## Regulatory References

| Document | Relevance |
|---|---|
| KSERC Tariff Regulation 2021 | Governs expense approval methodology |
| Regulation 73(3) | Symmetric distribution loss incentive/disincentive |
| OP No.09/2023 (Infopark MYT) | MYT norms for Infopark 2022-2027 |
| OP No.10/2023 (CSEZA MYT) | MYT norms for CSEZA 2022-2027 |
| OP No.11/2023 (KDHP MYT) | MYT norms for KDHP 2022-2027 |
| OP No.12/2023 (Technopark MYT) | MYT norms for Technopark 2022-2027 |

---

## Troubleshooting

**Gemini returns 503 / UNAVAILABLE**  
Gemini is overloaded (temporary). Delete the bad cache entry and retry in a few minutes.

**APPC is wrong (too low or too high)**  
Check that Gemini extracted `energy_purchased_lakh_units` (not `energy_input_lakh_units`).  
APPC = PPC ÷ energy_purchased_from_KSEB, NOT ÷ total_energy_input.

**approved_loss is wrong**  
Check that `energy_input_lakh_units` was extracted correctly from the Energy Balance table.  
The formula is `approved_loss = energy_input × target% / 100`.

**Wrong licensee norms applied**  
Check that the `licensee_name` string in the pipeline call matches a key in `myt_baselines.json`. 
The system does fuzzy matching (e.g., "infopark" matches "Infopark").
