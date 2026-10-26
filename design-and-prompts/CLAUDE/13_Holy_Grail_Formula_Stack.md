# KSERC AI Truing-Up — The Holy Grail Document
## Formulas · Math · Tech Stack · Unstoppable AI Architecture
> Work Order KSERC/CSO/03-05 | RIET, Thiruvananthapuram
> This is your single source of truth. Feed this to every AI tool, every session, every time.

---

# ⚠️ APP VERDICT FIRST — What to Use vs What to Drop

| App | Verdict | Role in Project |
|---|---|---|
| **n8n** | ✅ USE | Pipeline orchestrator — upload → analyze → notify |
| **Zie619 automations** | ✅ USE | Free n8n workflow templates — clone, don't build from scratch |
| **AI Studio** | ✅ USE | Gemini API key source + prompt lab |
| **v0.dev** | ✅ USE | Generate entire frontend in React+Tailwind from description |
| **Supabase** | ✅ USE INSTEAD OF RAW POSTGRES | Replaces PostgreSQL + Auth + File Storage — free tier, zero setup |
| **Rowboat** | ✅ USE | Multi-agent framework — runs your parallel draft AI agents |
| **Ollama** | ✅ USE | Local LLM for when real KSERC confidential data is involved |
| **Stitch** | ✅ USE | ETL — pulls historical KSERC data into Supabase |
| **Antigravity** | ✅ USE | Rapid UI mockup before handing to v0 |
| **Google ADK** | ✅ USE | The agent reasoning brain — tool-calling, multi-step logic |
| **Colab** | ✅ USE | Test Python analysis code, RAG, embeddings — free GPU |
| **GitHub** | ✅ USE | Version control — required |
| **GitHub Copilot** | ✅ USE | Line-by-line code completion inside your editor |
| **chef.convex** | ⚠️ OPTIONAL | Real-time backend — use only if you want live collaborative features |
| **Y Combinator** | ❌ NOT A TOOL | It is a startup accelerator, not software. Ignore for building. |

---

# PART 1 — THE MATHEMATICS
## Every Formula the AI Brain Must Know and Execute

---

## 1.1 Core Truing-Up Formula

```
Revenue Gap / Surplus = Approved ARR − Actual Revenue Collected

Where:
  ARR  = Aggregate Revenue Requirement (₹ Lakh)

If result > 0  → Revenue GAP   (Commission owes licensee)
If result < 0  → Revenue SURPLUS (Licensee collected excess)
If result = 0  → Balanced (rare)

Historical Bounds (from real KSERC orders):
  Maximum ever approved surplus : +₹280.42 Lakh  (Technopark 2020-21)
  Maximum ever approved gap     : −₹64.72 Lakh   (Infopark 2024-25)
  Any result outside these bounds → FLAG AS ANOMALY
```

**Python Implementation:**
```python
def revenue_gap(approved_arr: float, actual_revenue: float) -> dict:
    # Subtract actual revenue from approved ARR to get the gap
    gap = approved_arr - actual_revenue
    # Positive = gap (owed to licensee), negative = surplus (excess collected)
    outcome = "GAP" if gap > 0 else "SURPLUS"
    # Sanity check against all known KSERC historical outcomes
    anomaly = gap > 64.72 or gap < -280.42
    return {"gap": round(gap, 4), "outcome": outcome, "anomaly": anomaly}
```

---

## 1.2 AT&C Loss Formula

```
AT&C Loss (%) = [ (Energy Input − Energy Realized) / Energy Input ] × 100

Where:
  Energy Input    = Total electricity purchased/generated (MU = Million Units)
  Energy Realized = (Units Sold × Collection Efficiency)

Simplified form used by KSERC:
  AT&C Loss (%) = [ (Energy Input − Energy Sold) / Energy Input ] × 100

Real example — Infopark FY2024-25:
  Target   = 4.23%
  Actual   = 2.86%
  Result   → Efficiency gain achieved (actual < target)
```

**Python Implementation:**
```python
def atc_loss(energy_input_mu: float, energy_sold_mu: float,
             target_pct: float) -> dict:
    # Core AT&C formula: losses as fraction of input
    actual_loss_pct = ((energy_input_mu - energy_sold_mu) / energy_input_mu) * 100
    # Check if licensee beat the target
    efficiency_gain_achieved = actual_loss_pct < target_pct
    # Calculate gain in percentage points
    gain_pct = target_pct - actual_loss_pct if efficiency_gain_achieved else 0
    # Energy saved due to better-than-target performance (in MU)
    energy_saved_mu = (gain_pct / 100) * energy_input_mu
    return {
        "actual_loss_pct"          : round(actual_loss_pct, 4),
        "target_pct"               : target_pct,
        "efficiency_gain_achieved" : efficiency_gain_achieved,
        "gain_pct"                 : round(gain_pct, 4),
        "energy_saved_mu"          : round(energy_saved_mu, 4)
    }
```

---

## 1.3 Efficiency Gain Sharing Formula (2/3 Rule)

