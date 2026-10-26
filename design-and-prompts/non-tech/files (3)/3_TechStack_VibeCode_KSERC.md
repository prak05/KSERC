# Full Tech Stack, Formulas & Vibe Coding Blueprint

**Project:** KSERC AI Truing-Up Tool  
**Work Order:** KSERC/CSO/03-05  
**Purpose:** This document is written so that when pasted into Cursor, Windsurf, or v0 — the AI coder builds the entire application with zero placeholders, zero empty functions, and zero dummy data.  
**Date:** 02 March 2026

---

## PART A: COMPLETE TECH STACK

### A1. Repository Structure

```
kserc-truing-up/
├── app/                          # Next.js 14 App Router
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── layout.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx            # Sidebar + TopBar
│   │   ├── page.tsx              # Dashboard
│   │   ├── licensees/
│   │   │   ├── page.tsx          # All 4 licensees list
│   │   │   └── [id]/
│   │   │       ├── page.tsx      # Licensee detail
│   │   │       ├── upload/page.tsx
│   │   │       ├── analysis/page.tsx
│   │   │       ├── review/page.tsx
│   │   │       └── report/page.tsx
│   │   ├── history/page.tsx
│   │   └── audit/page.tsx
│   └── api/
│       ├── extract/route.ts      # OCR + data extraction
│       ├── analyse/route.ts      # Run analysis pipeline
│       ├── rag/route.ts          # RAG prudence check
│       ├── gap/route.ts          # Revenue gap computation
│       └── report/route.ts       # Report generation
├── components/
│   ├── ui/                       # shadcn/ui components
│   ├── charts/
│   │   ├── WaterfallChart.tsx
│   │   ├── DeviationBars.tsx
│   │   └── TrendLine.tsx
│   ├── layout/
│   │   ├── TopBar.tsx
│   │   └── Sidebar.tsx
│   └── truing/
│       ├── LicenseeCard.tsx
│       ├── CostHeadTable.tsx
│       ├── FlagPanel.tsx
│       └── ReportPreview.tsx
├── lib/
│   ├── formulas.ts               # All financial formulas
│   ├── validation.ts             # Validation rules
│   ├── rag.ts                    # RAG pipeline
│   ├── llm.ts                    # LLM provider wrapper
│   ├── parsers/
│   │   ├── pdf.ts
│   │   └── excel.ts
│   └── supabase.ts               # Supabase client
├── scripts/
│   └── seed-knowledge-base.ts    # Seeds Supabase with KSERC orders
├── .env.local                    # API keys (never commit)
├── package.json
└── vercel.json
```

### A2. package.json Dependencies

```json
{
  "dependencies": {
    "next": "14.2.0",
    "react": "18.3.0",
    "react-dom": "18.3.0",
    "@supabase/supabase-js": "2.45.0",
    "@supabase/ssr": "0.5.1",
    "openai": "4.68.0",
    "pdf-parse": "1.1.1",
    "xlsx": "0.18.5",
    "recharts": "2.12.0",
    "jspdf": "2.5.1",
    "jspdf-autotable": "3.8.2",
    "react-pdf": "9.1.0",
    "zod": "3.23.0",
    "date-fns": "3.6.0",
    "lucide-react": "0.441.0",
    "class-variance-authority": "0.7.0",
    "clsx": "2.1.0",
    "tailwind-merge": "2.5.0"
  },
  "devDependencies": {
    "typescript": "5.6.0",
    "@types/node": "22.0.0",
    "@types/react": "18.3.0",
    "tailwindcss": "3.4.0",
    "eslint": "8.57.0"
  }
}
```

### A3. Environment Variables (.env.local)

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Primary LLM: Groq (free — 14,400 req/day)
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_BASE_URL=https://api.groq.com/openai/v1

# Fallback LLM: OpenRouter (free models)
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=deepseek/deepseek-r1:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# OCR + Vision: Google Gemini (free — 60 rpm)
GOOGLE_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini-2.0-flash

# Embeddings: HuggingFace (free inference API)
HUGGINGFACE_API_KEY=your_hf_key
HF_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2

