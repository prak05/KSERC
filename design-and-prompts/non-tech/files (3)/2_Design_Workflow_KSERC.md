# Design & Workflow Specification

**Project:** KSERC AI Truing-Up Tool  
**Work Order:** KSERC/CSO/03-05  
**Version:** 1.0  
**Date:** 02 March 2026

---

## 1. Design Philosophy

The KSERC interface is designed for **regulatory officers aged 45–65** who are domain experts but not tech-savvy. The design borrows its visual language from KSERC's own official documents and website:

- **Primary Color:** Navy Blue `#1A3557` (institutional authority)
- **Accent Color:** Gold `#C8960C` (KSERC seal color)
- **Body Font:** Noto Sans (clean, government-appropriate)
- **Title Font:** EB Garamond (serif, formal, matches commission letterhead)
- **Monospace (numbers):** Source Code Pro (precise, unambiguous)
- **Background:** Light Grey `#F2F4F7` (easy on older eyes)
- **Status Colors:** Green `#1A7F4B` (approved), Red `#C0392B` (flagged), Amber `#D97706` (under review)

**Design Rules:**
1. No animations except subtle loading spinners
2. No color-only information (always pair with text/icon)
3. Every action is one click from where the user expects it
4. Every number shown on screen has a "Why this number?" tooltip
5. Error messages are plain English — never technical error codes

---

## 2. Application Layout

```
┌─────────────────────────────────────────────────────┐
│  [KSERC Logo]  AI Truing-Up Tool    [User] [Logout] │  ← Fixed Top Bar (60px, Navy)
├──────────┬──────────────────────────────────────────┤
│          │                                           │
│ Sidebar  │  Main Content Area                        │
│ (216px)  │                                           │
│          │                                           │
│ Dashboard│                                           │
│ Licensees│                                           │
│ Upload   │                                           │
│ Analysis │                                           │
│ Reports  │                                           │
│ History  │                                           │
│          │                                           │
│ [Version]│                                           │
└──────────┴──────────────────────────────────────────┘
```

### Sidebar Navigation Sections

**ANALYSIS**
- Dashboard (overview of all 4 licensees)
- Licensees (select a licensee to work on)

**WORKFLOW**
- Upload Data (upload annual accounts)
- Run Analysis (trigger AI analysis)
- Review & Edit (override AI verdicts)
- Generate Report (produce final document)

**RECORDS**
- Historical Data (past truing-up data)
- Commission Orders (past order reference library)
- Audit Trail (full computation log)

---

## 3. Screen-by-Screen Workflow

### Screen 1: Dashboard

**Purpose:** High-level status of all 4 licensees for the current truing-up cycle.

**Layout:**
- Page title: "Truing-Up Dashboard — FY 2024-25"
- 4 KPI cards at the top:
  - Total Licensees in Review
  - Pending Analysis
  - Reports Pending Approval
  - Completed This Cycle

- 4 Licensee Status Cards (one per licensee):
  - Licensee name and license number
  - Status badge: Not Started / Data Uploaded / Analysis Done / Under Review / Final
  - ARR Approved (₹ Cr)
  - ARR Actual (₹ Cr)
  - Gap / Surplus (₹ Cr) with green/red color
  - "Open" button → takes to Licensee Detail

**KSERC Specific:** Shows the work order reference at top right: KSERC/CSO/03-05

---

### Screen 2: Licensee Detail — Upload Data

**Purpose:** Upload and confirm financial data for one licensee.

**Step 1: Select Licensee and Financial Year**
- Dropdown: Select Licensee (KDHP / Technopark / Infoparks / CSEZA)
- Dropdown: Financial Year (2024-25)
- Dropdown: Document Type (Annual Accounts / ARR Petition / Audited Statements)

**Step 2: Upload Documents**
- Large drag-and-drop zone: "Drop PDF or Excel file here"
- Supported formats listed: PDF, XLSX, CSV
- Upload progress bar

**Step 3: AI Extraction Preview**
- System shows extracted data in a table:
  - Cost Head Name | Extracted Value | Source Page | Confidence
- User can correct any value by clicking the cell
- "Confirm Extraction" button → locks data and proceeds to analysis

**Validation Rules at Upload:**
- File size limit: 50 MB
- At least one revenue figure must be present
- At least 5 cost heads must be extracted
- If confidence < 70% for any field, highlight in amber with warning

