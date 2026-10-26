# KSERC AI Truing-Up Tool — Edge Case Checklist
> **Project:** AI-Based Analytical Tool for Truing Up of Accounts | Work Order No. KSERC/CSO/03-05  
> **Purpose:** Force the AI coding assistant to handle every non-happy-path scenario.  
> **Version:** 1.0 | Date: 2026

---

## How to Use This Checklist
When building any feature, explicitly prompt the AI with relevant edge cases from this list.  
Example: *"Build the upload feature. Also handle edge cases #U1, #U2, and #U3 from the Edge Case Checklist."*

---

## Category 1: Document Upload Edge Cases

| # | Edge Case | Expected Behavior | Test Input |
|---|---|---|---|
| U1 | User uploads a **non-PDF/Excel file** (e.g., .jpg, .docx) | Show error: "Invalid file type. Only PDF and Excel files are accepted." Reject the upload. | Upload a `.jpg` image |
| U2 | User uploads a **corrupted PDF** that cannot be parsed | Show error: "Document could not be read. Please upload a valid, non-password-protected PDF." | Upload a truncated PDF file |
| U3 | User uploads a **password-protected PDF** | Detect and show: "This PDF is password-protected. Please provide an unlocked version." | Password-locked PDF |
| U4 | User uploads the **same document type twice** in one session | Ask: "An Annual Accounts document already exists. Replace it?" (Yes/No dialog) | Upload annual_accounts twice |
| U5 | User uploads a file **larger than 50MB** | Reject immediately: "File exceeds 50MB limit. Please compress or split the document." | Upload a 60MB file |
| U6 | User uploads a PDF with **scanned images only** (no text layer) | Flag: "Document appears to be a scanned image. Text extraction may be incomplete. AI confidence may be lower." Proceed with best effort. | Scanned (image-only) PDF |
| U7 | User **cancels mid-upload** | Clean up partial file. Do not create a database record for incomplete upload. | Cancel after 50% upload |
| U8 | Network **disconnects during upload** | Retry up to 3 times. Show progress. If all retries fail, show actionable error. | Simulate network drop |

---

## Category 2: Data Extraction Edge Cases

| # | Edge Case | Expected Behavior | Test Input |
|---|---|---|---|
| E1 | **Missing mandatory column** in financial table (e.g., no "Employee Cost" row) | Flag the gap: "Employee Cost not found in uploaded accounts. Analysis for this item cannot proceed. Staff input required." | PDF without employee cost table |
| E2 | **Indian number format** in PDFs (e.g., "1,23,456.78" instead of "123,456.78") | Parse correctly. `1,23,456.78 → 123456.78`. Never misinterpret as 1.23 | Include amounts like "12,34,567.89" |
| E3 | Financial values expressed in **different units** (Crores vs Lakhs in same document) | Detect unit, convert to Lakhs. Flag unit mismatch with warning. | Mix Crore and Lakh values in same PDF |
| E4 | **Negative values** displayed in brackets (common accounting format: "(12.50)" = -12.50) | Parse `(12.50)` as `-12.50`. | Bracketed negative numbers |
| E5 | **Typo in document** (e.g., "Employe Cost" instead of "Employee Cost") | Use fuzzy matching (≥80% similarity) to map to known line items. Log the mapping made. | Misspelled column headers |
| E6 | **Blank or zero values** in a line item | Treat as ₹0, not as missing. Do not throw an error. Log "₹0 claimed for [item]." | Empty cells in table |
| E7 | PDF table **spanning multiple pages** | Merge correctly. The last row of page N and first row of page N+1 must not be double-counted. | Multi-page tables |
| E8 | **Multiple tables with same heading** in one PDF (e.g., two "Summary" tables) | Use the table nearest to the section heading "Truing Up" or "Annual Accounts". Log which table was used. | Duplicate table headings |

---

## Category 3: Calculation & Logic Edge Cases

| # | Edge Case | Expected Behavior | Test Input |
|---|---|---|---|
| C1 | **Revenue Surplus** (licensee collected MORE than approved ARR) | Compute correctly. Show as negative gap. Display green "SURPLUS" badge. Do not show an error. | actual_revenue > approved_arr |
| C2 | **Zero claimed amount** for a line item that usually has value | Flag: "₹0 claimed for [item_name], which is unusual. Verify against audited accounts." | Employee_cost = 0 |
| C3 | **Revenue Gap/Surplus outside historical range** (< −₹280.42L or > +₹64.72L) | Show prominent warning banner: "ANOMALY: Computed result of ₹X.XXL is outside the historical range. Manual review required before report generation." Block report generation until staff acknowledges. | Feed extreme values |
| C4 | **AICPI rate not configured** for the current year | Use last known rate with warning: "AICPI rate for FY2024-25 not configured. Using FY2023-24 rate of 4.2% as proxy. Please update in Settings." | Leave AICPI empty |
| C5 | **Cumulative surplus not carried forward** from previous year | Pull from historical_orders table. If not found, warn: "Previous year's cumulative balance not found. Interest calculation may be incomplete." | No previous year data |
| C6 | **Distribution loss = exactly 0%** | Flag as anomaly: "0% distribution loss is physically impossible. Data may be incorrect. Verify with licensee." | Set dist_loss = 0 |
| C7 | **Approved > Claimed** (reversal scenario) | Handle gracefully. Explain in plain language why Commission may approve more than claimed (e.g., interest on surplus correction). Show ⚠️ "Reversal detected" banner. | Replicate CSEZA 2023-24 case |
| C8 | **One-time expenditure not documented** | Do not reject outright. Flag: "One-time expenditure claimed without documentary evidence. Place in 'Pending Review' queue." | Claim with no supporting document |

