# KSERC AI Truing-Up Tool — Test Plan
> **Project:** AI-Based Analytical Tool for Truing Up of Accounts | Work Order No. KSERC/CSO/03-05  
> **Purpose:** Critical user journeys to manually test before KSERC demonstration.  
> **Version:** 1.0 | Date: 2026

---

## How to Use This Test Plan
Execute each test case manually before the KSERC demo. Mark ✅ Pass or ❌ Fail.  
All test cases must pass before presenting to the Commission.

---

## Module 1: Authentication

| Test ID | Test Case | Steps | Expected Result | Pass/Fail |
|---|---|---|---|---|
| AUTH-01 | Valid login | Enter correct credentials, click Login | Redirected to Dashboard. Welcome message shown. | |
| AUTH-02 | Invalid password | Enter wrong password | Error: "Incorrect username or password". No redirect. | |
| AUTH-03 | Empty username | Submit with blank username | Inline error: "Username is required" | |
| AUTH-04 | Session expiry | Wait 8+ hours after login, make a request | Redirect to Login with message: "Session expired. Please log in again." | |
| AUTH-05 | Logout | Click Logout | Redirected to Login. JWT token invalidated. | |

---

## Module 2: Document Upload

| Test ID | Test Case | Steps | Expected Result | Pass/Fail |
|---|---|---|---|---|
| UPL-01 | Upload valid PDF | Select Infopark, FY 2024-25. Upload a valid Annual Accounts PDF | Success message. Document listed as "Uploaded" in session. | |
| UPL-02 | Upload invalid file type | Try to upload a `.jpg` file | Error: "Invalid file type. Only PDF and Excel files are accepted." | |
| UPL-03 | Upload all 4 required documents | Upload Annual Accounts, ARR Order, Previous Truing-Up, Energy Audit | All 4 shown in the upload list. "Run Analysis" button becomes enabled. | |
| UPL-04 | Duplicate document type | Upload Annual Accounts twice | Confirmation dialog: "Replace existing Annual Accounts?" | |
| UPL-05 | Missing mandatory document | Try to run analysis with only 2 documents uploaded | Warning: "Annual Accounts and ARR Order are mandatory. Please upload them to proceed." | |

---

## Module 3: Analysis Engine

| Test ID | Test Case | Steps | Expected Result | Pass/Fail |
|---|---|---|---|---|
| ANA-01 | Trigger analysis | Upload all docs, click "Run AI Analysis" | Progress screen shown. Steps complete one by one with ✅ checkmarks. | |
| ANA-02 | Revenue Gap computation | Use Infopark 2024-25 sample data (claimed ₹79.76L) | AI recommends: ₹64.72L gap. Matches historical benchmark. | |
| ANA-03 | Section 3(1) duty rejection | Include Section 3(1) duty (₹2.50L) in sample data | Line item shows: ❌ Rejected. Approved: ₹0. Reason cited. | |
| ANA-04 | CSR rejection | Include CSR expense (₹1.20L) in sample data | Line item shows: ❌ Rejected. Approved: ₹0. Reason cited. | |
| ANA-05 | O&M normative cap | Employee cost above normative limit | Line item shows: ⚠️ Flagged. Approved = normative cap. Excess shown as disallowed. | |
| ANA-06 | AT&C loss calculation | Use data: input=1000 MU, sold=971.4 MU, target=4.23% | AT&C Loss = 2.86%. Efficiency gain achieved = ✅. 2/3 savings calculated. | |
| ANA-07 | Surplus scenario | Use data where actual_revenue > approved_arr | Result shows as Surplus (negative value, green badge). No error. | |
| ANA-08 | Out-of-range result | Manually inject a value that would produce > ₹280L surplus | Warning banner: "ANOMALY: Result outside historical range. Manual review required." | |
| ANA-09 | AI reasoning citation | Check any flagged item's reasoning | Reasoning text contains: regulation name + clause number OR past order reference. No unsupported claims. | |
| ANA-10 | Reversal scenario | Use CSEZA 2023-24 sample (claimed ₹-3.42L, actual surplus) | Tool detects reversal. Shows ⚠️ "Reversal detected" banner. Correct surplus computed. | |

---

## Module 4: Human Review Interface

| Test ID | Test Case | Steps | Expected Result | Pass/Fail |
|---|---|---|---|---|
| REV-01 | Accept AI recommendation | Click "Accept" on a flagged item | Item status changes to "Approved by Staff". Saved to DB. | |
| REV-02 | Override AI recommendation | Enter a different amount with a reason | Override recorded. Audit log entry created. Summary recalculated. | |
| REV-03 | Override without reason | Try to override without entering a reason | Form validation: "Please provide a reason for the override." Cannot submit. | |
| REV-04 | View full reasoning | Click "View Reasoning" on any line item | Side panel opens. Shows: retrieval context + step-by-step reasoning + citations. | |
| REV-05 | Summary auto-updates | Accept/reject several items | Revenue Gap/Surplus in Summary Card updates in real time. | |
| REV-06 | Attempt report before review | Click Generate Report with 3 flagged items unreviewed | Warning: "3 flagged items not reviewed. Generate report anyway?" (Confirm/Cancel) | |