```
When Actual AT&C Loss < Approved Target:

  Efficiency Gain in MU = (Target% - Actual%) × Energy Input / 100

  Power Purchase Savings = Efficiency Gain (MU) × Power Purchase Cost per Unit (₹/Unit)

  Licensee Retains = (2/3) × Power Purchase Savings
  Commission Takes = (1/3) × Power Purchase Savings

Regulation: KSERC Tariff Regulations 2021 — Distribution Loss Efficiency Sharing
```

**Python Implementation:**
```python
def efficiency_gain_sharing(target_pct: float, actual_pct: float,
                             energy_input_mu: float,
                             pp_cost_per_unit: float) -> dict:
    # Only calculate if licensee actually beat the target
    if actual_pct >= target_pct:
        return {"gain_achieved": False, "licensee_share_lakhs": 0}
    # Energy saved in MU due to better performance
    energy_saved_mu = ((target_pct - actual_pct) / 100) * energy_input_mu
    # Convert MU to kWh: 1 MU = 1,000,000 kWh = 10 Lakh kWh
    energy_saved_kwh = energy_saved_mu * 1_000_000
    # Total rupee savings from not buying that power
    total_savings_rs = energy_saved_kwh * pp_cost_per_unit
    # Convert to Lakhs
    total_savings_lakhs = total_savings_rs / 100_000
    # Licensee keeps 2/3, commission keeps 1/3
    licensee_share = (2 / 3) * total_savings_lakhs
    return {
        "gain_achieved"         : True,
        "energy_saved_mu"       : round(energy_saved_mu, 4),
        "total_savings_lakhs"   : round(total_savings_lakhs, 4),
        "licensee_share_lakhs"  : round(licensee_share, 4),
        "commission_share_lakhs": round(total_savings_lakhs - licensee_share, 4)
    }
```

---

## 1.4 O&M Normative Cap Formula

```
Normative Cap = Previous Year Approved O&M × (1 + Escalation Rate)

Where:
  Escalation Rate = AICPI (All India Consumer Price Index annual change)
  Typical range: 3.5% to 5.5% (verify actual rate for the year)

If Actual Claimed > Normative Cap:
  Disallowed Amount = Actual Claimed − Normative Cap
  Approved Amount   = Normative Cap

Exception: One-time documented expenditures (pay arrears, emergency repairs)
  may be approved ABOVE the cap if verified by documentary evidence.

Regulation: KSERC Tariff Regulations 2021, Regulation 12(3)
Covers: Employee Cost + Repair & Maintenance + Admin & General (O&M trio)
```

**Python Implementation:**
```python
def om_normative_check(prev_approved_lakhs: float, actual_claimed_lakhs: float,
                        aicpi_rate: float,
                        one_time_expense_lakhs: float = 0.0) -> dict:
    # Calculate the maximum allowable O&M for this year
    normative_cap = prev_approved_lakhs * (1 + aicpi_rate)
    # Total approved = cap + any verified one-time items
    total_approved = normative_cap + one_time_expense_lakhs
    # Amount disallowed = what was claimed beyond the approved ceiling
    disallowed = max(0, actual_claimed_lakhs - total_approved)
    # Approved is whichever is lower: claimed or total ceiling
    approved = min(actual_claimed_lakhs, total_approved)
    status = "approved" if disallowed == 0 else "approved_with_reduction"
    return {
        "normative_cap"       : round(normative_cap, 4),
        "one_time_approved"   : one_time_expense_lakhs,
        "total_ceiling"       : round(total_approved, 4),
        "claimed"             : actual_claimed_lakhs,
        "approved"            : round(approved, 4),
        "disallowed"          : round(disallowed, 4),
        "status"              : status,
        "regulation_ref"      : "KSERC Tariff Regulations 2021, Reg. 12(3)"
    }
```

---

## 1.5 Interest on Regulatory Surplus Formula

```
When a licensee has accumulated surplus over multiple years:

  Annual Interest = Cumulative Surplus Balance × SBI Retail Term Deposit Rate

This interest is counted as NON-TARIFF INCOME on the revenue side.
Licensees often forget to include this — KSERC adds it themselves.

Real case: KPUPL 2022-23
  Licensee reported interest income: ₹196.41 Lakh
  Commission recalculated: ₹326.04 Lakh
  Difference added to income: ₹129.63 Lakh (increased surplus further)

CRITICAL: SBI rate changes annually. Always verify current rate.
Typical range: 6.5% to 7.25% per annum
```

**Python Implementation:**
```python
def interest_on_surplus(cumulative_surplus_lakhs: float,
                         sbi_rate_pct: float) -> dict:
    # Convert percentage rate to decimal
    rate_decimal = sbi_rate_pct / 100
    # Simple annual interest on the accumulated surplus fund
    interest_income_lakhs = cumulative_surplus_lakhs * rate_decimal
    return {
        "cumulative_surplus_lakhs" : cumulative_surplus_lakhs,
        "sbi_rate_pct"             : sbi_rate_pct,
        "interest_income_lakhs"    : round(interest_income_lakhs, 4),
        "note": "This is NON-TARIFF INCOME. Add to revenue side of ARR computation."
    }
```

