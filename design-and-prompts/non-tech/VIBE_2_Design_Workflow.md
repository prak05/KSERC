# Design Guidelines & User Workflow

## 1. Aesthetic & UI Philosophy
*   **Vibe:** "Utilitarian Government Tech." Clean, trustworthy, and authoritative.
*   **Color Palette:**
    *   Primary: Deep Navy (`#1A3557`), Dark Navy (`#0F2238`)
    *   Accent: Gold (`#C8960C`)
    *   Backgrounds: Off-white/Light Gray (`#F2F4F7`) for pages, White (`#FFFFFF`) for cards.
    *   Status Colors: Green (`#1A7F4B`) for approved/savings, Red (`#C0392B`) for disallowed/revenue gap, Amber (`#D97706`) for flagged/warnings.
*   **Typography:** Google Fonts. `Noto Sans` for UI readability, `EB Garamond` for official document headers, `Source Code Pro` for all financial numbers/data tables.
*   **Inspiration:** Strictly mimic the provided `kserc_real.html` prototype.

## 2. User Journey Workflow

### Step 1: Authentication & Setup
*   **Screen:** Centered login card with KSERC logo.
*   **Action:** Staff logs in. (For vibe coding, use simple hardcoded auth or Supabase Auth).
*   **Transition:** Redirects to the Main App layout (Sidebar + Content Area).

### Step 2: Session Configuration & Upload
*   **Screen:** "Upload & Analyse" tab.
*   **Action:**
    1. Select Licensee (Dropdown) and Financial Year.
    2. Input constants: Expected AICPI Rate (%), SBI term deposit rate (%).
    3. Drag and drop exactly 2-4 documents: Annual Accounts (Required), ARR Order (Required), Previous Order (Optional), Tariff Schedule (Optional).
*   **System Action:** UI shows a progress bar. Documents are sent to the AI API for structured extraction.

### Step 3: Analysis & Validation View (The Core)
*   **Screen:** "Analysis Results" tab.
*   **Section A (Vital KPIs):** 4 KPI boxes at the top showing: Revenue Gap/Surplus, Total Claimed, AT&C Loss %, Total Disallowed.
*   **Section B (Line Items Table):** A large data table listing every expense. Columns: `Item Name | Claimed | Cap | Approved | Disallowed | Status | Action`.
    *   *Action button:* "View Reasoning" opens a side panel.
*   **Section C (Reasoning Panel):** Clicking an item slides open a panel explaining the AI's logic (e.g., "Step 1: Extracted X. Step 2: Applied Rule Y. Step 3: Disallowed Z").
*   **Section D (Revenue Gap Table):** A strict accounting table showing Approved ARR minus Actual Revenue to arrive at the final Gap/Surplus.

### Step 4: Corrections & Overrides
*   **Action:** If the AI missed a value, display a glaring yellow "Manual Entry Required" banner with input fields.
*   **Action:** Staff can click "Override" on any flagged line item to forcefully approve a cost, requiring them to type a justification note (Audit Log).

### Step 5: Report Generation
*   **Screen:** "Generate Report" tab.
*   **Action:** Staff reviews a checklist to ensure all data is present. Clicks "Download PDF Report".
*   **System Action:** Generates a formal, printable A4 PDF styled exactly like a legal KSERC "Order" document using the extracted data and the mathematical outcomes.
