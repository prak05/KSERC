# Version Timeline

Every stage of the KSERC truing-up tool is preserved as its own branch. `main` is the current build.

| # | Branch | Period | What it is |
|---|---|---|---|
| 0 | [`Ex`](../../tree/Ex) | Feb 2026 | The first KSERC repo: FastAPI + worker, Cloudflare/Vercel deploy. |
| 1 | [`v1-python-prototype`](../../tree/v1-python-prototype) | Feb 20 – Mar 4 | Python multi-agent prototype: LangGraph, Vertex AI, Chroma RAG, React/Vite front end. |
| 2 | [`v2-ai-studio-ui-prototype`](../../tree/v2-ai-studio-ui-prototype) | Mar 1 | UI prototype: dashboard, knowledge base, rules server, SQLite history, quick calculator, benchmarks. |
| 3 | [`v3-nextjs-langgraph`](../../tree/v3-nextjs-langgraph) | Mar 2 – Mar 27 | Next.js 14 rewrite: LangGraph.js extract → audit → draft, JSON precedent DB, deterministic normative math, LLM fallback chain, OCR chain. |
| 4 | [`v4-merger-nextjs-python-backend`](../../tree/v4-merger-nextjs-python-backend) | Mar 5 – Mar 10 | Both lines merged: Next.js front end over a FastAPI Python backend; login, case history, review flow. |
| 5 | [`v5-production-snapshot-mar06`](../../tree/v5-production-snapshot-mar06) | Mar 6 – Mar 7 | Production snapshot with the Next.js app and the Python engine side by side. |
| 6 | [`v6-nextjs-premium-ui`](../../tree/v6-nextjs-premium-ui) | Mar 8 | Premium UI pass: live audit terminal, RAG search, results dashboard. |
| 7 | [`v7-trueup-engine`](../../tree/v7-trueup-engine) | Mar 5 – Mar 27 | The engine on Google Cloud: FastAPI + 9-node LangGraph, depreciation and interest engines, editable order drafter, generated FY 2024-25 orders. |
| 8 | **`main`** | Oct 2026 | **AWS edition.** Bedrock, Textract, DynamoDB, S3 and ECS Fargate with Terraform; a fully local mode with no keys; Analyst Q&A, case history, Word export, quick calculator and benchmarks merged in from earlier versions; new editorial UI. |
| — | [`docs-research`](../../tree/docs-research) | Feb – Mar | Research reports, PRD and design specs, prompts, NBA handover, sample orders and development logs. |

> Credentials that appeared in early development history were removed before publication.