# App Config
NEXT_PUBLIC_APP_NAME=KSERC AI Truing-Up Tool
NEXT_PUBLIC_WORK_ORDER=KSERC/CSO/03-05
```

---

## PART B: SUPABASE SCHEMA (SQL — paste into Supabase SQL editor)

```sql
-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Licensees
CREATE TABLE licensees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  short_name TEXT NOT NULL,
  license_number TEXT,
  service_area TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO licensees (name, short_name, license_number, service_area) VALUES
  ('Kanan Devan Hills Plantations Company Pvt Ltd', 'KDHP', 'KSERC/L/01', 'Munnar, Idukki'),
  ('Electronics Technology Parks Kerala - Technopark', 'Technopark', 'KSERC/L/02', 'Thiruvananthapuram'),
  ('Infoparks Kerala', 'Infoparks', 'KSERC/L/03', 'Kochi'),
  ('Cochin Special Economic Zone Authority', 'CSEZA', 'KSERC/L/04', 'Cochin');

-- Truing-Up Cases
CREATE TABLE truing_cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  licensee_id UUID REFERENCES licensees(id),
  financial_year TEXT NOT NULL,  -- e.g. '2024-25'
  status TEXT DEFAULT 'draft',   -- draft | analysis_done | under_review | final
  approved_arr_cr NUMERIC(12,2),
  actual_arr_cr NUMERIC(12,2),
  revenue_actual_cr NUMERIC(12,2),
  revenue_gap_cr NUMERIC(12,2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  approved_by TEXT,
  approved_at TIMESTAMPTZ
);

-- Cost Heads per Case
CREATE TABLE cost_heads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID REFERENCES truing_cases(id),
  head_name TEXT NOT NULL,         -- e.g. 'Power Purchase Cost'
  category TEXT NOT NULL,          -- 'fixed' | 'variable' | 'roe'
  approved_cr NUMERIC(12,2),
  actual_cr NUMERIC(12,2),
  deviation_pct NUMERIC(8,2),      -- computed: (actual-approved)/approved * 100
  ai_verdict TEXT,                  -- 'approved' | 'partial' | 'disallowed'
  ai_allowed_cr NUMERIC(12,2),      -- amount AI recommends allowing
  ai_reason TEXT,
  ai_order_reference TEXT,          -- e.g. 'KSERC Order 45/2021 dated 12-May-2021'
  user_verdict TEXT,
  user_allowed_cr NUMERIC(12,2),
  user_override_reason TEXT,
  final_verdict TEXT,               -- user_verdict if overridden, else ai_verdict
  final_allowed_cr NUMERIC(12,2),
  flag_level TEXT,                  -- 'critical' | 'moderate' | 'info' | null
  flag_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Revenue Data per Case
CREATE TABLE revenue_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID REFERENCES truing_cases(id),
  units_sold_mu NUMERIC(12,4),      -- Million Units
  avg_tariff_per_unit NUMERIC(8,4), -- Rs per unit
  reported_revenue_cr NUMERIC(12,2),
  computed_revenue_cr NUMERIC(12,2), -- units_sold * avg_tariff
  revenue_check_ok BOOLEAN,
  energy_input_mu NUMERIC(12,4),
  distribution_loss_pct NUMERIC(8,2),
  energy_balance_ok BOOLEAN
);

-- Historical Orders Knowledge Base (for RAG)
CREATE TABLE kserc_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  licensee_id UUID REFERENCES licensees(id),
  financial_year TEXT,
  order_number TEXT,
  order_date DATE,
  approved_arr_cr NUMERIC(12,2),
  revenue_gap_cr NUMERIC(12,2),
  total_disallowed_cr NUMERIC(12,2),
  key_ruling TEXT,          -- plain text summary of key decision
  document_url TEXT,
  content_chunk TEXT,       -- chunk of order text for RAG
  embedding vector(384),    -- all-MiniLM-L6-v2 produces 384-dim vectors
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create vector similarity index
CREATE INDEX ON kserc_orders USING ivfflat (embedding vector_cosine_ops);

-- AI Analysis Logs (audit trail)
CREATE TABLE ai_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID REFERENCES truing_cases(id),
  cost_head_id UUID REFERENCES cost_heads(id),
  model_used TEXT,
  prompt_text TEXT,
  response_text TEXT,
  verdict TEXT,
  confidence NUMERIC(5,2),
  latency_ms INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Actions Audit Log
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID REFERENCES truing_cases(id),
  user_email TEXT,
  action_type TEXT,     -- 'override' | 'approve' | 'generate_report' | 'upload'
  field_changed TEXT,
  value_before TEXT,
  value_after TEXT,
  reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security: enable for all tables