---

## Category 4: AI Reasoning Edge Cases

| # | Edge Case | Expected Behavior | Test Input |
|---|---|---|---|
| A1 | **Gemini API is down** or rate-limited | Fall back to rule-based analysis only (symbolic solver). Indicate in report: "AI reasoning unavailable; rule-based analysis applied." Never block the user from getting a result. | Block API calls |
| A2 | **AI returns a hallucinated regulation clause** | The symbolic solver layer must cross-check all cited clauses against the knowledge base. If not found, strip the citation and flag: "Citation could not be verified. Staff must confirm regulatory basis." | Prompt model to make up a clause |
| A3 | **AI returns confidence < 50%** for a line item | Automatically escalate to 'pending_review'. Do not auto-approve. Show: "Low confidence. Staff review required." | Feed ambiguous/conflicting data |
| A4 | **Contradictory information** across two uploaded documents | Flag: "Conflict detected: Annual Accounts shows ₹X.XXL for [item] but ARR Order shows ₹Y.YYL. Please verify the correct figure." Pause analysis for that item until resolved. | Two documents with different values for same item |
| A5 | **Knowledge base is empty** (RAG has nothing to retrieve) | Run symbolic solver only. Show banner: "Regulatory knowledge base not loaded. AI reasoning is limited to built-in rules. Please contact the system administrator." | Delete all knowledge base files |

---

## Category 5: User Interface Edge Cases

| # | Edge Case | Expected Behavior | Test Input |
|---|---|---|---|
| UI1 | Staff clicks "Generate Report" before reviewing all flagged items | Show warning: "3 flagged items have not been reviewed. Generate report anyway?" (Confirm/Cancel) | Leave flagged items unreviewed |
| UI2 | Staff **overrides** an AI recommendation but doesn't provide a reason | Require the override note field. Show inline error: "Please provide a reason for the override." | Override without note |
| UI3 | Staff **logs out mid-analysis** | Save the analysis state. When staff logs back in, offer to resume from where they left off. | Logout during analysis |
| UI4 | **Slow network** causes the analysis polling to timeout | Show: "Analysis is taking longer than expected. It may still be running. Check back in a few minutes." Provide a manual refresh button. | Simulate 30-second API delay |
| UI5 | Staff **double-clicks** "Run Analysis" | Prevent duplicate submissions. After first click, disable the button and show a spinner. | Double-click the button |
| UI6 | Report PDF generation **fails** | Show error: "Report generation failed. Please try again. If the problem persists, contact support." Do not leave a broken download link. | Corrupt the report template |
| UI7 | **Table has 0 rows** (all items approved, none flagged) | Show: "All line items approved. No flagged or rejected items." (Empty state, not a blank screen) | Analysis with all approvals |
| UI8 | **Print/export** the analysis results table | Ensure the table is print-friendly. Provide a "Export to Excel" button that downloads all line items. | Click Export |

---

## Category 6: Security Edge Cases

| # | Edge Case | Expected Behavior | Test Input |
|---|---|---|---|
| S1 | **Unauthenticated API request** | Return 401 Unauthorized. Never return data. | API call without token |
| S2 | **Expired JWT token** | Return 401 with message: "Session expired. Please log in again." Redirect to login. | Wait for token to expire |
| S3 | **Analyst tries to access Commissioner-only function** (e.g., final approval) | Return 403 Forbidden. Show: "You do not have permission to perform this action." | Login as analyst, try to finalize |
| S4 | **SQL injection** in search/filter fields | All inputs must be parameterized queries. Never concatenate user input into SQL. | Enter `'; DROP TABLE users;--` |
| S5 | **XSS attack** in override notes field | Sanitize all user-entered text before storing or rendering. Use DOMPurify on frontend. | Enter `<script>alert(1)</script>` |
| S6 | **Path traversal** in file download (e.g., `../../etc/passwd`) | Validate all file paths against the allowed output directory. Never serve files outside `/generated_reports/`. | Request `../../etc/passwd` |

---

## Priority Matrix

| Priority | Edge Cases |
|---|---|
| **P0 — Must fix before demo** | C1, C3, U1, U3, A1, S1, S2, S4 |
| **P1 — Fix before production** | E1, E2, E4, C7, A3, A4, UI1, UI2, S5, S6 |
| **P2 — Nice to have** | U6, E5, E7, C8, UI3, UI8 |
