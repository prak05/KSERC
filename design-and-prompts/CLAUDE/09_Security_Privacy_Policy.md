# KSERC AI Truing-Up Tool — Security & Data Privacy Policy
> **Project:** AI-Based Analytical Tool for Truing Up of Accounts | Work Order No. KSERC/CSO/03-05  
> **Prepared by:** RIET Project Team  
> **Applicable Regulation:** KSERC Work Order Clause 5 — Data and Confidentiality  
> **Version:** 1.0 | Date: 2026

---

## 1. Governing Clause

As per Work Order No. KSERC/CSO/03-05, Clause 5:

> *"Any data shared by the Commission for the purpose of this assignment shall be used strictly for the stated objective only. The institution shall ensure confidentiality of data and shall not disclose or share the same with any third party without prior written approval of the Commission. Appropriate data security measures shall be put in place by the institution."*

This document defines how that obligation is fulfilled in the software system.

---

## 2. Data Classification

| Data Type | Classification | Examples |
|---|---|---|
| Audited Annual Accounts of licensees | **CONFIDENTIAL** | Revenue figures, cost breakdowns |
| Commission-approved ARR orders | **Internal** | Approved costs per licensee |
| Historical truing-up orders | **Internal** (publicly available) | Past surplus/gap figures |
| KSERC staff credentials | **SECRET** | Usernames, password hashes |
| AI reasoning outputs | **Internal** | Analysis reports, recommendations |
| Generated truing-up orders | **CONFIDENTIAL** | Draft order documents |
| KSERC Tariff Regulations | **Public** | Regulation text |

---

## 3. Data Handling Rules

### 3.1 Storage
- All uploaded documents stored only on the designated KSERC/RIET server. Never in third-party cloud storage without Commission approval.
- File paths stored in the database; files stored in `/uploaded_documents/` — outside the web root.
- Generated reports stored in `/generated_reports/` — accessible only via authenticated download API.
- Database encrypted at rest (PostgreSQL encryption enabled in production).

### 3.2 Transmission
- All HTTP traffic encrypted with TLS 1.3 (HTTPS only in production).
- No financial data transmitted over unencrypted channels.
- API responses include `Cache-Control: no-store` headers to prevent browser caching of financial data.

### 3.3 AI API Data Handling
- **Gemini API (Google):** In the prototype phase, document text is sent to the Gemini API for analysis. This means licensee financial data may leave the local server.
- **Action Required:** Before production deployment with real KSERC data, either:
  - Switch to an on-premise SLM (Mistral-7B via Ollama) — no data leaves the server, OR
  - Review and accept Google's data processing terms with Commission approval
- **Prototype Phase Constraint:** Only sample/anonymized data to be used with the Gemini API until formal approval.

### 3.4 Data Retention
- Uploaded documents retained for the duration of the active truing-up case + 90 days.
- After 90 days, documents are automatically deleted from the file system (database records retained for audit).
- Users cannot delete their own uploaded documents (only admins can, with audit log entry).

---

## 4. Access Control

### 4.1 Role-Based Access
| Role | Permissions |
|---|---|
| **analyst** | Upload documents, trigger analysis, view results, add review notes |
| **senior_analyst** | All analyst + override AI recommendations, flag for escalation |
| **commissioner** | All senior_analyst + finalize & approve reports, access all sessions |
| **admin** | User management, system settings, view audit logs |

### 4.2 Session Security
- JWT tokens expire after 8 hours (one work day).
- Failed login attempts: lock account after 5 consecutive failures. Admin must unlock.
- Concurrent sessions: a user can only have 1 active session at a time (new login invalidates old token).
- All logins and logouts logged in `audit_log` table with IP address and timestamp.

### 4.3 API Security
- All API endpoints require valid JWT except `/auth/login`.
- Role checked on every protected endpoint (not just at login).
- Sensitive endpoints (finalize report, user management) require `commissioner` or `admin` role.

---

## 5. Audit Trail

Every significant action is logged in the `audit_log` database table:

| Event | Logged |
|---|---|
| User login / logout | ✅ |
| Document upload | ✅ (filename, size, uploader, timestamp) |
| Analysis triggered | ✅ |
| AI recommendation viewed | ✅ |
| Staff override of AI recommendation | ✅ (old value, new value, reason, staff ID) |
| Report generated | ✅ |
| Report marked as final | ✅ |
| User account created/modified | ✅ |
| Document deleted | ✅ |

The audit log is **append-only** — no records can be modified or deleted. Only admins can read audit logs.

---

## 6. What Data Is Sent to External APIs

| External Service | Data Sent | Purpose | Prototype / Production |
|---|---|---|---|
| Google Gemini API | Extracted text from financial documents | AI reasoning | Prototype only (sample data). Production: switch to on-premise model. |
| ChromaDB (local) | Document embeddings | Vector search | Local only. No external transmission. |
| sentence-transformers (local) | Document text | Generate embeddings | Local only. No external transmission. |

---

## 7. Prohibited Actions (System-Level Enforcements)

1. **No sharing of uploaded documents via URL.** File download requires authentication.
2. **No export of raw database dump** through the user interface.
3. **No user can view another user's sessions** unless they are Commissioner or Admin role.
4. **No copy of real KSERC data** to be stored on developer machines. Use sample data for development.
5. **The application must not send error details** (stack traces, SQL queries) to the browser. Log errors server-side only.

---

## 8. Vulnerability Management

### Input Validation
- All API inputs validated with Pydantic schemas before processing.
- File type validated by reading the file header (magic bytes), not just the file extension.
- File names sanitized before storage — original name stored in DB, server-assigned name used on disk.

### Dependency Security
- `pip-audit` run monthly to check for known vulnerabilities in Python dependencies.
- `npm audit` run monthly for frontend dependencies.
- No dependency pinned to a version with a known CVE.

### Security Headers (HTTP)
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
Cache-Control: no-store (on all API responses)
```

---

## 9. Incident Response

If a data breach or unauthorized access is suspected:

1. **Immediately notify** the KSERC Point of Contact (PoC) designated under Work Order Clause 7.
2. **Disable** the affected user account(s) immediately.
3. **Preserve** the audit log — do not delete or modify any logs.
4. **Document** what data may have been accessed and by whom.
5. **Report** a formal incident report to KSERC within 24 hours.

---

## 10. Developer Obligations (RIET Team)

| Obligation | Implementation |
|---|---|
| Don't use real data for testing | Use sample/anonymized data only in development |
| Don't store credentials in code | All secrets in `.env` file, never committed to Git |
| Don't share KSERC documents outside the project | Treat all KSERC-provided materials as confidential |
| Don't deploy without HTTPS | Enforce HTTPS in production Nginx config |
| Review access logs monthly | Admin reviews audit_log for suspicious activity |
