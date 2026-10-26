# API Reference

All routes are served by `app.py` under `/api`. The React UI is served from `/` by the same process.

## Analysis

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/analyze` | Upload petition PDFs and start an analysis. `multipart/form-data`: `files[]`, `licensee` (`Technopark` \| `Infopark` \| `CSEZA` \| `KDHP`), `financial_year`, optional rates (`inflation_rate`, `iwc_interest_rate`, `sbi_eblr_rate`, `sbi_retail_td_rate`, `supply_code_sd_rate`, `bee_energy_audit_fee`, `norm_loan_opening`, `sd_balance`, `cumulative_gap`). Returns `{analysis_id}`. |
| `GET` | `/api/status/{id}` | `{status, result, progress}` — `status` is `RUNNING`, `PENDING_RM_REVIEW`, `COMPLETED` or `FAILED`. Poll every few seconds. |
| `POST` | `/api/rm-continue` | Resume after the R&M review pause: `{analysis_id, selected_items}` (items allowed as one-time expenditure under Reg. 80(3)). |
| `POST` | `/api/rm-onetime` | Re-apply a one-time R&M selection to a completed analysis: `{analysis_id, selected_indices[], manual_items?[{description, amount}]}`. |
| `POST` | `/api/override` | Officer override of one component: `{analysis_id, component_key, new_approved_amount, justification, user_id?}`. |
| `GET` | `/api/analyses` | Case history, newest first: `{analyses: [{analysis_id, licensee, financial_year, status, updated_at}]}`. |

## Orders

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/hearing-data` | Save court-hearing details used in the order: `{analysis_id, hearing_date, licensee_submissions[], respondent_position, commission_observations}`. |
| `POST` | `/api/generate-order` | Draft the truing-up order: `{analysis_id, order_json?}` (pass edited `order_json` to regenerate). Returns `{pdf_url, html, order_json, analysis_id}`. |
| `POST` | `/api/finalize-pdf` | Render edited order HTML to PDF: `{analysis_id, html}`. |
| `GET` | `/api/download/{id}` | Download the order PDF. |
| `GET` | `/api/export-docx/{id}` | Download the order as an editable Word document. |

## Regulations and the Analyst

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/regulations` | Regulation documents in the corpus: `{docs: [{doc_id, filename, category, chars, method, extracted_at}], count}`. |
| `POST` | `/api/regulations/upload` | Add a PDF to the corpus (`file`, `category`). Scanned PDFs are read by the model. |
| `DELETE` | `/api/regulations/{doc_id}` | Remove a document from the corpus. |
| `POST` | `/api/ask` | Analyst Q&A grounded in the corpus: `{question}` → `{answer, sources[]}`. |

## Reference data

| Method | Path | Purpose |
|---|---|---|
| `GET` / `POST` | `/api/reference/economic-indicators` | CPI, WPI, SBI PLR and related indices by financial year. |
| `GET` / `POST` | `/api/reference/rates/{fy}` | Interest and deposit rates for a financial year. |
| `POST` | `/api/reference/orders/extract` | Extract approved figures from a past truing-up order PDF (preview). |
| `POST` | `/api/reference/orders/confirm` | Save the reviewed extraction as precedent. |
| `GET` | `/api/reference/orders` | Stored reference orders. |
| `GET` | `/api/reference/myt-baselines` | MYT baseline norms per licensee and year. |

## Service

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | `{status, service, cloud, llm_provider}` — used by the load balancer health check. |
