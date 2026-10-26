# KSERC AI Truing-Up Tool — API Contract / Interface Spec
> **Base URL:** `http://localhost:8000/api/v1` (development)  
> **Authentication:** Bearer JWT token in `Authorization` header  
> **Financial unit:** ₹ Lakh (numeric values), display formatted in UI.

---

## 0. LLM Provider & AI Routing (NEW)

The backend supports pluggable AI providers. All AI calls MUST be initiated by the backend (not the frontend) to preserve:
- confidentiality (Work Order Clause 5)
- audit trail
- consistent deterministic rule application

### Supported Providers
- `gemini` (Google AI Studio — prototype)
- `deepseek` (API — cost-effective)
- `grok` (API — if available)
- `ollama` (local — production confidential mode)
- `none` (rule-engine only fallback)

### Provider Selection Priority
Default behavior:
1. Use `provider_preference` if supplied.
2. Else use server default `AI_PROVIDER` from environment.
3. If provider fails/rate-limits → fall back to `none` (rule-engine only), never block analysis.

---

## 1. Authentication

### POST /auth/login
(unchanged)

---

## 2. Licensees

### GET /licensees
(unchanged)

---

## 3. Analysis Sessions

### POST /sessions
Create a new truing-up analysis session.

**Request:**
```json
{
  "licensee_id": 3,
  "financial_year": "2024-25",
  "ai_config": {
    "provider_preference": "deepseek",
    "allow_external_ai": true,
    "temperature": 0.1
  }
}
```

**Notes**
- `ai_config` is optional.
- `allow_external_ai=false` forces `ollama` or `none` only.

**Response 201 Created:**
```json
{
  "session_id": 42,
  "licensee": "Infoparks Kerala",
  "financial_year": "2024-25",
  "status": "pending",
  "created_at": "2026-01-28T10:30:00Z",
  "ai_config_effective": {
    "provider": "deepseek",
    "temperature": 0.1,
    "fallback_used": false
  }
}
```

### GET /sessions
(unchanged; add optional `ai_provider` field per session if you want)

### GET /sessions/{session_id}
(unchanged; add optional `ai_provider` + `fallback_used`)

---

## 4. Document Upload

### POST /sessions/{session_id}/documents
(unchanged)

---

## 5. Analysis Engine

### POST /sessions/{session_id}/analyze
Trigger analysis for a session (async).

**Request (optional override):**
```json
{
  "ai_config": {
    "provider_preference": "grok",
    "allow_external_ai": true,
    "temperature": 0.1
  }
}
```

**Response 202 Accepted:**
```json
{
  "session_id": 42,
  "status": "ingesting",
  "message": "Analysis started. Poll /sessions/42/status for progress.",
  "estimated_duration_seconds": 120,
  "ai_config_effective": {
    "provider": "grok",
    "temperature": 0.1
  }
}
```

### GET /sessions/{session_id}/status
Add AI metadata + fallback visibility.

**Response 200 OK:**
```json
{
  "session_id": 42,
  "status": "analyzing",
  "progress_pct": 70,
  "current_step": "Running prudence checks on cost elements",
  "ai_runtime": {
    "provider": "grok",
    "fallback_used": false,
    "last_error": null
  },
  "steps_completed": [
    "Document ingestion complete",
    "Financial data extracted",
    "Revenue gap computed: ₹64.72 Lakh"
  ],
  "steps_pending": [
    "Normative O&M check",
    "Generating reasoning report"
  ]
}
```

---

## 6. Analysis Results

### GET /sessions/{session_id}/results
Add model provenance for audit.

**Response 200 OK:**
```json
{
  "session_id": 42,
  "licensee": "Infoparks Kerala",
  "financial_year": "2024-25",
  "ai_provenance": {
    "provider": "grok",
    "model": "grok-<version>",
    "temperature": 0.1,
    "fallback_used": false
  },
  "summary": {
    "claimed_gap_lakhs": -79.76,
    "ai_recommended_gap_lakhs": -64.72,
    "commission_approved_lakhs": null,
    "outcome": "gap"
  },
  "line_items": [
    {
      "id": 202,
      "item_name": "Employee Cost",
      "item_category": "om_cost",
      "claimed_amount": 12.30,
      "normative_cap": 11.80,
      "ai_recommended": 11.80,
      "staff_approved": null,
      "validation_status": "flagged",
      "regulatory_reference": "KSERC Tariff Regulations 2021, Reg. 12(3) — O&M normative cap",
      "reasoning_summary": "Claimed ₹12.30L exceeds normative ₹11.80L (prev year ₹11.32L × AICPI 1.042). Excess ₹0.50L disallowed.",
      "reasoning_source": {
        "type": "hybrid",
        "deterministic_rules_applied": true,
        "llm_used": true,
        "provider": "grok"
      }
    }
  ]
}
```

---

## 7. AI Reasoning Detail

### GET /sessions/{session_id}/line-items/{line_item_id}/reasoning
Add citations verification status.

**Response 200 OK:**
```json
{
  "line_item_id": 202,
  "item_name": "Employee Cost",
  "reasoning_chain": [
    {
      "step": 1,
      "action": "Regulation Lookup",
      "retrieved_text": "Regulation 12(3) ...",
      "source": "KSERC Tariff Regulations 2021",
      "citation_verified": true
    }
  ],
  "confidence_score": 0.96,
  "ai_runtime": {
    "provider": "grok",
    "model": "grok-<version>",
    "fallback_used": false
  }
}
```

---

## 8. Staff Review (Human Override)

### PATCH /sessions/{session_id}/line-items/{line_item_id}
(unchanged)

---

## 9. Reports
(unchanged)

---

## 10. Historical Data
(unchanged)

---

## 11. Error Response Format
(unchanged)
