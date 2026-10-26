# Product Requirements Document (PRD)

**Project:** KSERC AI-Based Truing-Up Analytical Tool  
**Work Order:** KSERC/CSO/03-05 · Dated 28 January 2026  
**Institution:** Rajadhani Institute of Engineering and Technology (RIET), Kerala  
**Client:** Kerala State Electricity Regulatory Commission (KSERC)  
**Version:** 1.0 — Prototype / Funding Pitch  
**Author:** Prakhar Sharma, B.Tech, RIET Kerala  
**Date:** 02 March 2026

---

## 1. Executive Summary

KSERC requires an AI-powered regulatory tool to automate the **Truing-Up process** for small distribution licensees. Currently, KSERC staff manually compare approved tariff estimates against actual year-end financials — a time-intensive, error-prone process requiring specialist regulatory knowledge.

This document defines all functional and non-functional requirements for an intelligent web application that ingests financial documents, applies regulatory validation logic, flags deviations, and generates regulatory-grade Truing-Up reports — reducing manpower burden while retaining final human approval authority.

---

## 2. Problem Statement

At the end of each financial year, KSERC must conduct a **Truing-Up** exercise for each licensed distribution company:

1. The licensee submitted an Annual Revenue Requirement (ARR) petition containing projected costs and revenues.
2. KSERC approved a tariff based on those projections.
3. Actual year-end data is now available and must be compared against the approved figures.
4. KSERC must compute the Revenue Gap or Surplus and determine the adjustment to carry forward.

This process for the 4 small licensees (KDHP, Technopark, Infoparks, CSEZA) involves:

- Cross-referencing 20–40 cost heads per licensee
- Applying precedent-based prudence checks (referencing historical commission orders)
- Detecting cost inflation, revenue suppression, or accounting irregularities
- Generating a structured regulatory order document

Currently, this entire workflow is performed manually by KSERC consultants, taking weeks per licensee. The AI tool replaces this with an automated pipeline requiring only final human sign-off.

---

## 3. Target Licensees (Scope)

| # | Licensee | Short Name |
|---|----------|------------|
| 1 | Kanan Devan Hills Plantations Company Pvt Ltd | KDHP |
| 2 | Electronics Technology Parks – Kerala, Technopark | Technopark |
| 3 | Infoparks Kerala | Infoparks |
| 4 | Cochin Special Economic Zone Authority | CSEZA |

---

## 4. Users

| User Role | Description | Interaction Level |
|-----------|-------------|-------------------|
| KSERC Officer (Primary) | Uploads data, reviews AI output, approves report | High — GUI only, no backend visibility |
| KSERC Consultant (Tech/Fin) | Reviews detailed analysis, flags corrections | Medium — views schematics and logic traces |
| Commission Secretary | Final approval of generated Truing-Up order | Low — reads summary and approves |
| System Administrator | Manages data and API configurations | Backend access |

**UX Mandate:** The interface must be designed for users aged 45–65 with formal regulatory backgrounds, not technology backgrounds. No jargon, no complex navigation, large readable text, minimal steps per workflow.

---

## 5. Core Concepts: Truing-Up Formula

### 5.1 Annual Revenue Requirement (ARR)

```
ARR = Fixed Costs + Variable Costs + Return on Equity
    = (Depreciation + O&M + Interest on Loans + Admin Expenses)
    + (Power Purchase Cost + Transmission Charges)
    + (Equity × RoE Rate)
```

### 5.2 Revenue Gap / Surplus

```
Revenue Gap (or Surplus) = ARR_actual − Revenue_actual

If Revenue Gap > 0 → Licensee under-recovered → Gap to be carried forward as asset
If Revenue Gap < 0 → Licensee over-recovered → Surplus to be adjusted in next tariff
```

### 5.3 Truing-Up Adjustment

```
Truing-Up Amount = ARR_approved − ARR_actual (difference in each line item)

For each cost head i:
  Δᵢ = Actual_i − Approved_i

If Δᵢ > 0 (cost overrun):
  Apply Prudence Check → Allow only if justified
  Disallow portion = Δᵢ × Disallowance_Rate (0.0 to 1.0)

Net Allowable Expense = Approved_i + min(Δᵢ, Normative_Cap_i) − Disallowed_i
```

### 5.4 Prudence Check Rules (based on KSERC historical orders)

| Cost Head | Rule | Max Allowable Escalation |
|-----------|------|--------------------------|
| Power Purchase Cost | Allowed only if backed by KSEB billing or PPA | 100% with proof |
| O&M Expenses | Normative escalation cap per KSERC regulation | Prior year × 1.05 |
| Employee Costs | As per pay commission / actual salary slips | Actuals with audit |
| Depreciation | Straight-line per KSERC asset schedule | Per approved asset register |
| Return on Equity | Fixed % on approved equity base | As per KSERC tariff order |
| Admin & General Expenses | Benchmarked against similar licensees | ±15% variance allowed |

---

## 6. Functional Requirements

### FR-01: Document Upload and Parsing

- **FR-01.1** User uploads Annual Accounts (PDF or Excel) for a licensee
- **FR-01.2** System extracts structured financial data: cost heads, revenue figures, energy units
- **FR-01.3** System maps extracted fields to KSERC standard cost taxonomy
- **FR-01.4** System shows the extracted data to user for confirmation before analysis
- **FR-01.5** Supports PDF (scanned and digital), Excel (.xlsx), and CSV formats

### FR-02: Data Validation and Anomaly Detection

- **FR-02.1** Compare each actual cost head against KSERC-approved amount
- **FR-02.2** Flag deviations exceeding configurable threshold (default: ±10%)
- **FR-02.3** Detect energy balance inconsistencies (energy input ≠ revenue + losses)
- **FR-02.4** Flag year-on-year spikes (>20% increase in any cost head vs prior year)
- **FR-02.5** Check for revenue suppression: units sold × average tariff vs reported revenue
- **FR-02.6** All flags show the exact formula used and the values that triggered the flag

