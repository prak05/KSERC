# KSERC AI Truing-Up Tool — User Flow & Wireframes
> **Project:** AI-Based Analytical Tool for Truing Up of Accounts | Work Order No. KSERC/CSO/03-05  
> **Version:** 1.0 | Date: 2026

---

## 1. High-Level User Journey

```
[KSERC Staff arrives at the tool]
        │
        ▼
[LOGIN] ──► [DASHBOARD] 
                │
                ├──► [UPLOAD DOCUMENTS]
                │         │
                │         ▼
                │    [SELECT LICENSEE + YEAR]
                │         │
                │         ▼
                │    [UPLOAD: Annual Accounts + ARR Order + Past Truing Up]
                │         │
                │         ▼
                │    [AI INGESTION & VALIDATION]
                │         │
                ├──► [ANALYSIS ENGINE]
                │         │
                │         ├─ Revenue Gap / Surplus Calculation
                │         ├─ Power Purchase Validation
                │         ├─ O&M Normative Check
                │         ├─ AT&C Loss Computation
                │         ├─ Distribution Loss Efficiency Check
                │         └─ Prudence Check (Perennial Rejections)
                │         │
                │         ▼
                │    [FLAGGED ITEMS + AI REASONING]
                │         │
                │         ▼
                │    [HUMAN REVIEW SCREEN]
                │         │
                │         ▼
                │    [APPROVE / MODIFY / REJECT LINE ITEMS]
                │         │
                ├──► [REPORT GENERATION]
                │         │
                │         ▼
                │    [DRAFT TRUING-UP ORDER (PDF)]
                │         │
                │         ▼
                │    [FINAL APPROVAL BY COMMISSIONER]
                │
                └──► [HISTORICAL DATA VIEW]
```

---

## 2. Screen-by-Screen Wireframe Description

### Screen 1 — Login Page
```
┌────────────────────────────────────────────────────────┐
│                                                        │
│            [KSERC LOGO]  [RIET LOGO]                   │
│                                                        │
│       Kerala State Electricity Regulatory Commission   │
│            AI Truing-Up Analysis Tool                  │
│                                                        │
│   ┌──────────────────────────────────────┐             │
│   │  Username                            │             │
│   └──────────────────────────────────────┘             │
│   ┌──────────────────────────────────────┐             │
│   │  Password                            │             │
│   └──────────────────────────────────────┘             │
│                                                        │
│          [ LOGIN TO KSERC PORTAL ]                     │
│                                                        │
│   Authorized access only. Work Order KSERC/CSO/03-05  │
└────────────────────────────────────────────────────────┘
```

---

### Screen 2 — Dashboard (Home)
```
┌──────────────────────────────────────────────────────────────────┐
│  [KSERC Logo]  AI Truing-Up Tool         User: Staff  [Logout]   │
├─────────────┬────────────────────────────────────────────────────┤
│             │  Dashboard                                         │
│  Dashboard  │  ─────────────────────────────────────────────    │
│  Upload     │  FY 2024-25 Summary                               │
│  Analysis   │                                                    │
│  History    │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  Reports    │  │Infopark  │  │Technopark│  │Kanan Dev.│        │
│  Settings   │  │GAP       │  │SURPLUS   │  │SURPLUS   │        │
│  Help       │  │₹64.72 L  │  │Pending   │  │Pending   │        │
│             │  └──────────┘  └──────────┘  └──────────┘        │
│             │                                                    │
│             │  ┌─────────────────────────────────────────────┐  │
│             │  │  RECENT ACTIVITY                            │  │
│             │  │  • Infopark FY2024-25 — Analysis Complete   │  │
│             │  │  • CSEZA FY2023-24 — Pending Review         │  │
│             │  │  • KDHPCL FY2022-23 — Report Generated      │  │
│             │  └─────────────────────────────────────────────┘  │
│             │                                                    │
│             │  [ + Start New Truing-Up Analysis ]               │
└─────────────┴────────────────────────────────────────────────────┘
```

---