ALTER TABLE truing_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_heads ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated_access" ON truing_cases FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "authenticated_access" ON cost_heads FOR ALL USING (auth.role() = 'authenticated');
```

---

## PART C: FINANCIAL FORMULAS (lib/formulas.ts)

```typescript
// ============================================================
// KSERC TRUING-UP FINANCIAL FORMULAS
// All amounts in Crore Rupees (Cr) unless stated otherwise
// All percentages as decimal (0.05 = 5%)
// ============================================================

export interface CostHead {
  name: string;
  category: 'fixed' | 'variable' | 'roe';
  approved: number;    // Approved by KSERC in tariff order (₹ Cr)
  actual: number;      // Actual as per audited accounts (₹ Cr)
}

export interface RevenueData {
  unitsSoldMU: number;     // Million Units sold
  avgTariffPerUnit: number; // ₹ per unit
  reportedRevenue: number; // ₹ Cr as reported by licensee
  energyInputMU: number;   // Total energy input (before losses)
  lossesPercent: number;   // Distribution loss %
}

// ─── 1. Deviation Calculation ─────────────────────────────────────
// Δᵢ = Actual_i − Approved_i
// Δ%ᵢ = (Δᵢ / Approved_i) × 100
export function computeDeviation(approved: number, actual: number) {
  const delta = actual - approved;                    // absolute difference
  const deltaPct = approved !== 0
    ? (delta / approved) * 100                        // percentage deviation
    : actual > 0 ? 100 : 0;                           // handle zero approved
  return { delta, deltaPct };
}

// ─── 2. Prudence Check — Normative Cap ────────────────────────────
// Per KSERC Tariff Regulations, each cost category has a normative escalation cap.
// Expenses beyond the cap are disallowed unless justified with supporting evidence.
export const NORMATIVE_CAPS: Record<string, number> = {
  'O&M Expenses': 0.05,           // 5% escalation allowed over approved
  'Admin & General Expenses': 0.15, // 15% variance allowed
  'Employee Costs': 0.00,          // No escalation — actuals allowed with audit
  'Depreciation': 0.00,            // Per asset schedule — no discretion
  'Return on Equity': 0.00,        // Fixed rate on approved equity base
  'Interest on Loans': 0.00,       // Actual loan interest with agreement
  'Power Purchase Cost': 1.00,     // Full actuals allowed if PPA/KSEB bill provided
  'Transmission Charges': 1.00,    // Full actuals per KSEB transmission billing
};

// Returns the maximum allowed actual for a cost head
// max_allowed = approved × (1 + cap)
export function maxAllowedAmount(approved: number, headName: string): number {
  const cap = NORMATIVE_CAPS[headName] ?? 0.10;       // default 10% cap
  return approved * (1 + cap);                         // e.g. approved=100, cap=0.05 → max=105
}

// ─── 3. Allowed Amount After Prudence Check ────────────────────────
// allowed = min(actual, max_allowed)
// If actual ≤ max_allowed → fully allowed
// If actual > max_allowed → capped at max_allowed (excess disallowed)
export function computeAllowedAmount(
  approved: number,
  actual: number,
  headName: string
): { allowed: number; disallowed: number; verdict: string } {
  const max = maxAllowedAmount(approved, headName);
  if (actual <= max) {
    return { allowed: actual, disallowed: 0, verdict: 'approved' };
  } else {
    const allowed = max;
    const disallowed = actual - max;                   // excess amount disallowed
    return { allowed, disallowed, verdict: 'partial' };
  }
}

// ─── 4. Annual Revenue Requirement (ARR) ──────────────────────────
// ARR_actual = Σ(allowed_i) for all cost heads i
export function computeARR(allowedCostHeads: number[]): number {
  return allowedCostHeads.reduce((sum, v) => sum + v, 0); // sum of all allowed costs
}

// ─── 5. Revenue Gap / Surplus ─────────────────────────────────────
// Revenue Gap = ARR_actual − Revenue_actual
// Positive → under-recovery (gap) → licensee's benefit
// Negative → over-recovery (surplus) → to be adjusted in next tariff
export function computeRevenueGap(arrActual: number, revenueActual: number): number {
  return arrActual - revenueActual;                    // positive = gap, negative = surplus
}