---

## 1.6 Capital Misclassification Reclassification Formula

```
When a licensee claims a capital asset purchase as an O&M (R&M) expense:

  Step 1: Reject the R&M claim entirely
  Step 2: Add asset to Gross Fixed Assets (GFA)
  Step 3: Compute depreciation:

    Annual Depreciation = Asset Value × Depreciation Rate (%)

  Depreciation rates per KSERC Regulations:
    Buildings           : 3.34%
    Plant & Machinery   : 5.28%
    Lines & Cable Network: 5.28%
    Vehicles            : 9.50%
    Furniture & Fixtures: 6.33%
    Office Equipment    : 6.33%

Real case: Infopark 2024-25
  EHT bushing replacement claimed as R&M: ₹11.59 Lakh
  Commission: reclassified as capital → approved depreciation only
```

**Python Implementation:**
```python
def reclassify_capital_expense(asset_value_lakhs: float,
                                asset_type: str) -> dict:
    # Standard depreciation rates from KSERC Tariff Regulations
    depreciation_rates = {
        "plant_machinery"    : 0.0528,   # 5.28% — most electrical equipment
        "lines_cable"        : 0.0528,   # 5.28%
        "buildings"          : 0.0334,   # 3.34%
        "vehicles"           : 0.0950,   # 9.50%
        "furniture_fixtures" : 0.0633,   # 6.33%
        "office_equipment"   : 0.0633    # 6.33%
    }
    rate = depreciation_rates.get(asset_type, 0.0528)  # Default to plant/machinery
    annual_depreciation = asset_value_lakhs * rate
    return {
        "original_rm_claim_rejected"   : asset_value_lakhs,
        "reclassified_as_capital"       : True,
        "asset_type"                    : asset_type,
        "depreciation_rate_pct"         : rate * 100,
        "approved_depreciation_lakhs"   : round(annual_depreciation, 4),
        "net_disallowed_lakhs"          : round(asset_value_lakhs - annual_depreciation, 4)
    }
```

---

## 1.7 Power Purchase Cost Variance Formula

```
Power Purchase Validation:

  Approved PP Cost = Approved Units (MU) × Approved BST Rate (₹/kWh)
  Actual PP Cost   = Actual Units Purchased × Actual BST Rate

  Variance = Actual PP Cost − Approved PP Cost

  If variance is due to:
    → Volume change (uncontrollable) : Pass-through allowed
    → Rate change from KSEB BST      : Pass-through allowed (uncontrollable)
    → Efficiency loss (controllable) : Apply gain-sharing formula above

  Check: Cost per Unit = Total PP Cost / Total Units Purchased
  Flag if: Actual Cost/Unit deviates > 15% from Approved Rate
```

---

## 1.8 Z-Score Anomaly Detection (Statistical)

```
For detecting unusual year-over-year changes in any cost item:

  Z-Score = (Current Year Value − Historical Mean) / Historical Std Deviation

  If |Z-Score| > 2.0 → FLAGGED (unusual, 95% confidence interval)
  If |Z-Score| > 3.0 → CRITICAL ANOMALY (99.7% confidence interval)

Apply to: Employee Cost, R&M, Power Purchase Cost/Unit, Revenue per Consumer

Python uses scipy.stats for this computation.
```

**Python Implementation:**
```python
import numpy as np  # For mean and standard deviation calculations

def zscore_anomaly(current_value: float,
                   historical_values: list[float]) -> dict:
    # Calculate the average of all historical values
    mean = np.mean(historical_values)
    # Calculate standard deviation (spread of historical data)
    std  = np.std(historical_values)
    # If no variation in history, can't compute z-score
    if std == 0:
        return {"z_score": 0, "flag": "INSUFFICIENT_HISTORY"}
    # Z-score = how many standard deviations from the mean
    z = (current_value - mean) / std
    # Classify severity
    flag = "NORMAL"
    if abs(z) > 3.0: flag = "CRITICAL_ANOMALY"
    elif abs(z) > 2.0: flag = "FLAGGED"
    return {
        "current_value"    : current_value,
        "historical_mean"  : round(mean, 4),
        "historical_std"   : round(std, 4),
        "z_score"          : round(z, 4),
        "flag"             : flag
    }
```

---

## 1.9 Fourier Transform — For Seasonal Pattern Detection in Power Data

```
The Fourier Transform decomposes a time series into frequency components.
For KSERC, this is used to detect SEASONAL patterns in:
  - Power purchase cost (peaks in summer/monsoon)
  - Consumer demand cycles
  - Revenue collection patterns

Discrete Fourier Transform (DFT):
  X[k] = Σ(n=0 to N-1) x[n] · e^(−j2πkn/N)

Where:
  x[n]  = time series values (e.g., monthly power purchase cost)
  N     = number of data points
  k     = frequency component index
  X[k]  = complex frequency domain representation

Inverse DFT (reconstruction):
  x[n] = (1/N) · Σ(k=0 to N-1) X[k] · e^(j2πkn/N)

Practical use for KSERC AI:
  1. Take 24-36 months of monthly power purchase data
  2. Apply FFT (Fast Fourier Transform via numpy)
  3. Identify dominant frequency peaks (e.g., 12-month cycle = annual seasonality)
  4. Separate seasonal component from trend
  5. Use trend line to project what the cost SHOULD be
  6. Compare against what licensee claimed → detect inflation
```

