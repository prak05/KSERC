# KSERC AI Truing-Up Tool — Context / Memory File & Prompt Library
> **Project:** AI-Based Analytical Tool for Truing Up of Accounts | Work Order No. KSERC/CSO/03-05  
> **Feed this file to the AI coding assistant at the start of every new session.**
> **Version:** 1.0 | Date: 2026

---

# PART 1: CONTEXT / MEMORY FILE

## Project Identity
This is an AI-based regulatory tool built for the **Kerala State Electricity Regulatory Commission (KSERC)** under Work Order No. KSERC/CSO/03-05. The tool automates the **Truing-Up** process — comparing what electricity distribution licensees were approved to earn vs. what they actually earned, and computing whether they owe money or are owed money (Revenue Gap / Surplus).

## The 4 Distribution Licensees
1. **KDHPCL** — Kanan Devan Hills Plantations Company Pvt Ltd (plantation area)
2. **TECHNOPARK** — Electronics Technology Parks, Kerala (IT park)
3. **INFOPARK** — Infoparks Kerala (IT park)
4. **CSEZA** — Cochin Special Economic Zone Authority (SEZ)

## Core Financial Concept
```
Revenue Gap / Surplus = Approved ARR − Actual Revenue

Positive result = Revenue GAP (licensee is owed money)
Negative result = Revenue SURPLUS (licensee collected more than approved)
```

## Historical Benchmarks (CRITICAL — Use for Sanity Checks)
- Max surplus ever approved: **₹280.42 Lakh** (Technopark 2020-21)
- Max gap ever approved: **₹-64.72 Lakh** (Infopark 2024-25)
- Largest rejection: **₹15.04 Lakh** disallowed from Infopark's ₹79.76L claim (2024-25)
- Notable reversal: CSEZA claimed −₹3.42L but KSERC approved +₹87.85L (2023-24)
- Notable overshoot: KDHPCL asked ₹13.61L, got ₹58.72L (2021-22)
- **ANY computed value outside these ranges must trigger a warning.**

## Regulatory Logic (Hardcoded Rules — Never Change Without Human Approval)
1. **Section 3(1) Electricity Duty → ALWAYS REJECT (₹0 approved)**
2. **CSR Expenses → ALWAYS REJECT (₹0 approved)**  
3. **RPO Liability Provisions → REJECT; only actual REC payments allowed**
4. **O&M Costs (Employee + R&M + A&G) → Cap at: `Previous Approved × (1 + AICPI Rate)`**
5. **Distribution Loss < Target → Licensee retains 2/3 of efficiency savings**
6. **Interest on Surplus → Must use SBI Retail Term Deposit Rate**
7. **One-time expenditures (documented) → May be approved over and above norm**
8. **Capital items wrongly claimed as R&M → Reclassify; compute depreciation instead**

## Technology Choices (Do Not Override)
- **Backend:** Python 3.11 + FastAPI
- **Frontend:** React 18 + TypeScript + Tailwind CSS + shadcn/ui
- **AI / LLM:** Google Gemini 1.5 Flash (free tier)
- **RAG:** LlamaIndex + ChromaDB (local vector DB)
- **Database:** PostgreSQL
- **Report Generation:** reportlab (PDF) + python-docx (Word)
- **Financial unit:** Always ₹ Lakh (4 decimal places)

## Code Style Rules (Enforce Every Session)
- **Every Python line must have an inline comment** (per student developer requirement)
- Never use placeholder data — all output must come from real uploaded documents or seeded historical data
- Financial values always in ₹ Lakh
- All AI reasoning must cite: regulation clause + past order reference
- TypeScript strict mode, no `any` types
- Errors displayed as toast notifications (never `alert()`)
- No `localStorage` for financial data

## Current Build Status (Update Each Session)
```
✅ Database schema defined
✅ API contract defined
✅ Design system defined
⚙️  Backend: FastAPI skeleton — IN PROGRESS
⚙️  Frontend: React setup — IN PROGRESS
❌ AI reasoning engine — NOT STARTED
❌ PDF extraction service — NOT STARTED
❌ Report generation — NOT STARTED
❌ Historical data seeded — NOT STARTED
```

## Lessons Learned (Update as You Build)
- [ ] When extracting tables from KSERC PDFs, use `pdfplumber` (handles complex regulatory tables better than PyPDF2)
- [ ] Gemini API free tier has rate limits — implement retry with exponential backoff
- [ ] All monetary amounts from PDFs will be formatted as "12,34,567.89" (Indian number system) — parse accordingly
- [ ] KSERC orders use "Lakh" not "Lac" — standardize in all outputs
- [ ] The word "surplus" in KSERC means the licensee collected MORE than approved (opposite of common usage)

---

# PART 2: PROMPT LIBRARY

## Category A: Backend — Calculation Prompts

