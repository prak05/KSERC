# Product Requirements Document (PRD)
**Project Name:** KSERC AI-Based Analytical Tool for Truing Up of Accounts
**Client:** Kerala State Electricity Regulatory Commission (KSERC)
**Target:** Distribution Licensees (KDHPCL, Technopark, Infopark, CSEZA)

## 1. Executive Summary
Develop an AI-assisted financial validation tool to assist KSERC in the "truing-up" process of distribution licensees for FY 2024-25. The tool will compare estimated/approved costs against actual submitted accounts, identify deviations, check prudency, and compute the final revenue gap or surplus. It must run on extremely low-cost/free LLM APIs and offer a fully functional app with no dummy data or placeholders.

## 2. Goals & Objectives
*   **Automate Truing-Up:** Ingest historical ARR orders, actual annual accounts, and tariff documents to compute the revenue gap/surplus automatically.
*   **Prudence Checks & Validation:** Automatically disallow costs that violate established KSERC rules (e.g., O&M normative caps, Section 3(1) duty).
*   **Zero Hallucination:** Computations must be strictly formula-based. The AI is *only* used for data extraction and reasoning explanation.
*   **Low Cost / Open Source:** Built on a completely free or ultra-cheap API infrastructure (DeepSeek / Groq / OpenAI-compatible free tiers).
*   **Explainable AI:** Every disallowance or flagged item must have a clear "Reasoning Trace" linking back to the official regulation.

## 3. Core Features
1.  **AI Document Extraction Engine:** Ingests PDFs/Excel sheets (ARR Order, Annual Accounts) and extracts financial data points into structured JSON.
2.  **Regulatory Rules Engine (Hardcoded Math):** 
    *   Applies Perennial Rejections (Section 3(1) duty, CSR, RPO liabilities).
    *   Computes O&M Normative Cap (Escalation index calculations).
    *   Computes AT&C Loss efficiency gains and 2/3 sharing rules.
    *   Computes exact Revenue Gap / Surplus (Approved ARR - Actual Revenue).
3.  **Validation Dashboard:** Clutter-free UI showing tabular data of Claimed vs Approved vs Disallowed amounts.
4.  **AI Reasoning Panel:** Explains *why* a specific value was disallowed with citations.
5.  **Manual Override & Audit Log:** Allows KSERC staff to manually correct extracted values or override AI decisions safely.
6.  **Report Generator:** Compiles the findings into a formal, downloadable PDF drafted as a KSERC "Order".

## 4. User Personas
*   **KSERC Regulator / Analyst:** Demands high accuracy, clutter-free tabular interfaces, zero animations, highly legible fonts, and instant reasoning traces for all numbers.

## 5. Non-Functional Requirements
*   **Accuracy:** 100% mathematical accuracy for the rules engine.
*   **Privacy:** Since this uses free public APIs, the data sent to the AI must strictly be document text extraction only (no sensitive commission-internal notes unless sanitized). 
*   **Vibe Coding Ready:** The source code must be cleanly modularized so an AI code generator (Cursor/Windsurf) can assemble the entire app from this spec.