**Python Implementation:**
```python
import numpy as np  # NumPy has built-in FFT

def detect_seasonal_pattern(monthly_values: list[float]) -> dict:
    # Convert list to numpy array for FFT processing
    signal = np.array(monthly_values)
    n = len(signal)  # Total number of data points

    # Apply Fast Fourier Transform — decomposes signal into frequencies
    fft_result = np.fft.fft(signal)

    # Get the magnitude (amplitude) of each frequency component
    magnitudes = np.abs(fft_result)[:n // 2]  # Take only positive frequencies

    # Find the frequency with the highest amplitude (dominant pattern)
    dominant_freq_idx = np.argmax(magnitudes[1:]) + 1  # Skip DC component (index 0)

    # Convert frequency index to period in months
    dominant_period_months = n / dominant_freq_idx

    # Calculate the trend using linear regression on the signal
    x = np.arange(n)  # Time indices: 0, 1, 2, ... n-1
    trend_coeffs = np.polyfit(x, signal, 1)  # Fit a straight line
    trend_line = np.polyval(trend_coeffs, x)  # Evaluate the trend at each point

    # Detrended signal = original − trend (shows cyclical component only)
    detrended = signal - trend_line

    return {
        "dominant_period_months"    : round(dominant_period_months, 1),
        "trend_slope_per_month"     : round(trend_coeffs[0], 4),
        "seasonal_detected"         : dominant_period_months > 6,
        "detrended_values"          : detrended.tolist(),
        "interpretation"            : f"Dominant cycle every {dominant_period_months:.1f} months. "
                                       f"Monthly trend: ₹{trend_coeffs[0]:.2f}L per month."
    }
```

---

## 1.10 Regression for Cost Projection (Linear Regression)

```
Used to project what a cost SHOULD be based on historical trajectory:

  ŷ = β₀ + β₁x

Where:
  ŷ  = predicted cost value
  x  = time (year index: 1, 2, 3...)
  β₀ = intercept (baseline value)
  β₁ = slope (trend per year)

Least Squares solution:
  β₁ = [Σ(xᵢ − x̄)(yᵢ − ȳ)] / Σ(xᵢ − x̄)²
  β₀ = ȳ − β₁x̄

If Actual Cost >> Projected Cost → investigate and flag
```

---

# PART 2 — THE UNSTOPPABLE AI ARCHITECTURE
## A System That Learns From Every Order It Creates

---

## 2.1 The Learning Loop (How It Gets Smarter)

```
Every Truing-Up Order Created → Feeds Back Into the Brain

┌─────────────────────────────────────────────────────────┐
│                  LEARNING FLYWHEEL                       │
│                                                          │
│  New Order Uploaded                                      │
│       ↓                                                  │
│  AI Analyzes + Produces Draft Order                      │
│       ↓                                                  │
│  KSERC Staff Reviews → Approves / Modifies               │
│       ↓                                                  │
│  FINAL ORDER STORED IN SUPABASE                          │
│       ↓                                                  │
│  New order EMBEDDED into ChromaDB vector store           │
│       ↓                                                  │
│  Next analysis RETRIEVES this order as precedent         │
│       ↓                                                  │
│  AI now knows one more real decision to reason from      │
│       ↓                                                  │
│  Repeat → System gets smarter with every order           │
└─────────────────────────────────────────────────────────┘
```

This is not fine-tuning (expensive). This is **RAG with a growing knowledge base** — free, instant, and gets better with every use.

---

## 2.2 The Complete System Map

