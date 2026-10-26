# KSERC AI Truing-Up Tool — Database Schema (ERD)
> **Project:** AI-Based Analytical Tool for Truing Up of Accounts | Work Order No. KSERC/CSO/03-05  
> **Version:** 1.0 | Date: 2026

---

## 1. Entity-Relationship Overview

```
┌─────────────┐        ┌──────────────────┐        ┌─────────────────┐
│    users    │        │    licensees      │        │  financial_years │
│─────────────│        │──────────────────│        │─────────────────│
│ id (PK)     │        │ id (PK)           │        │ id (PK)          │
│ username    │        │ name              │        │ year_label       │
│ password_hash│       │ short_code        │        │ start_date       │
│ role        │        │ address           │        │ end_date         │
│ created_at  │        │ license_number    │        └────────┬────────┘
└──────┬──────┘        └────────┬──────────┘                │
       │                        │                            │
       │                        ▼                            │
       │              ┌──────────────────────────────────────┤
       │              │        analysis_sessions              │
       │              │──────────────────────────────────────│
       └─────────────►│ id (PK)                               │
                      │ licensee_id (FK → licensees)          │
                      │ financial_year_id (FK → fin_years)    │
                      │ created_by (FK → users)               │
                      │ status (ENUM)                         │
                      │ created_at                            │
                      │ completed_at                          │
                      └────────────┬─────────────────────────┘
                                   │
              ┌────────────────────┼──────────────────────────┐
              │                    │                          │
              ▼                    ▼                          ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐
   │ uploaded_documents│  │ analysis_results │  │  generated_reports  │
   └──────────────────┘  └──────────────────┘  └────────────────────┘
              │                    │
              │                    ▼
              │          ┌──────────────────────┐
              │          │   line_item_validations│
              │          └──────────────────────┘
              │                    │
              │                    ▼
              │          ┌──────────────────────┐
              │          │   ai_reasoning_logs   │
              │          └──────────────────────┘
```

---

## 2. Complete Schema (PostgreSQL)

