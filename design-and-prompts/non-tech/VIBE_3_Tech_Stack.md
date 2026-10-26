# Tech Stack & Backend Logic Specification

## 1. Full Tech Stack (Vibe Coding Ready)

This stack optimizes for **zero-cost**, rapid AI-assisted development (using Cursor/Windsurf), and immediate deployability via Vercel.

### Frontend
*   **Framework:** Next.js (App Router) + React
*   **Styling:** Tailwind CSS (configured to match the KSERC Navy/Gold theme exactly).
*   **UI Components:** `shadcn/ui` (for highly accessible, clean, non-bloated tables, modals, and buttons).
*   **PDF Generation:** `jspdf` and `jspdf-autotable` (client-side generation to avoid heavy backend processing).
*   **Icons:** `lucide-react`

### Backend / Data / Auth
*   **BaaS:** Supabase (Provides free tier PostgreSQL database for the audit log, secure file storage for uploaded PDFs, and simple Auth).
*   **API Routes:** Next.js serverless API routes (deployed on Vercel) to handle document parsing securely without exposing keys to the browser.
*   **Document Parsing:** `pdf-parse` or integration with an OCR workflow if dealing with scanned PDFs.

### AI "Brain" (The Zero-Cost LLM Engine)
Instead of expensive OpenAI keys, use ultra-cheap or free OpenAI-compatible endpoints that offer excellent context windows for document extraction.
*   **Primary Recommended Provider:** **Groq** (`llama-3.3-70b-versatile`)
    *   *Why:* Extremely fast, massive free tier limits, excellent at JSON extraction.
    *   *Link:* [console.groq.com](https://console.groq.com/)
*   **Alternative Provider:** **DeepSeek API** (`deepseek-chat`)
    *   *Why:* Near-zero cost, highly intelligent for coding and data structuring.
    *   *Link:* [platform.deepseek.com](https://platform.deepseek.com/)
*   **Backup Free Provider:** `glhf.chat` (Good AI / Llama 3 endpoints) via the [free-llm-api-resources list](https://github.com/cheahjs/free-llm-api-resources).
*   **Orchestration Library:** `LangChain.js` or standard `@ai-sdk/openai` configured to point to the alternate Base URLs.

## 2. Application Logic Architecture (Zero Hallucination)

The app must use the LLM **ONLY for extraction**, and use **hardcoded Python/JS math for validation** to ensure zero hallucinations.

### Step 1: The Prompt (LLM Extraction)
Pass the document text to the LLM (e.g., Groq API) with a strict system prompt:
*"You are a parser. Extract these exact values from the text into JSON: `approved_arr_lakhs`, `actual_revenue_lakhs`, and an array of `line_items` (name, category, claimed_amount). If not found, return null."*

### Step 2: Core KSERC Formulas (Math Engine)

This logic must be coded directly in the Next.js API route or Utility functions:

**A. The Revenue Gap Formula:**
\`\`\`javascript
const netApprovedARR = approvedARR - nonTariffIncome;
const revenueGap = netApprovedARR - actualRevenueCollected;
// If revenueGap > 0  --> It's a GAP (Licensee is owed money)
// If revenueGap < 0  --> It's a SURPLUS (Licensee has excess)
\`\`\`

**B. O&M Normative Cap Formula (Prudence Check):**
\`\`\`javascript
// Applies to: Employee Costs, R&M, A&G
const cap = previousYearApproved * (1 + (aicpiRate / 100));
let disallowed = Math.max(0, claimedAmount - cap);
let approved = claimedAmount - disallowed;
// Tag as "Flagged" if disallowed > 0.
\`\`\`

**C. Perennial Rejections (Hardcoded Disallowances):**
\`\`\`javascript
const perennialKeywords = ["section 3(1)", "csr", "rpo provision"];
if (perennialKeywords.some(kw => itemName.toLowerCase().includes(kw))) {
    approved = 0;
    disallowed = claimedAmount;
    status = "Rejected"; // Needs KSERC specific citation string.
}
\`\`\`

**D. AT&C Loss Efficiency Gain Formula:**
\`\`\`javascript
const actualLossPct = ((energyInput - energySold) / energyInput) * 100;
if (actualLossPct < approvedTargetPct) {
    const gainMU = ((approvedTargetPct - actualLossPct) / 100) * energyInput;
    const savingsLakhs = (gainMU * 1000000 * powerPurchaseCostPerUnit) / 100000;
    const licenseeShare = (2 / 3) * savingsLakhs; // Allowed to be retained
}
\`\`\`

## 3. Vibe Coding AI Prompt / Instructions
When using a modern AI code editor (Cursor / Windsurf), dump all three of these markdown files into the context and simply type:

> *"Generate the complete Next.js application for this KSERC Truing-Up Tool using shadcn/ui and Tailwind. Use the deepseek/groq api setup for the extraction. Implement all the formulas exactly as specified in the Tech Stack doc. Ensure no placeholder components are used and the app acts like the functional html prototype. Hook up the UI state to a simulated backend function."*