```
USER (KSERC Staff Browser)
        │
        │ HTTPS
        ▼
┌───────────────────────────────────────────────────────────┐
│           v0-GENERATED REACT FRONTEND                     │
│  (Antigravity mockup → v0 code → deployed on Vercel)     │
└─────────────────────────┬─────────────────────────────────┘
                          │ REST API calls
                          ▼
┌───────────────────────────────────────────────────────────┐
│           PYTHON FASTAPI BACKEND (on Colab/VPS)           │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  Upload API  │  │ Analysis API │  │  Reports API   │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘  │
│         └─────────────────┼────────────────────┘          │
│                           ▼                               │
│         ┌─────────────────────────────────────┐          │
│         │      GOOGLE ADK AGENT BRAIN          │          │
│         │                                     │          │
│         │  Tool 1: query_regulations(query)   │          │
│         │  Tool 2: lookup_historical(lic,yr)  │          │
│         │  Tool 3: calculate_gap(arr, rev)    │          │
│         │  Tool 4: check_om_cap(prev, actual) │          │
│         │  Tool 5: detect_anomalies(data)     │          │
│         │  Tool 6: perennial_reject(items)    │          │
│         │                                     │          │
│         │  ROWBOAT orchestrates parallel      │          │
│         │  agent drafts (LiR3AG strategy)     │          │
│         └────────────────┬────────────────────┘          │
│                          ▼                               │
│         ┌────────────────────────────────────┐           │
│         │    KNOWLEDGE BASE (ChromaDB)        │           │
│         │  • KSERC Regulations 2021/2014     │           │
│         │  • All past orders (growing)       │           │
│         │  • Every finalized order added     │           │
│         └────────────────┬───────────────────┘           │
│                          ▼                               │
│     GEMINI 1.5 FLASH (AI Studio) ←→ OLLAMA (local)      │
│     [prototype: Gemini] [production: Ollama+Mistral]     │
└───────────────────────────────────────────────────────────┘
                          │
              ┌───────────▼───────────┐
              │     SUPABASE           │
              │  PostgreSQL DB         │
              │  Auth (staff login)    │
              │  File Storage (PDFs)   │
              │  Real-time updates     │
              └────────────┬──────────┘
                           │
              ┌────────────▼──────────┐
              │    n8n WORKFLOW        │
              │  (Zie619 templates)    │
              │  Upload → Analyze      │
              │  → Notify → Archive    │
              └────────────┬──────────┘
                           │
              ┌────────────▼──────────┐
              │  STITCH ETL            │
              │  Pulls historical data │
              │  from any source into  │
              │  Supabase on schedule  │
              └───────────────────────┘
```

---

## 2.3 The Rowboat Multi-Agent Strategy (Parallel Drafting)

```
Rowboat runs multiple specialized agents simultaneously.
Each agent focuses on one dimension of the truing-up.
A master agent synthesizes all drafts into one final order.

Agent A — O&M Inspector
  Input: All cost items
  Task: Apply normative cap formula to Employee, R&M, A&G
  Output: Approved/disallowed per item with regulation cite

Agent B — Revenue Validator  
  Input: ARR order + actual accounts
  Task: Compute revenue gap/surplus, check non-tariff income
  Output: Final revenue gap figure with calculation trail

Agent C — Rejection Scanner
  Input: All claimed items
  Task: Flag Section 3(1), CSR, RPO provisions
  Output: List of perennial rejections with ₹0 approved

Agent D — Technical Auditor
  Input: Energy data
  Task: AT&C loss, efficiency gain, power purchase variance
  Output: Technical validation findings

Agent E — Anomaly Detector
  Input: Current + historical data
  Task: Z-score analysis, Fourier trend check, year-on-year spikes
  Output: Flagged anomalies with severity rating

Master Synthesizer Agent
  Input: Outputs from Agents A through E
  Task: Merge into coherent KSERC order format
  Task: Resolve any conflicts between agents
  Output: Final draft truing-up order
```

---

## 2.4 Supabase Schema (Replaces Raw PostgreSQL)

```sql
-- Run this in Supabase SQL Editor (free at supabase.com)

-- Licensees table
create table licensees (
  id          bigint generated always as identity primary key,
  name        text not null,
  short_code  text not null unique,
  created_at  timestamptz default now()
);

-- Insert the 4 KSERC licensees immediately
insert into licensees (name, short_code) values
  ('Kanan Devan Hills Plantations Company Pvt Ltd', 'KDHPCL'),
  ('Electronics Technology Parks – Kerala, Technopark', 'TECHNOPARK'),
  ('Infoparks Kerala', 'INFOPARK'),
  ('Cochin Special Economic Zone Authority', 'CSEZA');

-- Analysis sessions
create table analysis_sessions (
  id              bigint generated always as identity primary key,
  licensee_id     bigint references licensees(id),
  financial_year  text not null,
  status          text default 'pending',
  created_at      timestamptz default now(),
  completed_at    timestamptz,
  unique(licensee_id, financial_year)
);

-- Line item validations
create table line_item_validations (
  id                bigint generated always as identity primary key,
  session_id        bigint references analysis_sessions(id),
  item_name         text not null,
  claimed_lakhs     numeric(12,4),
  normative_cap     numeric(12,4),
  approved_lakhs    numeric(12,4),
  disallowed_lakhs  numeric(12,4),
  status            text,
  reasoning         text,
  regulation_ref    text,
  created_at        timestamptz default now()
);

-- AI reasoning logs (full traceability)
create table ai_reasoning_logs (
  id              bigint generated always as identity primary key,
  session_id      bigint references analysis_sessions(id),
  step_name       text,
  retrieved_context text,
  reasoning_chain text,
  conclusion      text,
  confidence      numeric(4,3),
  created_at      timestamptz default now()
);

-- Historical orders (pre-seed with known KSERC data)
create table historical_orders (
  id              bigint generated always as identity primary key,
  licensee_code   text,
  financial_year  text,
  claimed_lakhs   numeric(12,4),
  approved_lakhs  numeric(12,4),
  outcome_type    text,
  notes           text
);

-- Pre-seed all known historical data
insert into historical_orders 
  (licensee_code, financial_year, claimed_lakhs, approved_lakhs, outcome_type, notes)
values
  ('TECHNOPARK', '2020-21', null,    280.42,  'SURPLUS',   'Highest surplus on record'),
  ('CSEZA',      '2022-23', null,    135.14,  'SURPLUS',   null),
  ('KDHPCL',     '2022-23', null,    116.91,  'SURPLUS',   null),
  ('CSEZA',      '2023-24', -3.42,   87.85,   'REVERSAL',  'Claimed deficit, Commission found surplus'),
  ('KDHPCL',     '2021-22', 13.61,   58.72,   'OVERSHOOT', 'Commission approved 4x what was asked'),
  ('INFOPARK',   '2020-21', -76.53,  -60.80,  'GAP',       '15.73L disallowed'),
  ('INFOPARK',   '2024-25', -79.76,  -64.72,  'GAP',       '15.04L disallowed');

-- Generated reports
create table generated_reports (
  id            bigint generated always as identity primary key,
  session_id    bigint references analysis_sessions(id),
  report_type   text,
  file_path     text,
  is_final      boolean default false,
  created_at    timestamptz default now()
);
```

