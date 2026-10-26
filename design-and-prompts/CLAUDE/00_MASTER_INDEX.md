# KSERC AI Truing-Up Tool — Master Project Index
> **Work Order:** KSERC/CSO/03-05 | Dated 28th January 2026  
> **Institution:** Rajadhani Institute of Engineering and Technology (RIET), Thiruvananthapuram  
> **Student:** Prakhar Sharma, B.Tech, RIET Kerala  
> **Objective:** AI-based tool to automate the Truing-Up analysis of 4 distribution licensees for FY 2024-25

---

## Quick Summary: What Is Being Built

The **KSERC AI Truing-Up Tool** is an intelligent financial validation system for the Kerala State Electricity Regulatory Commission. It automates the process of comparing what electricity distribution licensees were approved to earn versus what they actually earned — and computes the Revenue Gap or Surplus.

**The 4 Licensees:**
1. Kanan Devan Hills Plantations (KDHPCL)
2. Electronics Technology Parks / Technopark
3. Infoparks Kerala
4. Cochin Special Economic Zone Authority (CSEZA)

**Core Formula:**
```
Revenue Gap / Surplus = Approved ARR − Actual Revenue
Positive = Gap (licensee owed money)   Negative = Surplus (collected too much)
```

---

## Document Index — Feed These to Your AI Assistant

| # | File Name | Purpose | When to Use |
|---|---|---|---|
| 01 | `01_Design_System.md` | Colors, typography, spacing, components | Every UI screen you build |
| 02 | `02_User_Flow_Wireframes.md` | Screen-by-screen layout + navigation flow | Before building any new page |
| 03 | `03_Tech_Stack_Architecture.md` | Tech choices, file structure, code rules | Start of every coding session |
| 04 | `04_Database_Schema.md` | Full PostgreSQL schema with all tables | Before any DB or ORM work |
| 05 | `05_API_Contract.md` | All API endpoints with request/response examples | Connecting frontend to backend |
| 06 | `06_Context_Memory_Prompt_Library.md` | Project state + ready-to-use prompts for each feature | Start of every new coding session |
| 07 | `07_AI_Behavior_Guidelines.md` | System prompt for the AI engine + rules | Building the AI reasoning module |
| 08 | `08_Edge_Case_Checklist.md` | 40+ edge cases to handle | After building any feature |
| 09 | `09_Security_Privacy_Policy.md` | KSERC data confidentiality obligations | Before any data handling code |
| 10 | `10_Test_Plan.md` | Manual test cases for KSERC demo | Before every demo |
| 11 | `11_Visual_References_Moodboard.md` | Visual vibe + anti-patterns | Before any UI generation |

---

## Build Order (Recommended Sequence)

```
Phase 1 — Foundation (Do This First)
  1. Set up project structure (React + FastAPI + PostgreSQL + Docker)
  2. Run database migrations (create all tables from 04_Database_Schema.md)
  3. Build authentication (Login + JWT)
  4. Build basic document upload API

Phase 2 — Core Engine
  5. PDF extraction service (pdfplumber)
  6. Calculation module (revenue gap, AT&C loss, O&M cap)
  7. Symbolic rule engine (perennial rejections, normative checks)
  8. Seed historical data (7 records in historical_orders table)

Phase 3 — AI Brain
  9. Set up ChromaDB + sentence-transformers
  10. Ingest KSERC regulations into knowledge base
  11. Build RAG query function (LlamaIndex)
  12. Integrate Gemini 1.5 Flash for reasoning
  13. Build parallel drafting + reasoning synthesis

Phase 4 — Frontend
  14. Dashboard + sidebar navigation
  15. Upload screen
  16. Analysis progress screen
  17. Results table with review interface
  18. Historical data view

Phase 5 — Reports
  19. PDF report generator (reportlab)
  20. Word report generator (python-docx)

Phase 6 — Polish & Test
  21. Handle all P0 edge cases from 08_Edge_Case_Checklist.md
  22. Run all tests from 10_Test_Plan.md
  23. Demo dry run
```

---

## Historical Benchmarks (Critical Reference)

| Licensee | Year | Claimed | Approved | Type |
|---|---|---|---|---|
| Technopark | 2020-21 | — | +₹280.42 L | Max Surplus |
| CSEZA | 2022-23 | — | +₹135.14 L | Surplus |
| Kanan Devan | 2022-23 | — | +₹116.91 L | Surplus |
| CSEZA | 2023-24 | −₹3.42 L | +₹87.85 L | Reversal ⚠️ |
| Kanan Devan | 2021-22 | +₹13.61 L | +₹58.72 L | Overshoot ⚠️ |
| Infopark | 2020-21 | −₹76.53 L | −₹60.80 L | Max Gap |
| Infopark | 2024-25 | −₹79.76 L | −₹64.72 L | Max Gap |

> Any AI output outside ±₹280.42 L must trigger a warning.

---

## Perennial Rejections (Hardcoded — Never Change)

These items are **always** rejected by KSERC, regardless of what the licensee claims:
1. **Section 3(1) Electricity Duty** → ₹0 approved
2. **CSR Expenses** → ₹0 approved  
3. **RPO Liability Provisions** → ₹0 (only actual REC payments allowed)

---

## Key Contacts

| Role | Name | Contact |
|---|---|---|
| KSERC (Client) | Secretary, KSERC | kserc@erckerala.org, 0471 273 5544 |
| Institution | Principal, RIET | principal@riet.edu.in, 9495431623 |
| Student Developer | Prakhar Sharma, B.Tech, RIET | — |

---

## Work Order Reference
- **Work Order No.:** KSERC/CSO/03-05
- **Date:** 28th January 2026
- **Timeline:** 8 weeks from date of issue (prototype to KSERC ASAP)
- **IPR:** Vests with KSERC. RIET may use for academic purposes with prior Commission approval.
- **Nature:** ISR initiative — no financial remuneration.