### Screen 3 — Upload Documents
```
┌──────────────────────────────────────────────────────────────────┐
│  Upload Documents                                                │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Step 1 of 3: Select Licensee & Year                            │
│                                                                  │
│  Distribution Licensee:                                          │
│  ┌──────────────────────────────────────┐                       │
│  │  [ Select Licensee ▼ ]               │                       │
│  │  • Kanan Devan Hills Plantations      │                       │
│  │  • Electronics Technology Parks       │                       │
│  │  • Infoparks Kerala                   │                       │
│  │  • Cochin Special Economic Zone Auth. │                       │
│  └──────────────────────────────────────┘                       │
│                                                                  │
│  Financial Year:  [ 2024-25 ▼ ]                                 │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│  Step 2 of 3: Upload Required Documents                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  📄 Audited Annual Accounts (PDF)           [Upload]     │    │
│  │  📄 ARR Order for FY 2024-25 (PDF)          [Upload]     │    │
│  │  📄 Previous Year Truing-Up Order (PDF)     [Upload]     │    │
│  │  📄 Energy Audit Statement (PDF/Excel)      [Upload]     │    │
│  │  📄 Tariff Schedule (PDF)                   [Optional]   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│  Step 3 of 3: Verify & Submit                                   │
│                                                                  │
│  [ Cancel ]                    [ Run AI Analysis → ]            │
└──────────────────────────────────────────────────────────────────┘
```

---

### Screen 4 — AI Analysis in Progress
```
┌──────────────────────────────────────────────────────────────────┐
│  Analyzing: Infoparks Kerala — FY 2024-25                        │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  ✅  Document Ingestion Complete (4 files)                       │
│  ✅  Revenue & Cost Data Extracted                               │
│  ✅  Revenue Gap Computed: ₹64.72 Lakh                          │
│  ⚙️  Running Prudence Checks...  [━━━━━━━━━━░░░░] 70%           │
│  ⏳  Generating Reasoning Report...                              │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  AI Reasoning Log                                        │    │
│  │  ────────────────────────────────────────────────────   │    │
│  │  > Loaded KSERC Tariff Regulations 2021                  │    │
│  │  > Employee Cost (Actual ₹12.3L) vs Norm ₹11.8L         │    │
│  │  > ⚠ Excess of ₹0.5L flagged for review                 │    │
│  │  > Distribution Loss: Actual 2.86% vs Target 4.23%      │    │
│  │  > Efficiency Gain = (4.23 - 2.86)% × Energy Input      │    │
│  │  > Licensee retains 2/3 of savings: Calculating...      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Please wait. Do not close this window.                         │
└──────────────────────────────────────────────────────────────────┘
```

---

### Screen 5 — Analysis Results / Human Review
```
┌──────────────────────────────────────────────────────────────────┐
│  Analysis Results: Infoparks Kerala — FY 2024-25                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  SUMMARY                                                   │ │
│  │  Claimed Gap: ₹79.76 Lakh   Recommended: ₹64.72 Lakh      │ │
│  │  Disallowed:  ₹15.04 Lakh   Status: [GAP — RED BADGE]     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  LINE-ITEM VALIDATION                                           │
│  ──────────────────────────────────────────────────────────     │
│  Item               Claimed   Approved  Status      Action      │
│  ─────────────────────────────────────────────────────────────  │
│  Power Purchase     ₹45.2L   ₹45.2L    ✅ Pass      [View]     │
│  Employee Cost      ₹12.3L   ₹11.8L    ⚠️ Flagged   [Review]   │
│  R&M Expense        ₹3.1L    ₹2.9L     ⚠️ Flagged   [Review]   │
│  Section 3(1) Duty  ₹2.5L    ₹0L       ❌ Rejected  [View]     │
│  CSR Expense        ₹1.2L    ₹0L       ❌ Rejected  [View]     │
│  Depreciation       ₹8.9L    ₹8.9L     ✅ Pass      [View]     │
│  Interest on Loans  ₹6.5L    ₹6.5L     ✅ Pass      [View]     │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│  [ View Full AI Reasoning ]   [ Modify ]   [ Generate Report → ]│
└──────────────────────────────────────────────────────────────────┘
```

---