---

## 2.5 Fresh Install — Zero to Running in One Terminal Session

```bash
# ── STEP 1: Create project directory ──────────────────────
mkdir -p ~/Desktop/KSERC/app/templates
mkdir -p ~/Desktop/KSERC/app/static/img
mkdir -p ~/Desktop/KSERC/uploads
mkdir -p ~/Desktop/KSERC/reports
cd ~/Desktop/KSERC

# ── STEP 2: Create and activate virtual environment ────────
python3 -m venv kserc-env
source kserc-env/bin/activate

# ── STEP 3: Install ALL required packages at once ──────────
pip install flask \
            google-generativeai \
            pdfplumber \
            reportlab \
            python-docx \
            python-dotenv \
            werkzeug \
            supabase \
            numpy \
            scipy \
            pandas \
            sentence-transformers \
            chromadb

# ── STEP 4: Create .env with your Gemini key ───────────────
echo 'GEMINI_API_KEY=YOUR_KEY_FROM_AISTUDIO_HERE' > .env
echo 'SUPABASE_URL=YOUR_SUPABASE_PROJECT_URL' >> .env
echo 'SUPABASE_KEY=YOUR_SUPABASE_ANON_KEY' >> .env

# ── STEP 5: Verify installs ────────────────────────────────
python3 -c "import flask, google.generativeai, pdfplumber; print('All core packages OK')"

# ── STEP 6: Run the app ────────────────────────────────────
python3 app/main.py
```

---

## 2.6 Google ADK Agent Setup (The Reasoning Brain)

```bash
# Install Google ADK in your activated venv
pip install google-adk

# Verify
python3 -c "import google.adk; print('ADK ready')"
```

```python
# backend/app/services/adk_agent.py
# ─────────────────────────────────────────────────────────
# Google ADK Agent — The KSERC Reasoning Brain
# This agent uses tools to reason about a truing-up petition
# exactly like a senior KSERC staff member would.
# ─────────────────────────────────────────────────────────

from google.adk.agents import Agent          # Base agent class from Google ADK
from google.adk.tools import FunctionTool    # Wraps Python functions as agent tools

# ── Define the tools the agent can call ──────────────────
def query_regulations(query: str) -> str:
    """Search KSERC regulations knowledge base for relevant clauses."""
    # In production: query ChromaDB vector store with sentence-transformers
    # For now: return hardcoded rules for the most common queries
    rules = {
        "section 3": "Section 3(1) Electricity Duty: REJECTED. Cannot be passed to consumers.",
        "csr": "CSR Expenses: REJECTED. Appropriation of profit, not distribution cost.",
        "om cap": "Regulation 12(3): O&M capped at prev_approved × (1 + AICPI_rate).",
        "distribution loss": "Efficiency gain: licensee retains 2/3 of savings when actual < target.",
        "interest surplus": "Interest on surplus = cumulative_balance × SBI_retail_deposit_rate."
    }
    for key, val in rules.items():
        if key in query.lower():
            return val
    return "Regulation not found in cache. Verify against KSERC Tariff Regulations 2021."

def check_perennial_rejection(item_name: str, claimed_amount: float) -> dict:
    """
    Checks if a line item is a perennial rejection (always ₹0 approved).
    Returns the decision immediately without calling the LLM.
    """
    # List of items always rejected — hardcoded, deterministic, no AI needed
    always_rejected = [
        "section 3", "section 3(1)", "electricity duty",
        "csr", "corporate social responsibility",
        "rpo liability", "rpo provision", "renewable purchase obligation"
    ]
    item_lower = item_name.lower()
    # Check if this item matches any perennial rejection pattern
    for pattern in always_rejected:
        if pattern in item_lower:
            return {
                "item"          : item_name,
                "claimed"       : claimed_amount,
                "approved"      : 0.0,           # Always zero
                "disallowed"    : claimed_amount,
                "status"        : "REJECTED",
                "reason"        : f"Perennial rejection: {item_name} is not allowable in ARR.",
                "is_perennial"  : True
            }
    return {"is_perennial": False}  # Not a perennial rejection

# ── Create the ADK Agent with tools ──────────────────────
kserc_agent = Agent(
    name="KSERC-Analyst",
    model="gemini-1.5-flash",   # Uses Gemini under the hood
    instruction="""
You are a senior regulatory analyst for KSERC.
Analyze truing-up petitions using the provided tools.
Always call check_perennial_rejection for each line item FIRST.
Always call query_regulations before approving or rejecting a cost.
Show your calculations. Use ₹ Lakh. Cite regulation for every decision.
Never approve Section 3(1) duty or CSR under any circumstances.
""",
    tools=[
        FunctionTool(func=query_regulations),       # Regulation lookup tool
        FunctionTool(func=check_perennial_rejection) # Hard rejection tool
    ]
)
```

