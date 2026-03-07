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

-- RAG similarity search function
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