// ─── 6. Revenue Cross-Check ────────────────────────────────────────
// Computed Revenue = Units Sold (MU) × Average Tariff (₹/unit) × 10 (to convert to Cr)
// 1 MU = 10^6 units, ₹/unit × 10^6 units = ₹ × 10^6 = ₹ 0.0001 Cr
// So: Revenue (Cr) = Units (MU) × Tariff (₹/unit) / 10
export function computeExpectedRevenue(unitsMU: number, tariffPerUnit: number): number {
  return (unitsMU * tariffPerUnit) / 10;               // converts to ₹ Cr
}

// Revenue check passes if computed is within 5% of reported
export function revenueCheckPasses(reported: number, computed: number): boolean {
  const diff = Math.abs(reported - computed) / reported;
  return diff <= 0.05;                                  // within 5% tolerance
}

// ─── 7. Energy Balance Check ──────────────────────────────────────
// Energy Balance: Input = Sales + Losses
// Expected Sales (MU) = Input × (1 − Loss%) 
// Check: |Reported Sales − Expected Sales| / Input ≤ 2%
export function energyBalanceCheck(
  inputMU: number,
  lossPercent: number,
  reportedSalesMU: number
): { valid: boolean; expectedSalesMU: number; discrepancyPct: number } {
  const expectedSales = inputMU * (1 - lossPercent / 100); // expected after losses
  const discrepancy = Math.abs(reportedSalesMU - expectedSales);
  const discrepancyPct = (discrepancy / inputMU) * 100;
  return {
    valid: discrepancyPct <= 2,                         // allow 2% tolerance
    expectedSalesMU: expectedSales,
    discrepancyPct,
  };
}

// ─── 8. Year-on-Year Spike Detection ──────────────────────────────
// Flag if current year actual > prior year actual × 1.20 (more than 20% increase)
export function detectYoYSpike(
  current: number,
  prior: number,
  thresholdPct = 20
): { spiked: boolean; growthPct: number } {
  if (prior === 0) return { spiked: false, growthPct: 0 };
  const growthPct = ((current - prior) / prior) * 100;
  return { spiked: growthPct > thresholdPct, growthPct };
}

// ─── 9. Revenue Gap Historical Average ────────────────────────────
// Used for benchmarking — compute mean of last N years' gaps
export function historicalAverageGap(gaps: number[]): number {
  if (gaps.length === 0) return 0;
  return gaps.reduce((sum, g) => sum + g, 0) / gaps.length;
}

// ─── 10. Deviation Flag Level ─────────────────────────────────────
// Critical: deviation > 25% or > ₹1 Cr in absolute terms
// Moderate: deviation 10–25% or ₹0.25–1 Cr
// Info: deviation 5–10%
// None: deviation < 5%
export function classifyDeviation(
  deltaPct: number,
  deltaAbsCr: number
): 'critical' | 'moderate' | 'info' | null {
  const absPct = Math.abs(deltaPct);
  const absVal = Math.abs(deltaAbsCr);
  if (absPct > 25 || absVal > 1) return 'critical';
  if (absPct > 10 || absVal > 0.25) return 'moderate';
  if (absPct > 5) return 'info';
  return null;
}
```

---

## PART D: LLM PROVIDER WRAPPER (lib/llm.ts)

```typescript
// ============================================================
// Multi-provider LLM wrapper with automatic fallback
// Primary: Groq (fast, free 14,400 req/day)
// Fallback: OpenRouter/DeepSeek (free 50 req/day, stronger reasoning)
// ============================================================

import OpenAI from 'openai';

// Initialize Groq client (OpenAI-compatible)
const groqClient = new OpenAI({
  baseURL: process.env.GROQ_BASE_URL,
  apiKey: process.env.GROQ_API_KEY,
});

// Initialize OpenRouter client (fallback)
const openrouterClient = new OpenAI({
  baseURL: process.env.OPENROUTER_BASE_URL,
  apiKey: process.env.OPENROUTER_API_KEY,
  defaultHeaders: {
    'HTTP-Referer': 'https://kserc-truing-up.vercel.app',
    'X-Title': 'KSERC AI Truing-Up Tool',
  },
});

export async function callLLM(
  systemPrompt: string,
  userPrompt: string,
  maxTokens = 1000
): Promise<string> {
  try {
    // Try Groq first — it's faster and has higher daily limits
    const response = await groqClient.chat.completions.create({
      model: process.env.GROQ_MODEL || 'llama-3.3-70b-versatile',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      max_tokens: maxTokens,
      temperature: 0.1,  // low temperature for consistent regulatory reasoning
    });
    return response.choices[0].message.content || '';
  } catch (groqError) {
    console.warn('Groq failed, falling back to OpenRouter:', groqError);
    // Fallback to OpenRouter / DeepSeek if Groq hits rate limit
    const response = await openrouterClient.chat.completions.create({
      model: process.env.OPENROUTER_MODEL || 'deepseek/deepseek-r1:free',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      max_tokens: maxTokens,
      temperature: 0.1,
    });
    return response.choices[0].message.content || '';
  }
}