### FR-03: AI Regulatory Analysis (RAG + LLM)

- **FR-03.1** System maintains a knowledge base of KSERC past truing-up orders (2015–2024)
- **FR-03.2** For each deviation, AI generates a recommendation referencing similar past cases
- **FR-03.3** AI assigns an Allow / Partial Allow / Disallow verdict per cost head
- **FR-03.4** All AI verdicts show reasoning chain (which past order was referenced, what rule applied)
- **FR-03.5** User can override any AI verdict with a manual note
- **FR-03.6** Override history is logged for audit trail

### FR-04: Revenue Gap Computation

- **FR-04.1** Auto-compute final ARR_actual after all prudence checks applied
- **FR-04.2** Compute Revenue Gap = ARR_actual − Revenue_actual
- **FR-04.3** Display waterfall breakdown: each cost head's contribution to gap
- **FR-04.4** Show aggregate gap vs historical average gap for that licensee

### FR-05: Dashboard and Visualizations

- **FR-05.1** Per-licensee summary card: ARR Approved, ARR Actual, Gap/Surplus, Status
- **FR-05.2** Bar chart: Approved vs Actual per cost head
- **FR-05.3** Trend line: Revenue gap across 5 years
- **FR-05.4** Deviation heatmap: color-coded table of all cost heads
- **FR-05.5** Prudence check scorecard: % of costs approved, partially approved, disallowed

### FR-06: Report Generation

- **FR-06.1** Generate formal Truing-Up order document in KSERC format
- **FR-06.2** Report includes: licensee details, approved vs actual table, deviation analysis, prudence checks, final ARR, revenue gap, commission recommendations
- **FR-06.3** Report exported as PDF and Word (.docx)
- **FR-06.4** Report generation uses free-tier LLM API for narrative paragraph generation
- **FR-06.5** All numerical values in report are computed deterministically (not LLM-generated)
- **FR-06.6** Human review step required before report is marked "Final"

### FR-07: Historical Data Module

- **FR-07.1** Store and display historical truing-up data for all 4 licensees (FY 2018–2024)
- **FR-07.2** Searchable record of all past commission orders with key decisions
- **FR-07.3** Benchmark comparison: current year vs 5-year average per cost head
- **FR-07.4** Extreme case library: largest gap, largest surplus, largest disallowance on record

### FR-08: Audit Trail

- **FR-08.1** Every computation step logged with timestamp and input values
- **FR-08.2** Every AI verdict logged with model, prompt, and response
- **FR-08.3** Every user override logged with user ID, reason, and timestamp
- **FR-08.4** Full audit trail exportable as PDF for commission records

---

## 7. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | Page load < 3 seconds; AI analysis < 30 seconds per licensee |
| Availability | 99% uptime during KSERC working hours (9am–5pm IST) |
| Security | No licensee data stored in LLM provider servers; all data on own Supabase instance |
| Accessibility | Minimum font size 15px; high contrast; no color-only indicators |
| Offline Mode | Core computation works without LLM (LLM only for narrative generation) |
| Browser Support | Chrome 100+, Firefox 100+, Edge 100+ |
| Deployment | Vercel (frontend) + Supabase (database + auth) |
| Cost | Zero ongoing cost using free-tier APIs only |

---

## 8. Data Model (High Level)

### Licensees Table
`id, name, short_name, license_number, service_area, created_at`

### Truing Up Cases Table
`id, licensee_id, financial_year, status (draft/review/final), created_at, approved_by`

### Cost Heads Table
`id, case_id, head_name, category, approved_amount, actual_amount, deviation_pct, ai_verdict, ai_reason, user_override, override_reason`

### Revenue Table
`id, case_id, units_sold, avg_tariff, reported_revenue, computed_revenue, gap_amount`

### AI Analysis Log Table
`id, case_id, cost_head_id, model_used, prompt_hash, verdict, reasoning, timestamp`

### Historical Orders Table
`id, licensee_id, year, order_number, key_ruling, disallowance_amount, gap_amount, document_url`

---

## 9. Out of Scope (v1 Prototype)

- Multi-user concurrent editing
- Integration with KSERC's internal ERP
- Support for KSEB (main distribution licensee — handled separately)
- Mobile application
- Automated data fetching from licensee systems
- Real-time tariff simulation

---

## 10. Success Criteria

The prototype will be considered successful if it:

1. Correctly parses and extracts data from at least 2 uploaded financial documents
2. Generates a complete Revenue Gap computation with zero manual data entry
3. Produces a regulatory-style report that KSERC officers recognize as structurally valid
4. Demonstrates AI reasoning with traceable references to regulatory precedents
5. Runs entirely on free-tier APIs with no paid subscriptions

---

## 11. API Requirements (Zero Cost Stack)

| Purpose | Primary API | Fallback | Get Key From |
|---------|-------------|----------|--------------|
| Document Analysis (RAG) | Groq — `llama-3.3-70b-versatile` | OpenRouter — `deepseek/deepseek-r1:free` | console.groq.com |
| Report Generation (Narrative) | Google Gemini Flash 2.0 | Groq | aistudio.google.com |
| OCR (Scanned PDFs) | Google Gemini Vision | Mistral Pixtral | aistudio.google.com |
| Embeddings (RAG vector search) | Hugging Face Inference API | Local `all-MiniLM-L6-v2` | huggingface.co |
| Database | Supabase Free Tier | Firebase Firestore | supabase.com |
| Deployment | Vercel Hobby (free) | — | vercel.com |

---

*End of PRD v1.0*