---

## Module 5: Report Generation

| Test ID | Test Case | Steps | Expected Result | Pass/Fail |
|---|---|---|---|---|
| RPT-01 | Generate PDF report | Complete review, click Generate Report (PDF) | PDF downloaded. Opens correctly. Contains KSERC letterhead. | |
| RPT-02 | Generate Word report | Choose Word format | DOCX downloaded. Opens in Word. All tables present and correctly formatted. | |
| RPT-03 | Report content accuracy | Open generated PDF, check revenue gap figure | Figure matches the value shown on screen. No discrepancy. | |
| RPT-04 | Rejected items in report | Check Table 2 in PDF | Section 3(1) duty and CSR show ₹0 with rejection reason stated. | |
| RPT-05 | AI Reasoning Appendix | Check report includes reasoning appendix | Appendix contains regulation citations and calculation trails. No placeholder text. | |
| RPT-06 | No placeholder text | Scan entire report | Zero occurrences of: "TBD", "INSERT HERE", "XX.XX", "[DATE]", "[NAME]" | |

---

## Module 6: Historical Data View

| Test ID | Test Case | Steps | Expected Result | Pass/Fail |
|---|---|---|---|---|
| HIS-01 | View all historical orders | Navigate to Historical Data | All 7 pre-seeded records shown: Technopark 2020-21 through Infopark 2024-25. | |
| HIS-02 | Filter by licensee | Select "INFOPARK" filter | Only Infopark records shown. | |
| HIS-03 | Filter by outcome | Select "Reversal" filter | Only CSEZA 2023-24 shown (reversal case). | |
| HIS-04 | Benchmark display | Check bottom of page | Benchmarks shown: Max surplus ₹280.42L, Max gap ₹64.72L. | |
| HIS-05 | Export historical data | Click "Export Data" | Excel file downloaded with all visible records. | |

---

## Module 7: Security & Access Control

| Test ID | Test Case | Steps | Expected Result | Pass/Fail |
|---|---|---|---|---|
| SEC-01 | Unauthenticated API access | Call `/api/v1/sessions` without token (use curl or Postman) | 401 Unauthorized response. | |
| SEC-02 | Analyst cannot finalize report | Login as analyst role, try to access "Mark as Final" | 403 Forbidden. Option not shown in UI. | |
| SEC-03 | Analyst cannot see other users' sessions | Create two analyst accounts. Login as Analyst A. | Sessions created by Analyst B are not visible. | |
| SEC-04 | XSS in override notes | Enter `<script>alert('xss')</script>` in override note | Text saved and displayed as literal text. No script executed. | |
| SEC-05 | File download requires auth | Try to access report download URL without token | 401 Unauthorized. No file served. | |

---

## Module 8: End-to-End Demonstration Scenario

This is the single most important test — the complete KSERC demo flow.

| Step | Action | Expected Result | Pass/Fail |
|---|---|---|---|
| 1 | Login as KSERC staff | Successfully logged in. Dashboard shown. | |
| 2 | Create new session for Infopark FY 2024-25 | Session created. | |
| 3 | Upload 4 sample documents | All uploaded successfully. | |
| 4 | Trigger analysis | Progress screen completes. All steps check off. | |
| 5 | View results | Summary shows Revenue Gap ₹64.72L. 2 flagged, 2 rejected. | |
| 6 | Review each flagged item | View reasoning, accept AI recommendation for both. | |
| 7 | Generate PDF report | Report downloads. Opens. Contains correct figures and KSERC formatting. | |
| 8 | View historical data | Infopark 2024-25 result matches known KSERC order. | |
| **TOTAL DEMO TIME** | | Target: 10 minutes from login to report download | |

---

## Acceptance Criteria for KSERC Demo

All of the following must be true for the tool to be presented to KSERC:

- [ ] All **Module 3 (Analysis)** tests pass with sample data matching known KSERC orders
- [ ] **RPT-06 (No placeholder text)** passes — zero placeholder content in any output
- [ ] **ANA-03 and ANA-04** pass — Section 3(1) and CSR always rejected
- [ ] **End-to-End Demo Scenario** completes in under 10 minutes
- [ ] Generated PDF report is professional enough to present to the Commission
- [ ] All dollar figures in ₹ Lakh, 2 decimal places, with ₹ symbol
- [ ] No JavaScript console errors during the demo flow
- [ ] The tool runs on the demo machine without internet dependency (all AI = local or has fallback)