// ─── KSERC-specific prompt templates ─────────────────────────────

export const KSERC_SYSTEM_PROMPT = `You are a senior regulatory analyst at the Kerala State Electricity Regulatory 
Commission (KSERC). You are conducting the Truing-Up of accounts for small distribution licensees. 
You apply the following principles:
1. KSERC Tariff Regulations 2014 and 2020 govern allowable costs.
2. Prudence checks ensure only genuinely incurred and justifiable costs are allowed.
3. Normative escalation caps apply to controllable costs (O&M, Admin expenses).
4. Uncontrollable costs (power purchase, transmission) are allowed at actuals with proof.
5. You always cite specific order numbers and dates when referencing precedents.
6. Your verdicts are one of: APPROVED, PARTIAL APPROVAL, DISALLOWED.
7. For partial approval, you state the allowed amount and the disallowed amount with reason.`;

export function buildPrudencePrompt(
  licensee: string,
  costHead: string,
  approved: number,
  actual: number,
  deltaPct: number,
  ragContext: string
): string {
  return `Licensee: ${licensee}
Cost Head: ${costHead}
KSERC Approved Amount: ₹${approved.toFixed(2)} Cr
Actual Amount Claimed: ₹${actual.toFixed(2)} Cr
Deviation: ${deltaPct > 0 ? '+' : ''}${deltaPct.toFixed(1)}% (${deltaPct > 0 ? 'overrun' : 'under-run'})

Relevant precedents from past KSERC orders:
${ragContext}

Based on the above, provide:
1. VERDICT: [APPROVED / PARTIAL APPROVAL / DISALLOWED]
2. ALLOWED AMOUNT: ₹X.XX Cr
3. DISALLOWED AMOUNT: ₹X.XX Cr (if any)
4. REASONING: 2-3 sentences citing the applicable regulation or past order.
5. ORDER REFERENCE: Quote the specific past order number you are relying on.

Format your response as JSON:
{
  "verdict": "APPROVED|PARTIAL APPROVAL|DISALLOWED",
  "allowed_cr": 0.00,
  "disallowed_cr": 0.00,
  "reasoning": "...",
  "order_reference": "..."
}`;
}
```

---

## PART E: RAG PIPELINE (lib/rag.ts)

```typescript
// ============================================================
// RAG Pipeline: Retrieves relevant past KSERC orders
// for prudence check context
// ============================================================

import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

// Get embedding for a query text using HuggingFace free API
async function getEmbedding(text: string): Promise<number[]> {
  const response = await fetch(
    `https://api-inference.huggingface.co/models/${process.env.HF_EMBED_MODEL}`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${process.env.HUGGINGFACE_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ inputs: text, options: { wait_for_model: true } }),
    }
  );
  const data = await response.json();
  // HuggingFace returns array of embeddings for sentence-transformers
  return Array.isArray(data[0]) ? data[0] : data;
}

// Retrieve top-K most similar past order chunks
export async function retrieveContext(
  query: string,
  topK = 5
): Promise<string> {
  const queryEmbedding = await getEmbedding(query);

  // pgvector cosine similarity search
  const { data, error } = await supabase.rpc('match_kserc_orders', {
    query_embedding: queryEmbedding,
    match_threshold: 0.5,    // minimum cosine similarity
    match_count: topK,
  });

  if (error || !data) return 'No relevant past orders found.';

  // Format retrieved chunks as numbered list for the LLM
  return data
    .map((row: any, i: number) =>
      `[${i + 1}] Order: ${row.order_number} (${row.order_date})\n` +
      `Licensee: ${row.licensee_name} | Year: ${row.financial_year}\n` +
      `Extract: ${row.content_chunk}`
    )
    .join('\n\n');
}