### Screen 6 — AI Reasoning Detail (Drilldown)
```
┌──────────────────────────────────────────────────────────────────┐
│  ← Back   AI Reasoning: Employee Cost                            │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Item: Employee Cost (Operations & Maintenance)                  │
│  Claimed by Licensee: ₹12.30 Lakh                               │
│  Commission Approved: ₹11.80 Lakh                               │
│  Disallowed Amount:   ₹0.50 Lakh                                │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  AI REASONING                                           │    │
│  │                                                         │    │
│  │  Based on KSERC Tariff Regulations 2021, Regulation     │    │
│  │  12(3): Employee costs are capped at the normative       │    │
│  │  level escalated by the AICPI index (4.2% for FY25).    │    │
│  │                                                         │    │
│  │  Approved (FY24) = ₹11.32 Lakh                         │    │
│  │  Normative (FY25) = ₹11.32 × 1.042 = ₹11.80 Lakh      │    │
│  │  Claimed (FY25)   = ₹12.30 Lakh                        │    │
│  │  Excess            = ₹0.50 Lakh → DISALLOWED           │    │
│  │                                                         │    │
│  │  Reference: Past Order — Infopark FY2020-21 (same       │    │
│  │  logic applied; excess of ₹2.1L was disallowed).        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Staff Decision:                                                 │
│  ○ Accept AI Recommendation (₹11.80L)                          │
│  ○ Override — Enter Amount: [__________]                        │
│  ○ Flag for Senior Review                                       │
│                                                                  │
│  [ Save Decision ]                                              │
└──────────────────────────────────────────────────────────────────┘
```

---

### Screen 7 — Report Generation
```
┌──────────────────────────────────────────────────────────────────┐
│  Generate Truing-Up Report: Infoparks Kerala — FY 2024-25        │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Report includes:                                               │
│  ✅ Table 1: Comparison of Approved ARR vs Actuals              │
│  ✅ Table 2: Consumer Mix & Revenue Summary                      │
│  ✅ Table 3: Cost Validation (Line-by-Line)                     │
│  ✅ Table 4: Distribution Loss & Efficiency Analysis            │
│  ✅ Prudence Check Summary (Rejections & Approvals)             │
│  ✅ AI Reasoning Appendix (Traceability)                        │
│  ✅ Final Revenue Gap / Surplus: ₹64.72 Lakh                   │
│                                                                  │
│  Report Format:                                                 │
│  ○ PDF (Official Order Format)                                  │
│  ○ Word Document (Editable Draft)                               │
│  ○ Both                                                         │
│                                                                  │
│  [ Preview Draft ]        [ Download Report ]                   │
└──────────────────────────────────────────────────────────────────┘
```

---

### Screen 8 — Historical Data View
```
┌──────────────────────────────────────────────────────────────────┐
│  Historical Truing-Up Data                                       │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Filter:  Licensee [All ▼]   Year [All ▼]   Status [All ▼]     │
│                                                                  │
│  Licensee        Year      Claimed    Approved   Status         │
│  ─────────────────────────────────────────────────────────────  │
│  Technopark      2020-21   —          +₹280.42L  SURPLUS ✅     │
│  CSEZA           2022-23   —          +₹135.14L  SURPLUS ✅     │
│  Kanan Devan     2022-23   —          +₹116.91L  SURPLUS ✅     │
│  CSEZA           2023-24   -₹3.42L    +₹87.85L   REVERSAL ⚠️   │
│  Kanan Devan     2021-22   +₹13.61L   +₹58.72L   OVERSHOOT ⚠️  │
│  Infopark        2020-21   -₹76.53L   -₹60.80L   GAP ❌        │
│  Infopark        2024-25   -₹79.76L   -₹64.72L   GAP ❌        │
│                                                                  │
│  [Bar Chart: Year-on-Year Surplus/Gap by Licensee]             │
│  ─────────────────────────────────────────────────────────────  │
│  [ Export Data ]   [ View Order ]   [ Compare Years ]          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Navigation Flow Map

```
Login
  └── Dashboard
        ├── Upload Documents
        │     ├── Select Licensee + Year
        │     ├── Upload Files
        │     └── Confirm & Submit
        │           └── Analysis in Progress
        │                 └── Analysis Results
        │                       ├── Line-item Drilldown (Reasoning)
        │                       └── Report Generation
        │                             └── Download / Preview
        │
        ├── Historical Data
        │     ├── Filter & Search
        │     ├── View Individual Order
        │     └── Export
        │
        ├── Reports
        │     ├── Draft Reports (In Progress)
        │     └── Completed Orders
        │
        └── Settings
              ├── User Management
              ├── Regulatory Rules Configuration
              └── System Logs
```

---

## 4. Key Interaction Principles

1. **Single-column forms** — never multi-column. KSERC staff will scan top-to-bottom.
2. **Confirm before destructive actions** — always show a confirmation dialog before deleting or resetting data.
3. **No infinite scroll** — use pagination for tables (max 15 rows per page).
4. **Progress indicators** — always show where the user is in a multi-step process.
5. **Export everything** — every table and chart must have an export button (PDF / Excel).
6. **Breadcrumbs** — always show `Dashboard > Upload > Analysis` so users don't get lost.