---

## 2.7 Rowboat Multi-Agent Setup

```bash
pip install rowboat
```

```python
# backend/app/services/rowboat_agents.py
# Rowboat orchestrates multiple specialized agents running in parallel.
# Each agent reviews one aspect. Master agent synthesizes all findings.

from rowboat import MultiAgentOrchestrator, AgentConfig  # Rowboat framework

# Define each specialized agent configuration
om_inspector_config = AgentConfig(
    name="OM-Inspector",
    role="Validate O&M costs: Employee, R&M, A&G against normative caps",
    model="gemini-1.5-flash"
)

revenue_validator_config = AgentConfig(
    name="Revenue-Validator",
    role="Compute Revenue Gap or Surplus. Verify non-tariff income.",
    model="gemini-1.5-flash"
)

rejection_scanner_config = AgentConfig(
    name="Rejection-Scanner",
    role="Flag Section 3(1), CSR, RPO provisions. Approve ₹0 for all.",
    model="gemini-1.5-flash"
)

technical_auditor_config = AgentConfig(
    name="Technical-Auditor",
    role="AT&C loss, efficiency gain (2/3 rule), power purchase variance.",
    model="gemini-1.5-flash"
)

# Create the multi-agent orchestrator
orchestrator = MultiAgentOrchestrator(
    agents=[
        om_inspector_config,
        revenue_validator_config,
        rejection_scanner_config,
        technical_auditor_config
    ],
    synthesis_model="gemini-1.5-flash"  # Master agent that merges all drafts
)

async def parallel_analysis(document_text: str, licensee: str, year: str) -> str:
    """
    Runs all specialized agents in parallel on the same document.
    Each agent produces its own draft findings.
    Synthesis agent merges everything into one coherent KSERC order.
    """
    # Build the shared context all agents will receive
    shared_context = f"""
    Licensee: {licensee}
    Financial Year: {year}
    Document Content: {document_text[:6000]}
    """
    # Run all agents simultaneously — Rowboat handles parallelism
    result = await orchestrator.run(shared_context)
    return result  # Returns the synthesized final analysis
```

---

## 2.8 GitHub + Copilot Workflow

```bash
# Initialize git in your project (run once)
cd ~/Desktop/KSERC
git init
git add .
git commit -m "Initial KSERC AI Truing-Up Tool"

# Create .gitignore to protect secrets
cat > .gitignore << 'EOF'
.env
kserc-env/
uploads/
reports/
__pycache__/
*.pyc
.chroma/
EOF

# Push to GitHub
# First create a repo at github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/kserc-truingup.git
git push -u origin main
```

**GitHub Copilot shortcut keys:**
- `Tab` — accept suggestion
- `Alt+]` — next suggestion
- `Alt+[` — previous suggestion
- `Ctrl+Enter` — open Copilot panel with 10 suggestions

---

## 2.9 n8n + Zie619 Workflow

```bash
# Install n8n globally
npm install -g n8n

# Run n8n
n8n start
# Opens at http://localhost:5678

# Clone Zie619 templates
git clone https://github.com/Zie619/n8n-workflows ~/Desktop/zie619-workflows

# In n8n UI: Settings → Import Workflow → paste from zie619 folder
# Look for: webhook templates, HTTP request chains, polling loops
```

**Build this specific workflow in n8n:**
```
Webhook: POST /webhook/new-document
    → HTTP Request: POST localhost:8000/api/analyze
    → Wait 5 seconds
    → HTTP Request: GET localhost:8000/api/status
    → IF status = "complete":
        → HTTP Request: POST localhost:8000/api/reports
        → (Optional) Send email notification
    → ELSE: Loop back to Wait
```

---

## 2.10 Google Colab — Test Your AI Brain (Free GPU)

```python
# Paste this entire cell into a new Colab notebook to test
# your analysis engine before deploying

# ── Install packages in Colab ─────────────────────────────
!pip install google-generativeai pdfplumber chromadb sentence-transformers

# ── Set your API key ──────────────────────────────────────
import os
os.environ["GEMINI_API_KEY"] = "YOUR_KEY_HERE"  # Paste key directly in Colab

# ── Test the core revenue gap formula ────────────────────
def revenue_gap(approved_arr, actual_revenue):
    gap = approved_arr - actual_revenue
    outcome = "GAP" if gap > 0 else "SURPLUS"
    anomaly = gap > 64.72 or gap < -280.42
    return {"gap": round(gap, 4), "outcome": outcome, "anomaly": anomaly}

# Test with known Infopark 2024-25 values
result = revenue_gap(approved_arr=315.80, actual_revenue=251.08)
print(result)
# Expected: {'gap': 64.72, 'outcome': 'GAP', 'anomaly': False} ✅

# ── Test Gemini connection ────────────────────────────────
import google.generativeai as genai
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content("Is Section 3(1) electricity duty allowed in KSERC truing-up?")
print(response.text)
```

