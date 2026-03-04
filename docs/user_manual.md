# KSERC SDL Truing-Up Platform: User Manual

Welcome to the KSERC Smart Truing-Up platform. This tool is designed to automate the initial compliance checking and mathematical computations required to verify Tariff Truing-Up petitions from Small Distribution Licensees (SDLs).

## 1. System Overview

The platform uses AI algorithms and deterministic mathematical models to:
- Automatically extract financial claims from uploaded PDF petitions.
- Cross-reference claims against historical Multi-Year Tariff (MYT) baselines.
- Apply KSERC True-Up Regulations (Distribution Loss Penalties, 90% Depreciation Caps, O&M Indexation).
- Generate a formal PDF Order mirroring official KSERC publications.

## 2. File Upload Requirements

Before uploading a petition, ensure:
1. The document is in **PDF format**.
2. Scanned documents must have clearly readable tables (OCR processing may take longer).
3. The File Size does not exceed **50 MB**.

## 3. Web Interface Usage

1. **Select Licensee:** Choose the correct SDL (e.g., Technopark, Infopark, CSEZA, KDHP) from the dropdown. This is critical as MYT baselines differ per licensee.
2. **Select Financial Year:** Specify the Truing-Up year (e.g., "2022-23").
3. **Upload PDF:** Click to browse and select the petition document.
4. **Initiate Analysis:** Click the "Analyze Pipeline" button and wait for the system to process the document (this can take 1-3 minutes depending on document size).

## 4. Reviewing the Results

Once the analysis completes, the dashboard will display a component-by-component breakdown:
- **Amount Claimed:** Extracted from the licensee's petition.
- **Amount Approved:** The system's deterministically audited response.
- **Variance:** The difference (if any).
- **Status Label:** "Approved as Claimed", "Reduced", or "Increased".
- **Commission's Justification:** Automatically generated legal rationale for the decision.

### Exploring the Disallowances Log
A dedicated pane will list all items that were rejected or reduced, directly citing the relevant KSERC Regulation clause (e.g., *Regulation 27(4) 90% Capex Limit*).

## 5. Human-In-The-Loop Overrides

The system is designed to assist humans, not replace them. If the auditor fundamentally disagrees with the system's computation:
1. Click the **"Override"** button next to any expense component.
2. Enter the new **Approved Amount**.
3. Provide a written **Justification** for why the system's rule is being bypassed.
4. Click **Apply Override**.

*Note: Doing this will automatically recompute the Total Revenue Gap/Surplus and seamlessly regenerate the underlying PDF Order.*

## 6. Downloading the Official Order

Once all figures are reviewed and verified:
Click **"Download Draft Order (PDF)"**. 

The generated document will include:
- The KSERC emblem, members present, and dates.
- A multi-page regulatory narrative detailing findings per line item.
- The approved revenue table.
- A final directive detailing how current/past surplus funds should be treated (including Imputed Interest on Surplus at SBI Deposit rates).
- Signature blocks for the Chairman and Members.