### A1. Revenue Gap Calculator
```
Build a Python function called `calculate_revenue_gap` in `backend/app/services/calculator.py`.

Context: This is for KSERC (Kerala State Electricity Regulatory Commission) truing-up analysis.

Requirements:
1. Take `approved_arr` (float, in ₹ Lakh) and `actual_revenue` (float, in ₹ Lakh) as parameters
2. Return the gap/surplus as a float (positive = gap, negative = surplus)
3. Every line must have an inline comment explaining what it does
4. Include a full docstring with formula, example, and parameter descriptions
5. Add input validation (raise ValueError if either input is negative or None)
6. Return a dict with: gap_amount, outcome_type ('gap' or 'surplus'), and magnitude_assessment
   (based on historical range: ₹280.42L max surplus, ₹64.72L max gap)

Tech: Python 3.11, no external libraries needed
```

### A2. AT&C Loss Calculator
```
Build a Python function called `calculate_atc_loss` in `backend/app/services/calculator.py`.

Formula: AT&C Loss (%) = ((Energy Input MU - Energy Realized MU) / Energy Input MU) × 100

Requirements:
1. Parameters: `energy_input_mu` (float), `energy_sold_mu` (float), `approved_target_pct` (float)
2. Returns: dict with actual_loss_pct, target_pct, variance_pct, efficiency_gain_achieved (bool)
3. If actual_loss < target: calculate efficiency gain = (target - actual) × energy_input_mu / 100
   Per KSERC logic: licensee retains 2/3 of the savings from power purchase cost
4. Every line with inline comment
5. Include a worked example for Infopark 2024-25: target 4.23%, actual 2.86%
```

### A3. O&M Normative Cap Check
```
Build a Python function called `check_om_normative_cap` in `backend/app/services/rule_engine.py`.

Logic from KSERC Tariff Regulations 2021, Regulation 12(3):
- O&M costs (Employee + R&M + A&G) are capped at: previous_approved × (1 + escalation_rate)
- Escalation rate = AICPI (All India Consumer Price Index change for the year)
- If actual > cap: disallow the excess

Requirements:
1. Parameters: previous_approved_lakhs, actual_claimed_lakhs, aicpi_rate (float, e.g. 0.042 for 4.2%)
2. Returns: dict with normative_cap, claimed, approved, disallowed, status, regulatory_reference
3. status can be: 'approved', 'approved_with_reduction', 'check_required'
4. Every line with inline comment
5. One-time expenditure flag: add optional parameter `one_time_expense_lakhs` that can be approved over and above norm
```

### A4. Perennial Rejection Checker
```
Build a Python function called `check_perennial_rejections` in `backend/app/services/rule_engine.py`.

These items are ALWAYS rejected by KSERC (₹0 approved):
1. Section 3(1) Electricity Duty
2. CSR (Corporate Social Responsibility) expenses
3. RPO Liability Provisions (only actual REC payments allowed)

Requirements:
1. Parameter: dict with line item names and claimed amounts
2. Returns: list of dicts with item_name, claimed_amount, approved_amount (always 0), rejection_reason, regulatory_reference
3. Pattern matching should be flexible (e.g., "section 3(1)", "Section 3(1) duty", "electricity duty u/s 3(1)" should all match)
4. Every line with inline comment
5. Log each rejection to console with: f"PERENNIAL REJECTION: {item_name} — ₹{claimed:.2f}L disallowed"
```

---

## Category B: Backend — AI & RAG Prompts

### B1. RAG Knowledge Base Setup
```
Build a Python script `backend/app/services/rag_engine.py` that:

1. Ingests all PDF files from `backend/app/knowledge_base/` into ChromaDB
2. Uses sentence-transformers (`all-MiniLM-L6-v2` model) for embeddings — free, local
3. Uses LlamaIndex as the orchestration layer
4. Creates a retriever that accepts a query string and returns top 5 relevant chunks

Context: The knowledge base will contain:
- KSERC Tariff Regulations 2021 & 2014
- Past truing-up orders for all 4 licensees
- Relevant KSERC circulars

Requirements:
- Every line with inline comment
- Include a `query_knowledge_base(query: str) -> list[dict]` function
  that returns: [{text, source_document, relevance_score}]
- Handle case where knowledge_base/ is empty gracefully (return empty list with warning)
- Cache embeddings to disk so they don't regenerate on every restart
```

### B2. Gemini Reasoning Integration
```
Build a Python function `generate_reasoning` in `backend/app/services/rag_engine.py`.

This function makes the AI reason about a specific line item like a KSERC analyst.

Parameters:
- item_name: str (e.g., "Employee Cost")
- claimed_amount: float (₹ Lakh)
- normative_cap: float (₹ Lakh)
- retrieved_regulations: list[str] (from RAG retriever)
- historical_precedents: list[str] (from historical_orders table)

Process:
1. Build a prompt combining retrieved regulations + historical precedents
2. Call Gemini 1.5 Flash API (use GEMINI_API_KEY from .env)
3. Instruct the model to reason step-by-step and conclude with approved amount + reason
4. Parse response and return structured dict

Requirements:
- Model: gemini-1.5-flash (free tier)
- Temperature: 0.1 (low temperature = consistent, precise output — this is financial analysis)
- Every line with inline comment
- Include retry logic: max 3 retries with 2-second delays (handle rate limit errors)
- If API fails, fall back to rule-based output with a note that AI reasoning was unavailable
```