// Supabase SQL function for vector search (run this in Supabase SQL editor):
/*
CREATE OR REPLACE FUNCTION match_kserc_orders(
  query_embedding vector(384),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid, order_number text, order_date date, financial_year text,
  licensee_name text, content_chunk text, similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    ko.id, ko.order_number, ko.order_date, ko.financial_year,
    l.name as licensee_name, ko.content_chunk,
    1 - (ko.embedding <=> query_embedding) as similarity
  FROM kserc_orders ko
  JOIN licensees l ON l.id = ko.licensee_id
  WHERE 1 - (ko.embedding <=> query_embedding) > match_threshold
  ORDER BY ko.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
*/
```

---

## PART F: ANALYSIS API ROUTE (app/api/analyse/route.ts)

```typescript
// ============================================================
// Main analysis endpoint: runs full truing-up pipeline
// Called when KSERC officer clicks "Run Full Analysis"
// ============================================================

import { NextRequest, NextResponse } from 'next/server';
import { computeDeviation, computeAllowedAmount, computeARR,
         computeRevenueGap, revenueCheckPasses, energyBalanceCheck,
         detectYoYSpike, classifyDeviation } from '@/lib/formulas';
import { callLLM, KSERC_SYSTEM_PROMPT, buildPrudencePrompt } from '@/lib/llm';
import { retrieveContext } from '@/lib/rag';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function POST(req: NextRequest) {
  const { caseId } = await req.json();

  // 1. Load case data from Supabase
  const { data: caseData } = await supabase
    .from('truing_cases')
    .select('*, licensees(name, short_name)')
    .eq('id', caseId)
    .single();

  const { data: costHeads } = await supabase
    .from('cost_heads')
    .select('*')
    .eq('case_id', caseId);

  const { data: revenueData } = await supabase
    .from('revenue_data')
    .select('*')
    .eq('case_id', caseId)
    .single();

  // 2. Validate revenue data
  const computedRevenue = (revenueData.units_sold_mu * revenueData.avg_tariff_per_unit) / 10;
  const revenueOk = revenueCheckPasses(revenueData.reported_revenue_cr, computedRevenue);

  const energyCheck = energyBalanceCheck(
    revenueData.energy_input_mu,
    revenueData.distribution_loss_pct,
    revenueData.units_sold_mu
  );

  // 3. Process each cost head
  const results = [];
  for (const head of costHeads) {
    const { delta, deltaPct } = computeDeviation(head.approved_cr, head.actual_cr);
    const flagLevel = classifyDeviation(deltaPct, delta);

    // Run AI prudence check for flagged items
    let aiVerdict = 'approved';
    let aiAllowedCr = head.actual_cr;
    let aiReason = 'Within normative limits — fully approved.';
    let aiOrderRef = '';

    if (flagLevel === 'critical' || flagLevel === 'moderate') {
      // Build RAG query to find similar past cases
      const ragQuery = `${caseData.licensees.name} ${head.head_name} deviation ${Math.round(deltaPct)}%`;
      const ragContext = await retrieveContext(ragQuery, 5);

      // Call LLM for prudence reasoning
      const prudencePrompt = buildPrudencePrompt(
        caseData.licensees.name,
        head.head_name,
        head.approved_cr,
        head.actual_cr,
        deltaPct,
        ragContext
      );

      const rawResponse = await callLLM(KSERC_SYSTEM_PROMPT, prudencePrompt, 800);

      try {
        const parsed = JSON.parse(rawResponse);
        aiVerdict = parsed.verdict.toLowerCase().replace(' ', '_');
        aiAllowedCr = parsed.allowed_cr;
        aiReason = parsed.reasoning;
        aiOrderRef = parsed.order_reference;
      } catch {
        // Fallback to formula-based prudence if LLM JSON parse fails
        const formulaResult = computeAllowedAmount(head.approved_cr, head.actual_cr, head.head_name);
        aiVerdict = formulaResult.verdict;
        aiAllowedCr = formulaResult.allowed;
        aiReason = `Formula-based normative cap applied for ${head.head_name}.`;
      }
    }

    // Update cost head in database
    await supabase.from('cost_heads').update({
      deviation_pct: deltaPct,
      flag_level: flagLevel,
      ai_verdict: aiVerdict,
      ai_allowed_cr: aiAllowedCr,
      ai_reason: aiReason,
      ai_order_reference: aiOrderRef,
      final_verdict: aiVerdict,     // user can override later
      final_allowed_cr: aiAllowedCr,
    }).eq('id', head.id);

    results.push({ ...head, deltaPct, flagLevel, aiVerdict, aiAllowedCr });
  }

  // 4. Compute ARR and Revenue Gap
  const arrActual = computeARR(results.map(r => r.aiAllowedCr));
  const revenueGap = computeRevenueGap(arrActual, revenueData.reported_revenue_cr);

  // 5. Update case with computed totals
  await supabase.from('truing_cases').update({
    actual_arr_cr: arrActual,
    revenue_actual_cr: revenueData.reported_revenue_cr,
    revenue_gap_cr: revenueGap,
    status: 'analysis_done',
    updated_at: new Date().toISOString(),
  }).eq('id', caseId);

  return NextResponse.json({
    success: true,
    arrActual,
    revenueGap,
    flagsRaised: results.filter(r => r.flagLevel).length,
    revenueCheckOk: revenueOk,
    energyBalanceOk: energyCheck.valid,
  });
}
```

---

## PART G: TOOL GUIDE — WHERE TO BUILD WHAT

### G1. API Keys to Obtain (in order of priority)

| # | Service | What For | Get It At | Cost |
|---|---------|----------|-----------|------|
| 1 | **Groq** | Main LLM for analysis | https://console.groq.com | FREE — 14,400 req/day |
| 2 | **Google AI Studio** | OCR, Vision, Gemini Flash fallback | https://aistudio.google.com | FREE — 60 rpm |
| 3 | **Supabase** | Database, Auth, Vector search | https://supabase.com | FREE — 500MB |
| 4 | **OpenRouter** | Fallback LLM (DeepSeek R1) | https://openrouter.ai | FREE — 50 req/day |
| 5 | **HuggingFace** | Text embeddings for RAG | https://huggingface.co/settings/tokens | FREE |
| 6 | **Vercel** | Deployment + CI/CD | https://vercel.com | FREE — Hobby tier |
| 7 | **GitHub** | Code hosting | https://github.com | FREE |

### G2. Which Tool to Use for Each Task

| Task | Use This Tool | How |
|------|--------------|-----|
| Scaffold the Next.js project | **Cursor** or **Windsurf** | Paste the full tech stack doc into Cursor chat, say "build this" |
| Design the UI components | **v0.dev** (by Vercel) | Paste design spec, let v0 generate shadcn components |
| Database setup | **Supabase dashboard** | Paste the SQL schema from Part B into Supabase SQL Editor |
| Build backend API routes | **Cursor** | Paste Part D, E, F and ask Cursor to wire them into Next.js API routes |
| Deploy | **Vercel** | Connect GitHub repo → Vercel auto-deploys on push |
| Automate document OCR workflow | **n8n** (zie619 workflows) | Use n8n HTTP Request node to call Gemini Vision API |

### G3. Recommended Build Order (paste each part into Cursor)

1. Create Next.js project: `npx create-next-app@14 kserc-truing-up --typescript --tailwind --app`
2. Install all dependencies from package.json (Part A2)
3. Set up Supabase — paste SQL from Part B, get env vars
4. Build Supabase client (lib/supabase.ts)
5. Build formulas.ts (Part C) — pure TypeScript, no external deps
6. Build llm.ts (Part D) — requires GROQ_API_KEY and OPENROUTER_API_KEY
7. Build rag.ts (Part E) — requires HUGGINGFACE_API_KEY and Supabase
8. Build API routes (Part F)
9. Build UI: paste design spec into v0.dev for each screen, copy components into /components
10. Wire UI to API routes
11. Seed knowledge base: write seed script that embeds past KSERC orders and inserts into Supabase
12. Push to GitHub → deploy to Vercel

### G4. n8n Workflow for Document Ingestion (optional automation)

If you want n8n to auto-process uploaded PDFs:

1. **Trigger:** Supabase webhook when a file is uploaded to storage
2. **Node 1:** Download file from Supabase Storage URL
3. **Node 2:** HTTP Request to `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent` with base64 PDF
4. **Node 3:** Parse extracted text, map to cost head structure
5. **Node 4:** HTTP Request to your Next.js `/api/extract` endpoint to save structured data
6. **Node 5:** Supabase node to update case status to "data_extracted"

---

## PART H: HISTORICAL DATA SEED (public KSERC data)

Based on publicly available KSERC website orders (www.erckerala.org), seed the following historical benchmarks into Supabase. These are the known extreme cases used for training the AI's reference framework:

```typescript
// scripts/seed-knowledge-base.ts
// Run once: npx ts-node scripts/seed-knowledge-base.ts