---

### Screen 3: Analysis — Run Analysis

**Purpose:** Run all validation checks and AI reasoning on uploaded data.

**Layout:**
- Button: "Run Full Analysis" (primary, large)
- Progress section shows steps completing in real-time:
  1. ✓ Data Validation (completeness check)
  2. ✓ Arithmetic Consistency Check
  3. ✓ Year-on-Year Deviation Check
  4. ✓ Energy Balance Verification
  5. ✓ Revenue Cross-Check
  6. ✓ AI Prudence Check (calls LLM)
  7. ✓ Revenue Gap Computation
  8. ✓ Analysis Report Generated

- After completion, shows summary:
  - Total Cost Heads Analyzed: N
  - Flags Raised: N (X critical, Y moderate, Z informational)
  - AI Verdict: N Approved / N Partial / N Disallowed
  - Computed Revenue Gap: ₹ X Cr

---

### Screen 4: Review & Edit — Cost Head Detail

**Purpose:** Let KSERC officer review and override each cost head analysis.

**Layout:**
- Table with columns:
  - Cost Head | Category | Approved (₹ Cr) | Actual (₹ Cr) | Deviation % | AI Verdict | Action

- Each row is expandable to show:
  - **AI Reasoning:** "Based on KSERC Order No. [X] dated [Y], similar overrun in O&M was partially disallowed. Current deviation of 18% exceeds the normative cap of 5%..."
  - **Historical Benchmark:** Sparkline of this cost head over 5 years
  - **Rule Applied:** Text of the specific KSERC regulation used
  - **Override Section:** Dropdown (Approve / Partial Approve / Disallow) + Text box for reason

- Status bar showing total allowed ARR as officer makes changes

**Flags Panel (right column):**
- List of all flags with severity (critical / moderate / info)
- Each flag has a "Go to Cost Head" link

---

### Screen 5: Revenue Gap Summary

**Purpose:** Show the computed Revenue Gap with full waterfall.

**Charts:**
1. **Waterfall Chart:** Starting from ARR Approved, each cost head deviation adds/removes, ending at ARR Actual
2. **Bar Chart:** Approved vs Actual per cost head (horizontal bars, sorted by deviation size)
3. **Pie Chart:** Cost composition of final approved ARR

**Key Numbers (large, prominent):**
- ARR Approved by KSERC: ₹ X Cr
- ARR Actual (after prudence): ₹ X Cr  
- Revenue Actual: ₹ X Cr
- **Revenue Gap / Surplus: ₹ X Cr** (red if gap, green if surplus)

**Historical Comparison:**
- Table showing last 5 years' gaps for this licensee
- Current year highlighted

---

### Screen 6: Generate Report

**Purpose:** Generate the formal KSERC Truing-Up order document.

**Step 1: Review Summary (one page, all key decisions visible)**

**Step 2: Generate Draft Report**
- "Generate Draft" button
- System creates narrative sections using LLM API
- Preview appears in a document viewer

**Report Structure (matches KSERC order format):**
1. Background
2. Licensee Details and License Number
3. Approved ARR (as per KSERC Tariff Order)
4. Actual Performance — Cost-wise Analysis
5. Prudence Checks and Observations
6. Revenue and Revenue Gap Computation
7. Commission's Findings
8. Order / Directions
9. Annexures (data tables)

**Step 3: Human Review**
- KSERC officer reads the draft
- Can edit any paragraph directly in the preview
- Must tick a checkbox: "I have reviewed and confirm this report is accurate"

**Step 4: Export**
- "Download as PDF" button
- "Download as Word (.docx)" button
- Report is stamped with work order reference and date

---

### Screen 7: Historical Data

**Purpose:** Reference library of past truing-up data and commission orders.

**Tabs:**
- **Year-wise Data:** Table of all cases with key financial figures, filterable by licensee and year
- **Extreme Cases:** Manually curated examples — largest gap, largest disallowance, most contested case
- **Commission Orders:** Searchable library of past order PDFs with key ruling extracted

---

### Screen 8: Audit Trail

**Purpose:** Full log of all computations and decisions for regulatory compliance.

**Columns:** Timestamp | Action Type | User | Value Before | Value After | Reason

**Export:** Full audit trail as PDF, signed with session metadata.

---

## 4. AI Analysis Workflow (Internal Logic Flow)