---

## Category C: Frontend Prompts

### C1. Analysis Results Table Component
```
Build a React component `LineItemValidationTable` in `frontend/src/components/analysis/`.

This is the core review screen where KSERC staff see each line item's validation.

Design requirements (from Design System):
- Use Tailwind CSS only — no inline styles
- Table header: bg-[#1A3557] text-white
- Surplus values: text-[#1A7F4B] with bg-[#DCFCE7] badge
- Gap/rejected: text-[#C0392B] with bg-[#FEE2E2] badge
- Flagged: text-[#D97706] with bg-[#FEF3C7] badge
- Font for numbers: font-mono

Columns: Item Name | Claimed (₹L) | AI Recommended (₹L) | Status | Action

Status badges:
- ✅ "Approved" (green)
- ⚠️ "Flagged" (amber) 
- ❌ "Rejected" (red)

Action buttons:
- "View Reasoning" → opens a side panel with full AI reasoning chain
- "Override" → opens an inline edit field for staff to enter their own amount

Props interface (TypeScript):
interface LineItem {
  id: number;
  item_name: string;
  claimed_amount: number;
  ai_recommended: number;
  staff_approved: number | null;
  validation_status: 'approved' | 'flagged' | 'rejected' | 'pending_review';
  reasoning_summary: string;
  regulatory_reference: string;
}
```

### C2. Revenue Gap Summary Card
```
Build a React component `RevenueSummaryCard` in `frontend/src/components/dashboard/`.

Shows the single most important number: the Revenue Gap or Surplus.

Display:
- Large number (₹ Lakh, 2 decimal places) — monospace font, 28px
- Color: RED if gap (positive), GREEN if surplus (negative)
- Label below: "Revenue Gap" or "Revenue Surplus" accordingly
- Sub-label: "FY 2024-25 | Infoparks Kerala"
- Trend arrow: compare to previous year's value (if available)

Props:
interface RevenueSummaryCardProps {
  licensee: string;
  financial_year: string;
  computed_amount: number;  // positive = gap, negative = surplus
  previous_year_amount?: number;
}

Design: Card with white background, 1px border #DEE2E8, border-radius 8px, shadow-sm
```

### C3. Analysis Progress Screen  
```
Build a React component `AnalysisProgress` in `frontend/src/components/analysis/`.

This screen shows real-time progress of the AI analysis using polling.

Behavior:
1. Poll GET /sessions/{id}/status every 3 seconds
2. Show a progress bar (use HTML progress or a Tailwind bar)
3. Show completed steps with ✅ checkmark and pending steps with ⏳ spinner
4. Show a live "AI Reasoning Log" text area that appends new lines as analysis progresses
5. When status = 'review', automatically redirect to the Results page

Design:
- No animations other than the progress bar and spinner
- Simple, calm UI — KSERC staff should not feel overwhelmed
- "Please wait. Do not close this window." message at bottom

Use Axios for API calls. Use useEffect + setInterval for polling. Clean up interval on unmount.
```

---

## Category D: Report Generation Prompts

### D1. PDF Truing-Up Order Generator
```
Build a Python function `generate_truing_up_order_pdf` in `backend/app/services/report_gen.py`.

This generates an official-looking KSERC truing-up order PDF.

The PDF must match KSERC's order format:
- Header: KERALA STATE ELECTRICITY REGULATORY COMMISSION letterhead
- Title: "ORDER" centered, bold
- Sections: Background, Summary of Petition, Commission's Analysis, Decision
- Table 1: Comparison of Approved ARR vs Actuals
- Table 2: Line-Item Validation (Approved / Disallowed amounts)
- Table 3: Revenue Gap / Surplus Computation
- Footer: "By Order of the Commission" + Secretary signature line

Use: reportlab library
All currency: ₹ Lakh, formatted as "₹ XX.XX Lakh"
Font: Helvetica (built into reportlab, no external font needed)
Every line with inline comment
```

---

## Category E: Anomaly Detection Prompts

### E1. Statistical Anomaly Detector
```
Build a Python function `detect_anomalies` in `backend/app/services/rule_engine.py`.

This detects unusual patterns in the licensee's financial data.

Checks to implement:
1. Cost spike: if any cost item grew > 30% YoY without explanation → flag
2. Revenue anomaly: if revenue per unit deviates > 15% from approved rate → flag
3. Distribution loss jump: if actual loss increased by > 2 percentage points vs last year → flag
4. Power purchase cost spike: if cost/unit jumped > 20% → flag

Input: dict with current year and previous year data for same licensee
Output: list of anomaly dicts with:
  - anomaly_type, description, current_value, previous_value, deviation_pct, severity ('low'/'medium'/'high')

Use scipy.stats.zscore for statistical deviation detection where applicable.
Every line with inline comment.
Include worked example in docstring using Infopark 2024-25 data.
```