---

## 2.11 The Perennial Rejection Hardcodes
## Never Changes. Never Negotiates. Always ₹0.

```python
# This dictionary is the law. It never changes without a new KSERC regulation.
PERENNIAL_REJECTIONS = {
    "section_3_1_electricity_duty": {
        "patterns"      : ["section 3(1)", "section 3 (1)", "electricity duty u/s", "3(1) duty"],
        "approved"      : 0.0,
        "reason"        : "Section 3(1) Electricity Duty is not allowable in ARR computation.",
        "regulation"    : "Consistent KSERC precedent across all truing-up orders",
        "exceptions"    : None  # No exceptions. Ever.
    },
    "csr_expenses": {
        "patterns"      : ["csr", "corporate social responsibility", "community development"],
        "approved"      : 0.0,
        "reason"        : "CSR is an appropriation of profit, not a cost of electricity distribution.",
        "regulation"    : "Rejected in KPUPL 2023-24 and consistent prior orders",
        "exceptions"    : None  # No exceptions. Ever.
    },
    "rpo_provisions": {
        "patterns"      : ["rpo provision", "rpo liability", "renewable purchase obligation provision"],
        "approved"      : 0.0,
        "reason"        : "Only actual REC payments are allowed. Provisions are not.",
        "regulation"    : "KSERC Renewable Purchase Obligation Regulations",
        "exceptions"    : "Actual REC payments (not provisions) may be approved"
    }
}
```

---

## 2.12 The Self-Learning Loop Implementation

```python
# backend/app/services/learning_loop.py
# ─────────────────────────────────────────────────────────
# Every time a FINAL approved order is created, this function
# adds it to ChromaDB so future analyses can learn from it.
# This is how the system gets smarter with every order.
# ─────────────────────────────────────────────────────────

import chromadb                            # Local vector database
from sentence_transformers import SentenceTransformer  # Free local embeddings

# Load the embedding model once (downloads ~90MB first time)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Connect to ChromaDB (creates a persistent local database)
chroma_client = chromadb.PersistentClient(path="./chroma_knowledge_base")
orders_collection = chroma_client.get_or_create_collection("kserc_orders")

def add_order_to_knowledge_base(order_text: str, licensee: str,
                                  year: str, outcome: str) -> bool:
    """
    Called every time KSERC staff finalizes an order.
    Embeds the order text and stores in ChromaDB.
    Future AI analyses will retrieve this as a precedent.
    """
    # Create a unique ID for this order
    order_id = f"{licensee.lower().replace(' ', '_')}_{year}"

    # Convert the order text to a numerical embedding vector
    embedding = embedding_model.encode(order_text).tolist()

    # Store in ChromaDB with metadata for filtering
    orders_collection.add(
        ids=[order_id],                   # Unique identifier
        embeddings=[embedding],           # Numerical representation
        documents=[order_text],           # Original text for retrieval
        metadatas=[{                      # Metadata for filtered search
            "licensee": licensee,
            "year": year,
            "outcome": outcome
        }]
    )
    return True  # Confirm successful storage

def retrieve_similar_precedents(query: str, n_results: int = 3) -> list:
    """
    Given a query (e.g., "employee cost normative cap Infopark"),
    finds the most similar past KSERC orders.
    Used by the AI to ground its reasoning in real precedents.
    """
    # Convert query to embedding for similarity search
    query_embedding = embedding_model.encode(query).tolist()

    # Search ChromaDB for the most similar stored orders
    results = orders_collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results               # Return top N matches
    )
    # Return the matching order texts for the AI to read
    return results["documents"][0] if results["documents"] else []
```

---

## Summary: Your Complete Tool Chain in Execution Order

```
1. antigravity.dev   → Sketch the UI layout visually
2. v0.dev            → Convert layout to React + Tailwind code
3. Supabase          → Create database (run SQL from Section 2.4)
4. AI Studio         → Get Gemini API key + test system prompt
5. Colab             → Test all Python formulas (Section 2.10)
6. GitHub            → Init repo, push code, enable Copilot
7. Google ADK        → Build the agent tools (Section 2.6)
8. Rowboat           → Wire up parallel agents (Section 2.7)
9. Stitch            → Connect any CSV/Sheet data → Supabase
10. Zie619 + n8n     → Clone closest workflow template → adapt
11. Ollama           → Pull Mistral for production confidential data
12. chef.convex      → Add only if you want real-time collaboration
```

---
*Feed this entire document to every AI coding assistant at the start of each session.*
*The formulas are the ground truth. The architecture is the map. Build.*