```
Document Upload
    ↓
OCR / Text Extraction (Google Gemini Vision for scanned PDFs)
    ↓
Field Mapping (regex + LLM mapping to KSERC cost taxonomy)
    ↓
Validation Layer
  ├── Arithmetic check: do columns sum correctly?
  ├── Energy balance: input energy = sold + losses?
  ├── Revenue check: units × tariff ≈ reported revenue?
  └── Range check: is each value within historical range?
    ↓
Deviation Computation
  For each cost head:
    Δ = Actual − Approved
    Δ% = (Δ / Approved) × 100
    ↓
  Flag if |Δ%| > threshold
    ↓
RAG Prudence Check
  ├── Query: "How has KSERC historically treated [Cost Head] deviations of ~X%?"
  ├── Vector search in historical orders knowledge base
  ├── Retrieve top-3 similar past cases
  ├── LLM generates verdict (Approve / Partial / Disallow) + reasoning
  └── Reasoning cites specific order number and year
    ↓
Revenue Gap Computation
  ARR_actual = Σ (Approved_i + Allowed_Deviation_i)
  Gap = ARR_actual − Revenue_actual
    ↓
Report Generation
  ├── Deterministic sections: all tables and numbers (no LLM)
  └── Narrative sections: LLM drafts paragraphs (user reviews before final)
```

---

## 5. RAG (Retrieval-Augmented Generation) Architecture

### Knowledge Base Contents
- KSERC Truing-Up orders for KDHP, Technopark, Infoparks, CSEZA (2015–2024)
- KSERC Tariff Regulations 2014 and 2020 (relevant clauses)
- CERC and SERC benchmark decisions on prudence checks

### Vector Database
- **Tool:** Supabase `pgvector` extension (free, no additional cost)
- **Embedding model:** `all-MiniLM-L6-v2` via Hugging Face free inference API
- **Chunk size:** 500 tokens with 50-token overlap
- **Retrieval:** Top-K cosine similarity search (K=5)

### RAG Query Pattern
```python
# Query: "KDHP O&M expense deviation 15% prudence check"
# → Embed query
# → Find 5 most similar chunks from past orders
# → Build prompt:
#   "You are a KSERC regulatory officer. Based on the following extracts from
#    past commission orders: [CONTEXT], provide a verdict on whether an O&M
#    overrun of 15% by KDHP should be allowed. State the applicable regulation
#    and reference the specific order you are relying on."
# → LLM generates verdict
```

---

## 6. Technology Stack (Tool Selection Guide)

| Task | Recommended Tool | Why | Where to Build |
|------|-----------------|-----|----------------|
| Frontend UI | Next.js 14 + Tailwind CSS | Vercel-native, fast, React ecosystem | Cursor / Windsurf |
| Component Library | shadcn/ui | Free, accessible, Tailwind-based | Cursor |
| Charts | Recharts | Free, React, good for regulatory charts | — |
| Backend API | Next.js API Routes | Same repo, serverless on Vercel | Cursor |
| Database | Supabase (PostgreSQL + pgvector) | Free tier, real-time, auth built-in | supabase.com |
| Auth | Supabase Auth | Free, email + password | — |
| PDF Parsing | pdf-parse (npm) | Free, no API needed | — |
| Excel Parsing | xlsx (SheetJS) | Free, browser + server | — |
| OCR | Google Gemini 2.0 Flash (Vision) | Free 60 rpm, multimodal | aistudio.google.com |
| AI Analysis | Groq (llama-3.3-70b-versatile) | Free 14,400 req/day, very fast | console.groq.com |
| Fallback AI | OpenRouter (deepseek-r1:free) | Free 50 req/day, strong reasoning | openrouter.ai |
| Embeddings | HuggingFace (all-MiniLM-L6-v2) | Free inference API | huggingface.co |
| Report PDF | react-pdf / jsPDF | Free, client-side PDF generation | — |
| Deployment | Vercel Hobby | Free, GitHub integration | vercel.com |
| CI/CD | GitHub Actions | Free for public repos | github.com |

---

## 7. Responsive Behavior

The application is desktop-first (KSERC offices use desktop workstations). No mobile layout required for v1. Minimum screen width: 1280px. All tables are horizontally scrollable if content overflows.

---

*End of Design & Workflow Specification v1.0*