```sql
-- ============================================================
-- TABLE: users
-- Stores KSERC staff who can log into the system
-- ============================================================
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,               -- Auto-increment unique ID
    username        VARCHAR(100) NOT NULL UNIQUE,     -- Login username (e.g., staff email)
    password_hash   VARCHAR(255) NOT NULL,            -- bcrypt hashed password, NEVER store plain text
    full_name       VARCHAR(200),                     -- Staff member's full name
    role            VARCHAR(50) DEFAULT 'analyst',    -- 'analyst', 'senior_analyst', 'commissioner'
    is_active       BOOLEAN DEFAULT TRUE,             -- Soft disable instead of delete
    created_at      TIMESTAMP DEFAULT NOW(),          -- When user was created
    last_login      TIMESTAMP                         -- Track last login for audit
);


-- ============================================================
-- TABLE: licensees
-- The 4 distribution licensees covered under the Work Order
-- ============================================================
CREATE TABLE licensees (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(300) NOT NULL,            -- Full official name
    short_code      VARCHAR(20) NOT NULL UNIQUE,      -- e.g., 'INFOPARK', 'TECHNOPARK', 'KDHPCL', 'CSEZA'
    license_number  VARCHAR(100),                     -- KSERC license number
    address         TEXT,                             -- Registered address
    contact_email   VARCHAR(200),                     -- Licensee's official email
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Pre-populate with the 4 licensees from the Work Order
INSERT INTO licensees (name, short_code) VALUES
    ('Kanan Devan Hills Plantations Company Pvt Ltd', 'KDHPCL'),
    ('Electronics Technology Parks – Kerala, Technopark', 'TECHNOPARK'),
    ('Infoparks Kerala', 'INFOPARK'),
    ('Cochin Special Economic Zone Authority', 'CSEZA');


-- ============================================================
-- TABLE: financial_years
-- Tracks each truing-up financial year
-- ============================================================
CREATE TABLE financial_years (
    id          SERIAL PRIMARY KEY,
    year_label  VARCHAR(10) NOT NULL UNIQUE,    -- e.g., '2024-25'
    start_date  DATE NOT NULL,                  -- April 1 of the year
    end_date    DATE NOT NULL,                  -- March 31 of next year
    is_current  BOOLEAN DEFAULT FALSE           -- Flag the active truing-up year
);


-- ============================================================
-- TABLE: analysis_sessions
-- Each time staff initiates a truing-up analysis for a licensee
-- ============================================================
CREATE TABLE analysis_sessions (
    id                  SERIAL PRIMARY KEY,
    licensee_id         INTEGER REFERENCES licensees(id) ON DELETE RESTRICT,
    financial_year_id   INTEGER REFERENCES financial_years(id) ON DELETE RESTRICT,
    created_by          INTEGER REFERENCES users(id),
    status              VARCHAR(50) DEFAULT 'pending',
    -- Status values: 'pending', 'ingesting', 'analyzing', 'review', 'approved', 'report_generated'
    notes               TEXT,                       -- Staff notes on this analysis
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),
    completed_at        TIMESTAMP,                  -- When final approval was given
    UNIQUE(licensee_id, financial_year_id)          -- One analysis per licensee per year
);


-- ============================================================
-- TABLE: uploaded_documents
-- Tracks all files uploaded for an analysis session
-- ============================================================
CREATE TABLE uploaded_documents (
    id              SERIAL PRIMARY KEY,
    session_id      INTEGER REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    document_type   VARCHAR(100) NOT NULL,
    -- Types: 'annual_accounts', 'arr_order', 'previous_truing_up', 'energy_audit', 'tariff_schedule'
    original_filename   VARCHAR(500),               -- Original file name from upload
    stored_path         VARCHAR(1000),              -- Path on server where file is saved
    file_size_bytes     BIGINT,                     -- File size for audit
    mime_type           VARCHAR(100),               -- 'application/pdf', 'application/xlsx'
    extraction_status   VARCHAR(50) DEFAULT 'pending',
    -- 'pending', 'extracted', 'extraction_failed'
    extraction_error    TEXT,                       -- Error message if extraction failed
    uploaded_by         INTEGER REFERENCES users(id),
    uploaded_at         TIMESTAMP DEFAULT NOW()
);


-- ============================================================
-- TABLE: extracted_financial_data
-- Structured financial data extracted from uploaded documents
-- All monetary values stored in Lakhs (₹ Lakh)
-- ============================================================
CREATE TABLE extracted_financial_data (
    id                  SERIAL PRIMARY KEY,
    session_id          INTEGER REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    source_document_id  INTEGER REFERENCES uploaded_documents(id),
    
    -- Revenue Items
    approved_arr                    NUMERIC(12, 4),  -- Approved Aggregate Revenue Requirement (₹ Lakh)
    actual_revenue_from_tariff      NUMERIC(12, 4),  -- Actual revenue from electricity charges (₹ Lakh)
    actual_non_tariff_income        NUMERIC(12, 4),  -- Non-tariff income (interest, etc.) (₹ Lakh)
    
    -- Cost Items (all in ₹ Lakh)
    claimed_power_purchase_cost     NUMERIC(12, 4),
    claimed_employee_cost           NUMERIC(12, 4),
    claimed_rm_expense              NUMERIC(12, 4),  -- Repair & Maintenance
    claimed_ag_expense              NUMERIC(12, 4),  -- Admin & General
    claimed_depreciation            NUMERIC(12, 4),
    claimed_interest_on_loans       NUMERIC(12, 4),
    claimed_interest_on_wc          NUMERIC(12, 4),  -- Working Capital interest
    claimed_section_3_1_duty        NUMERIC(12, 4),  -- Always rejected by KSERC
    claimed_csr_expense             NUMERIC(12, 4),  -- Always rejected by KSERC
    claimed_other_expenses          NUMERIC(12, 4),
    
    -- Energy / Technical Data
    energy_input_mu                 NUMERIC(12, 4),  -- Energy input in Million Units (MU)
    energy_sold_mu                  NUMERIC(12, 4),  -- Energy sold to consumers (MU)
    approved_distribution_loss_pct  NUMERIC(6, 4),   -- KSERC-approved loss target (%)
    actual_distribution_loss_pct    NUMERIC(6, 4),   -- Actual distribution loss (%)
    
    -- Historical / ARR reference data
    previous_year_surplus_deficit   NUMERIC(12, 4),  -- Carry-forward from previous year (₹ Lakh)
    cumulative_regulatory_balance   NUMERIC(12, 4),  -- Running total (₹ Lakh)
    
    extraction_confidence           NUMERIC(4, 3),   -- AI extraction confidence (0.0 to 1.0)
    created_at                      TIMESTAMP DEFAULT NOW()
);


-- ============================================================
-- TABLE: analysis_results
-- Final computed results after rule engine + AI analysis
-- ============================================================
CREATE TABLE analysis_results (
    id                          SERIAL PRIMARY KEY,
    session_id                  INTEGER REFERENCES analysis_sessions(id) ON DELETE CASCADE UNIQUE,
    
    -- Core Calculated Metrics (₹ Lakh)
    computed_revenue_gap_surplus    NUMERIC(12, 4),  -- Positive = gap, Negative = surplus
    ai_recommended_gap_surplus      NUMERIC(12, 4),  -- AI's recommendation before human review
    commission_approved_amount      NUMERIC(12, 4),  -- Final approved amount after human review
    
    -- Computed AT&C Loss
    computed_atc_loss_pct           NUMERIC(6, 4),   -- (Energy Input - Energy Realized) / Energy Input
    
    -- Summary counts
    items_approved_count            INTEGER DEFAULT 0,
    items_flagged_count             INTEGER DEFAULT 0,
    items_rejected_count            INTEGER DEFAULT 0,
    
    -- Overall status
    overall_status                  VARCHAR(50),     -- 'gap', 'surplus', 'neutral'
    analysis_confidence_pct         NUMERIC(5, 2),   -- Overall AI confidence %
    
    created_at                      TIMESTAMP DEFAULT NOW(),
    reviewed_by                     INTEGER REFERENCES users(id),  -- Staff who reviewed
    reviewed_at                     TIMESTAMP
);


-- ============================================================
-- TABLE: line_item_validations
-- Detailed validation result for each cost/revenue line item
-- ============================================================
CREATE TABLE line_item_validations (
    id                  SERIAL PRIMARY KEY,
    session_id          INTEGER REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    item_name           VARCHAR(200) NOT NULL,       -- e.g., 'Employee Cost', 'Section 3(1) Duty'
    item_category       VARCHAR(100),                -- 'om_cost', 'revenue', 'power_purchase', 'tax'
    
    -- Values (₹ Lakh)
    claimed_amount      NUMERIC(12, 4),              -- What the licensee claimed
    normative_cap       NUMERIC(12, 4),              -- Regulatory maximum allowed
    ai_recommended      NUMERIC(12, 4),              -- AI's recommended approved amount
    staff_approved      NUMERIC(12, 4),              -- Final amount after human review
    disallowed_amount   NUMERIC(12, 4),              -- Amount not approved
    
    -- Decision
    validation_status   VARCHAR(50),
    -- 'approved', 'approved_with_reduction', 'flagged', 'rejected', 'pending_review'
    rejection_reason    TEXT,                        -- If rejected: why (e.g., "Section 3(1) duty not allowable")
    regulatory_reference VARCHAR(500),              -- e.g., "KSERC Tariff Regulations 2021, Reg. 12(3)"
    
    -- Staff override
    staff_override      BOOLEAN DEFAULT FALSE,       -- Did staff override AI recommendation?
    staff_override_note TEXT,                        -- Reason for override
    
    created_at          TIMESTAMP DEFAULT NOW()
);


-- ============================================================
-- TABLE: ai_reasoning_logs
-- Full traceability of AI reasoning for each line item
-- ============================================================
CREATE TABLE ai_reasoning_logs (
    id                      SERIAL PRIMARY KEY,
    session_id              INTEGER REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    line_item_id            INTEGER REFERENCES line_item_validations(id),
    reasoning_type          VARCHAR(100),           -- 'normative_check', 'anomaly_detection', 'regulation_lookup'
    retrieved_context       TEXT,                   -- What the RAG engine retrieved from knowledge base
    reasoning_chain         TEXT,                   -- Step-by-step AI reasoning text
    conclusion              TEXT,                   -- AI's conclusion for this item
    cited_sources           TEXT,                   -- References cited (regulation clause, past order)
    model_used              VARCHAR(100),           -- e.g., 'gemini-1.5-flash'
    confidence_score        NUMERIC(4, 3),          -- 0.0 to 1.0
    created_at              TIMESTAMP DEFAULT NOW()
);


-- ============================================================
-- TABLE: generated_reports
-- Tracks all generated truing-up order documents
-- ============================================================
CREATE TABLE generated_reports (
    id              SERIAL PRIMARY KEY,
    session_id      INTEGER REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    report_type     VARCHAR(50),        -- 'pdf_order', 'word_draft', 'excel_data'
    file_path       VARCHAR(1000),      -- Server path to generated file
    file_size_bytes BIGINT,
    generated_by    INTEGER REFERENCES users(id),
    generated_at    TIMESTAMP DEFAULT NOW(),
    is_final        BOOLEAN DEFAULT FALSE  -- TRUE = final order approved by Commissioner
);


-- ============================================================
-- TABLE: historical_orders
-- Seeded with past KSERC truing-up data for benchmarking
-- All amounts in ₹ Lakh
-- ============================================================
CREATE TABLE historical_orders (
    id              SERIAL PRIMARY KEY,
    licensee_code   VARCHAR(20),                    -- e.g., 'INFOPARK'
    financial_year  VARCHAR(10),                    -- e.g., '2020-21'
    claimed_amount  NUMERIC(12, 4),                 -- What licensee claimed
    approved_amount NUMERIC(12, 4),                 -- What KSERC approved
    outcome_type    VARCHAR(50),                    -- 'surplus', 'gap', 'reversal', 'overshoot'
    notes           TEXT,                           -- Notable aspects (e.g., 'Section 3(1) disallowed')
    source_order_ref VARCHAR(200)                   -- KSERC order reference number
);

-- Pre-populate with historical data from deep-research-report.md
INSERT INTO historical_orders (licensee_code, financial_year, claimed_amount, approved_amount, outcome_type, notes) VALUES
    ('TECHNOPARK',  '2020-21', NULL,     280.42,   'surplus',  'Highest observed surplus'),
    ('CSEZA',       '2022-23', NULL,     135.14,   'surplus',  NULL),
    ('KDHPCL',      '2022-23', NULL,     116.91,   'surplus',  NULL),
    ('KDHPCL',      '2021-22', 13.61,   58.72,    'overshoot', 'Commission approved 4x what was asked'),
    ('CSEZA',       '2023-24', -3.42,   87.85,    'reversal',  'Licensee claimed deficit; KSERC found surplus'),
    ('INFOPARK',    '2020-21', -76.53,  -60.80,   'gap',       'Commission reduced gap claim by ₹15.73L'),
    ('INFOPARK',    '2024-25', -79.76,  -64.72,   'gap',       'Commission reduced gap claim by ₹15.04L');


-- ============================================================
-- TABLE: audit_log
-- Complete audit trail of all user actions on financial data
-- ============================================================
CREATE TABLE audit_log (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),
    session_id      INTEGER REFERENCES analysis_sessions(id),
    action          VARCHAR(200) NOT NULL,           -- e.g., 'OVERRIDE_LINE_ITEM', 'APPROVE_REPORT'
    old_value       TEXT,                            -- Previous value (JSON)
    new_value       TEXT,                            -- New value (JSON)
    ip_address      VARCHAR(50),
    created_at      TIMESTAMP DEFAULT NOW()
);


-- ============================================================
-- INDEXES for performance
-- ============================================================
CREATE INDEX idx_sessions_licensee ON analysis_sessions(licensee_id);
CREATE INDEX idx_sessions_year ON analysis_sessions(financial_year_id);
CREATE INDEX idx_line_items_session ON line_item_validations(session_id);
CREATE INDEX idx_reasoning_session ON ai_reasoning_logs(session_id);
CREATE INDEX idx_historical_licensee_year ON historical_orders(licensee_code, financial_year);
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_session ON audit_log(session_id);
```

---

## 3. Key Business Rules Encoded in Schema

| Rule | Implementation |
|---|---|
| One analysis per licensee per year | `UNIQUE(licensee_id, financial_year_id)` on sessions table |
| All monetary values in Lakhs | `NUMERIC(12, 4)` — 12 digits, 4 decimal places |
| Positive = gap, Negative = surplus | Sign convention in `computed_revenue_gap_surplus` |
| Full audit trail | Every user action logged in `audit_log` |
| AI reasoning traceable | Every decision linked to `ai_reasoning_logs` with cited sources |
| Historical benchmarks pre-loaded | `historical_orders` seeded with all known KSERC data |