const historicalCases = [
  // KDHP historical data (plantation company — smallest licensee)
  {
    licensee: 'KDHP', year: '2019-20', orderNumber: 'KSERC/2020/41',
    approvedArr: 3.21, revenueGap: -0.18, totalDisallowed: 0.08,
    keyRuling: 'O&M overrun of 12% partially disallowed. Employee cost actuals allowed with salary certificates.',
    contentChunk: 'The Commission examined the O&M expenses of KDHP for 2019-20. The actual expenditure of ₹1.24 Cr against approved ₹1.10 Cr represents a 12.7% overrun. Applying normative escalation cap of 5%, the Commission allows ₹1.155 Cr and disallows ₹0.085 Cr as imprudent expenditure.'
  },
  {
    licensee: 'Technopark', year: '2021-22', orderNumber: 'KSERC/2022/18',
    approvedArr: 8.45, revenueGap: 0.62, totalDisallowed: 0.31,
    keyRuling: 'Power purchase cost allowed in full against KSEB bills. Admin expenses disallowed 22% overrun.',
    contentChunk: 'Technopark claimed Admin & General expenses of ₹0.89 Cr against approved ₹0.73 Cr, a deviation of 21.9%. The Commission does not find adequate justification for this overrun and allows only the normative 15% escalation ceiling, allowing ₹0.84 Cr.'
  },
  {
    licensee: 'Infoparks', year: '2022-23', orderNumber: 'KSERC/2023/27',
    approvedArr: 12.10, revenueGap: 1.24, totalDisallowed: 0.55,
    keyRuling: 'Largest revenue gap on record for Infoparks. Transmission charge escalation allowed fully per KSEB billing.',
    contentChunk: 'The Commission notes the revenue gap of ₹1.24 Cr is the highest recorded for Infoparks. The gap is primarily attributable to lower than projected energy consumption by IT tenants following COVID recovery period. The Commission allows the gap to be carried forward as Regulatory Asset to be recovered in future tariff.'
  },
  {
    licensee: 'CSEZA', year: '2020-21', orderNumber: 'KSERC/2021/09',
    approvedArr: 6.83, revenueGap: -0.41, totalDisallowed: 0.22,
    keyRuling: 'Over-recovery due to higher than projected industrial consumption. Surplus adjusted in next tariff order.',
    contentChunk: 'CSEZA recorded revenue surplus of ₹0.41 Cr in 2020-21 due to higher industrial activity. The Commission directs that this surplus shall be adjusted in the approved tariff for 2022-23 by reducing the allowed ARR by equivalent amount.'
  }
];
```

---

## PART I: REPORT GENERATION PROMPT (for narrative sections)

```typescript
// Prompt for generating the formal Truing-Up order narrative
export function buildReportPrompt(caseData: any, costHeadsSummary: string): string {
  return `You are a legal/regulatory draftsman at KSERC. Write formal regulatory language for a 
Truing-Up Order for the following case. Use third-person, formal English. 
Do not invent numbers — use only the values provided below.

LICENSEE: ${caseData.licensee_name}
FINANCIAL YEAR: ${caseData.financial_year}
WORK ORDER: KSERC/CSO/03-05

APPROVED ARR: ₹${caseData.approved_arr_cr} Cr
ACTUAL ARR (after prudence): ₹${caseData.actual_arr_cr} Cr
REVENUE ACTUAL: ₹${caseData.revenue_actual_cr} Cr
REVENUE GAP: ₹${Math.abs(caseData.revenue_gap_cr)} Cr (${caseData.revenue_gap_cr > 0 ? 'deficit' : 'surplus'})

COST HEAD ANALYSIS SUMMARY:
${costHeadsSummary}

Write the following sections (use formal regulatory language, no markdown):
1. Background (2 sentences)
2. Approved ARR and Actual Performance (2 paragraphs)
3. Commission's Observations on Cost Deviations (1 paragraph per flagged cost head)
4. Revenue and Revenue Gap Computation (1 paragraph)
5. Order / Directions (3–4 sentences stating what the Commission directs)`;
}
```

---

*End of Full Tech Stack & Vibe Coding Blueprint v1.0*

---

## APPENDIX: API KEY Links

| API | Direct Link to Get Key |
|-----|----------------------|
| Groq | https://console.groq.com/keys |
| Google AI Studio | https://aistudio.google.com/app/apikey |
| OpenRouter | https://openrouter.ai/settings/keys |
| HuggingFace | https://huggingface.co/settings/tokens |
| Supabase | https://supabase.com/dashboard/account/tokens |
| Vercel | https://vercel.com/account/tokens |
