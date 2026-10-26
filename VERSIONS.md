# KSERC AI Truing-Up Tool — Version Timeline

Automating the Kerala State Electricity Regulatory Commission's truing-up review: ingest a licensee's petition, extract the cost heads, check them against the regulations and MYT norms with deterministic formulas, and draft the Commission's order.

Every stage of the build is preserved as its own branch.

| # | Branch | Period | What it is |
|---|---|---|---|
| 0 | [`Ex`](../../tree/Ex) | Feb 2026 | The first KSERC repo: FastAPI + worker, Cloudflare/Vercel deploy. |
| 1 | [`v1-adwaith-python-prototype`](../../tree/v1-adwaith-python-prototype) | Feb 20 – Mar 4 | Python multi-agent prototype (LangGraph, Vertex AI, Chroma RAG), React/Vite front end. Built by Adwaith A Kumar. |
| 2 | [`v2-ai-studio-ui-prototype`](../../tree/v2-ai-studio-ui-prototype) | Mar 1 | Google AI Studio UI prototype: dashboard, knowledge base, rules server on `:6969`, SQLite history, quick calculator, benchmarks. |
| 3 | [`v3-nextjs-langgraph`](../../tree/v3-nextjs-langgraph) | Mar 2 – Mar 27 | Next.js 14 rewrite: LangGraph.js extract→audit→draft, JSON precedent DB, deterministic normative math, Groq/OpenRouter LLM fallback, OCR chain. |
| 4 | [`v4-merger-nextjs-python-backend`](../../tree/v4-merger-nextjs-python-backend) | Mar 5 – Mar 10 | Merger of both lines: Next.js front end proxying a FastAPI Python backend; login, case history, review flow. |
| 5 | [`v5-production-snapshot-mar06`](../../tree/v5-production-snapshot-mar06) | Mar 6 – Mar 7 | Production snapshot holding the Next.js v4/v5 app and the Python engine side by side. |
| 6 | [`v6-nextjs-premium-ui`](../../tree/v6-nextjs-premium-ui) | Mar 8 | Premium UI pass: live AuditTerminal, RAG search over regulations, results dashboard. |
| 7 | [`v7-trueup-engine`](../../tree/v7-trueup-engine) | Mar 5 – Mar 27 | The final engine: FastAPI + 9-node LangGraph (extract, deep-extract, MYT norms, anomaly detection, audit, review, draft, clarification, validation), depreciation and interest engines, editable order drafter with court-hearing support, ~94 tests, generated FY 2024-25 orders. 40-commit history by Adwaith A Kumar plus the final government-portal reskin. |
| — | [`docs-research`](../../tree/docs-research) | Feb – Mar | Research reports, PRD and design specs, prompts, NBA handover, sample orders and development logs. |

## Credits
- **Prakhar Sharma (prak05)** — product, Next.js line, UI, integration.
- **Adwaith A Kumar** — Python multi-agent engine (v1, v7 history).

> Credentials that appeared in early development history were removed before publication.
