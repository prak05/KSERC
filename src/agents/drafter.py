"""
KSERC SDL Truing Up — PDF Order Generator (Drafter Agent)
===========================================================

Uses Gemini 2.5 Pro with the ACTUAL reference OP 82 2023 PDF as a template,
plus the petition PDF as context, to generate a comprehensive 25-30 page
Truing Up Order.  Gemini outputs CLEAN HTML directly (not markdown),
which is then rendered to PDF using xhtml2pdf.
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from src.gemini_client import generate_with_pdf, get_client

logger = logging.getLogger(__name__)

# Path to the reference KSERC order that serves as the exact template
REFERENCE_ORDER_PDF = Path(r"C:\Users\adwai\OneDrive\Desktop\K-Project\Documents\Infopark True-Up 2022-23 (OP 82 2023).pdf")

# ── CSS that faithfully replicates the KSERC official order style ──────────
KSERC_CSS = """
    @page {
        size: a4 portrait;
        margin: 2.2cm 2.8cm 2.2cm 2.8cm;
    }

    body {
        font-family: "Times New Roman", Times, serif;
        font-size: 13pt;
        line-height: 2.3;
        text-align: justify;
        color: #000;
    }

    /* ── Headings ─────────────────────────────────────── */
    h1 {
        font-size: 15pt;
        font-weight: bold;
        text-align: center;
        margin-bottom: 18px;
        margin-top: 18px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    h2 {
        font-size: 14pt;
        font-weight: bold;
        text-align: center;
        margin-top: 18px;
        margin-bottom: 18px;
    }
    h3 {
        font-size: 13pt;
        font-weight: bold;
        text-align: left;
        margin-top: 18px;
        margin-bottom: 18px;
        padding-left: 8px;
        break-after: avoid;
    }

    /* ── Paragraphs ───────────────────────────────────── */
    p {
        margin-bottom: 18px;
        margin-top: 18px;
        text-indent: 0;
    }
    .center {
        text-align: center;
    }
    .bold {
        font-weight: bold;
    }

    /* ── Header block (petition details) ──────────────── */
    .header-table {
        width: 100%;
        border: none;
        margin-bottom: 18px;
        margin-top: 18px;
    }
    .header-table td {
        border: none;
        padding: 2px 4px;
        font-size: 13pt;
        vertical-align: top;
        line-height: 2.3;
    }
    .header-table .label {
        font-weight: bold;
        width: 20%;
        text-align: left;
    }
    .header-table .colon {
        width: 3%;
        text-align: center;
        font-weight: bold;
    }
    .header-table .value {
        width: 77%;
        text-align: left;
    }
    .header-table .spacer-row td {
        padding: 2px 0;
        height: 6px;
        line-height: 0;
    }

    /* ── Data tables (financial data) ─────────────────── */
    table.data-table {
        border-collapse: collapse;
        width: 100%;
        margin-top: 18px;
        margin-bottom: 18px;
        font-size: 12.0pt;
    }
    table.data-table th,
    table.data-table td {
        border: 1px solid #000;
        padding: 8px 10px;
        font-size: 12.0pt;
        vertical-align: middle;
        line-height: 2.3;
    }
    table.data-table th {
        font-weight: bold;
        text-align: center;
        background: none;
    }
    table.data-table td {
        text-align: left;
    }
    table.data-table td.num {
        text-align: right;
    }
    table.data-table td.center-cell {
        text-align: center;
    }
    table.data-table tr.total-row td {
        font-weight: bold;
        border-top: 2px solid #000;
    }
    .table-wrapper {
        margin-bottom: 8px;
    }

    /* ── Table caption (ABOVE table, centered, bold) ────── */
    .table-caption {
        text-align: center;
        font-weight: bold;
        font-size: 11pt;
        margin-bottom: 0;
        margin-top: 10px;
    }
    .table-subcaption {
        text-align: center;
        font-weight: bold;
        font-size: 10.5pt;
        margin-bottom: 0;
        margin-top: 1px;
    }
    .table-unit {
        text-align: right;
        font-style: italic;
        font-size: 10pt;
        margin-bottom: 2px;
    }

    /* ── Commission-decision paragraphs (bold italic) ───── */
    .commission-decision {
        font-weight: bold;
        font-style: italic;
    }

    /* ── Signature block ──────────────────────────────── */
    table.sig-table {
        width: 100%;
        border: none;
        margin-top: 30px;
        break-inside: avoid;
    }
    table.sig-table td {
        border: none;
        text-align: center;
        padding: 3px 6px;
        font-size: 11pt;
        vertical-align: top;
    }
    .secretary-block {
        text-align: center;
        margin-top: 20px;
        break-inside: avoid;
    }

    /* ── Ordered/numbered paragraphs ──────────────────── */
    ol { margin-bottom: 18px; margin-top: 18px; padding-left: 28px; }
    ol > li { margin-bottom: 18px; text-align: justify; }
    ul { margin-bottom: 18px; margin-top: 18px; padding-left: 24px; }
    li { margin-bottom: 18px; }

    /* ── Blockquotes (regulation citations) ────────────── */
    blockquote {
        margin-left: 28px;
        margin-right: 16px;
        margin-top: 18px;
        margin-bottom: 18px;
        font-style: italic;
        border-left: 2px solid #555;
        padding-left: 10px;
        font-size: 11pt;
        line-height: 2.3;
    }

    /* ── Misc ─────────────────────────────────────────── */
    strong, b { font-weight: bold; }
    em, i { font-style: italic; }

    /* ── Page footer ──────────────────────────────────── */
    #page-footer { text-align: center; font-size: 10pt; }

    /* ── Print media — Playwright respects this ──────── */
    @media print {
        body { line-height: 2.3; }
        p { margin-top: 18px; margin-bottom: 18px; }
        h3 { margin-top: 18px; margin-bottom: 18px; }
        blockquote { margin-top: 18px; margin-bottom: 18px; }
        table.data-table { page-break-inside: auto; }
        thead { display: table-header-group; }
    }
"""



def _generate_document_with_gemini(state: dict) -> str:
    """
    Use Gemini 2.5 Pro with THREE-PART generation:
    Part A: Header + Introduction + Hearing + Energy Sales (~10 pages)
    Part B: Distribution Loss + Power Purchase + O&M Expenses (~12 pages)
    Part C: Depreciation + Interest + Revenue + ARR Summary + Orders + Signature (~10 pages)
    Total target: 30+ pages, matching the reference order OP 82/2023.
    """
    from google.genai import types

    client = get_client()
    licensee = state.get("licensee_name", "Licensee")
    fy = state.get("financial_year", "2024-25")

    exp_keys = [
        "power_purchase_cost", "employee_cost", "repair_maintenance", "admin_general",
        "depreciation", "interest_long_term", "interest_consumer_deposits",
        "interest_working_capital", "carrying_cost", "return_on_nfa",
        "other_debits", "section3_1_duty", "other_expenses"
    ]
    rev_keys = ["revenue_from_sale", "wheeling_charges", "non_tariff_income", "other_revenue"]

    claimed_exp = state.get("claimed_expenses", {})
    approved_exp = state.get("approved_expenses", {})
    claimed_rev = state.get("claimed_revenues", {})

    data_block = "=== AUDITED FINANCIAL DATA (Rs. Lakhs) ===\n"
    data_block += f"{'Component':<45} {'Claimed':>12} {'Approved':>12} {'Variance':>12}\n"
    data_block += "-" * 85 + "\n"
    total_c, total_a = 0.0, 0.0
    for k in exp_keys:
        c = claimed_exp.get(k, 0.0)
        a = approved_exp.get(k, 0.0)
        if c > 0 or a > 0:
            name = k.replace("_", " ").title()
            data_block += f"{name:<45} {c:>12.2f} {a:>12.2f} {(a-c):>12.2f}\n"
            total_c += c
            total_a += a
    data_block += "-" * 85 + "\n"
    data_block += f"{'TOTAL EXPENDITURE':<45} {total_c:>12.2f} {total_a:>12.2f} {(total_a-total_c):>12.2f}\n\n"
    data_block += "REVENUES:\n"
    rev_total = 0.0
    for k in rev_keys:
        c = claimed_rev.get(k, 0.0)
        if c > 0:
            name = k.replace("_", " ").title()
            data_block += f"  {name}: {c:.2f}\n"
            rev_total += c
    data_block += f"  TOTAL REVENUE: {rev_total:.2f}\n\n"
    data_block += f"Total Claimed Expenditure: {state.get('total_claimed_expenditure', 0):.2f}\n"
    data_block += f"Total Approved Expenditure: {state.get('total_approved_expenditure', 0):.2f}\n"
    data_block += f"Total Revenue: {state.get('total_claimed_revenue', 0):.2f}\n"
    data_block += f"Revenue Gap/Surplus: {state.get('final_revenue_gap_surplus', 0):.2f} (Negative = Gap)\n"
    disallowances = state.get("disallowance_log", [])
    if disallowances:
        data_block += "\nDISALLOWANCES & JUSTIFICATIONS:\n"
        for d in disallowances:
            data_block += f"  - {d['item']}: Claimed {d.get('claimed',0):.2f}, Approved {d.get('approved',0):.2f}\n"
            data_block += f"    Reason: {d.get('justification', 'N/A')}\n"
    data_block += f"\nDISTRIBUTION LOSS:\n"
    data_block += f"  Claimed: {state.get('claimed_distribution_loss_pct', 0):.2f}%\n"
    data_block += f"  Target:  {state.get('target_distribution_loss_pct', 0):.2f}%\n"

    petition_path = state.get("petition_pdf_path", "")

    HTML_RULES = """
=== OUTPUT FORMAT: CLEAN HTML ONLY ===
ABSOLUTELY NO markdown. NEVER use pipe tables (|). Do NOT include html/head/body tags.

CRITICAL DATA RULE: ALL numbers and justifications MUST come from the PETITION PDF (PDF 2).
  - PDF 1 (reference order) is for FORMAT ONLY — copy its structure, headings, paragraph style.
  - NEVER copy any number from PDF 1 — those are FY 2022-23 values, not the current petition.
  - If a number is not in the petition, use 0.00 or state 'as per petition'.
  - Commission decisions are based on AUDITED DATA provided, not reference order values.

HTML ELEMENT RULES:
- Table name (ABOVE table, two lines): <p class="table-caption">Table N<br/><b>Title of Table</b></p>
- Unit line BELOW caption: <p class="table-subcaption">(Rs. in Lakhs unless specified)</p>
- Every financial table: <table class="data-table">
- Number cells (right-aligned): <td class="num">123.45</td>
- Total rows: <tr class="total-row"><td><b>Total</b></td><td class="num"><b>123.45</b></td></tr>
- Numbered paragraphs: <p><b>5.</b>&nbsp;&nbsp;Text of paragraph...</p>
- Section headings: <h3>Section Title</h3>
- Commission decision (bold+italic): <p class="commission-decision">After analyzing the details, the Commission hereby approves...</p>
- Regulation: <blockquote>Regulation XX: exact text</blockquote>
- Sub-items: <p style="margin-left:32px;"><b>a)</b> Text...</p>

STYLE: No background-color on cells. Bold centered header row. 1px solid borders.
"""


    config = types.GenerateContentConfig(
        temperature=0.15,
        response_mime_type="text/plain",
        max_output_tokens=65536,
    )

    def _upload_pdfs():
        logger.info("Uploading reference PDF...")
        ref = client.files.upload(
            file=str(REFERENCE_ORDER_PDF),
            config=types.UploadFileConfig(mime_type="application/pdf"),
        )
        pet = None
        if petition_path and Path(petition_path).exists():
            logger.info("Uploading petition PDF...")
            pet = client.files.upload(
                file=petition_path,
                config=types.UploadFileConfig(mime_type="application/pdf"),
            )
        return ref, pet

    def _delete_pdfs(ref, pet):
        try:
            client.files.delete(name=ref.name)
            if pet:
                client.files.delete(name=pet.name)
        except Exception:
            pass

    def _call_with_retry(parts_list, label="API call", max_retries=3):
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-pro",
                    contents=parts_list,
                    config=config,
                )
                return response.text.strip()
            except Exception as e:
                logger.warning(f"{label} attempt {attempt}/{max_retries} failed: {e}")
                if attempt == max_retries:
                    raise
                import time as _time
                _time.sleep(5 * attempt)

    # ==========================================================================
    # READ THE REFERENCE ORDER TEXT to give Gemini exact section structure
    # ==========================================================================
    import fitz as _fitz
    ref_text_summary = ""
    try:
        ref_doc = _fitz.open(str(REFERENCE_ORDER_PDF))
        pages_text = []
        for i, pg in enumerate(ref_doc):
            pages_text.append(pg.get_text())
        ref_doc.close()
        # First 5 pages as structure reference
        ref_text_summary = "\n".join(pages_text[:5])[:3000]
    except Exception:
        pass

    # ==========================================================================
    # PART A: Header + Introduction + Hearing + Energy Sales
    # ==========================================================================
    prompt_a = f"""You are an expert legal drafter for the Kerala State Electricity Regulatory Commission (KSERC).

TASK: Generate PART A of a Truing-Up Order for M/s {licensee} for FY {fy}.

INPUTS:
- PDF 1 = Reference Order OP 82/2023 (Infopark FY 2022-23 True-Up) - FORMAT TEMPLATE.
  Match its EXACT structure, paragraph style, depth, tone, regulation citations.
- PDF 2 = Petition by M/s {licensee} for FY {fy} - DATA SOURCE. Extract all numbers from here.
- Audited Data:
{data_block}

{HTML_RULES}


MANDATORY 4-STEP JUSTIFICATION STRUCTURE (for EVERY cost head and revenue item):

For each item (Employee Cost, R&M, Depreciation, Interest, etc.) write exactly:
  STEP 1 - CLAIMED: "The licensee has claimed Rs.XX.XX lakh on account of [item]. 
    [Extract exact details from Petition PDF: amount, basis given, how calculated]."
  STEP 2 - REGULATION: "As per Regulation [NN] of KSERC (Terms and Conditions for 
    Determination of Tariff) Regulations, 2021, [quote the applicable norm/formula]."
  STEP 3 - ANALYSIS: "The Commission has examined the claim. [State what verification 
    was done, e.g. comparison with norm, previous year actuals, KSEB verification, 
    calculation recheck]. [State if claim matches norm or deviates, and by how much]."
  STEP 4 - DECISION (bold+italic using commission-decision class):
    "<p class='commission-decision'>The Commission, after analyzing the details and 
    duly considering [reason], hereby approves Rs.XX.XX lakh / [approves/disallows] 
    the claim of the licensee for [item] for the year [FY].</p>"

CRITICAL: 
- All Rs. values in STEPS 1-4 must come from Petition PDF (PDF 2), NOT from reference order.
- For items where the commission allows full claim: say so with reason (claim found to be in order).
- For disallowances: state the exact regulation ceiling, the excess amount, and why it's disallowed.
- Never just say "Commission approves Rs.X" without the reasoning in Step 3.


START with this EXACT header:
<h1>KERALA STATE ELECTRICITY REGULATORY COMMISSION</h1>
<h2>THIRUVANANTHAPURAM</h2>
<p class="center bold">Petition No: OP XX / 2026</p>
<table class="header-table">
  <tr><td class="label">Present</td><td class="colon">:</td><td class="value"><b>Sri T K Jose, Chairman</b><br/><b>Adv. A J Wilson, Member</b><br/><b>Sri. B Pradeep, Member</b></td></tr>
  <tr class="spacer-row"><td colspan="3"></td></tr>
  <tr><td class="label">In the matter of</td><td class="colon">:</td><td class="value">Petition for approval of truing up of accounts for the financial year {fy}</td></tr>
  <tr class="spacer-row"><td colspan="3"></td></tr>
  <tr><td class="label">Petitioner</td><td class="colon">:</td><td class="value">M/s {licensee} Kerala</td></tr>
  <tr><td class="label">Represented by</td><td class="colon">:</td><td class="value">[Names from petition]</td></tr>
  <tr class="spacer-row"><td colspan="3"></td></tr>
  <tr><td class="label">Respondent</td><td class="colon">:</td><td class="value">M/s Kerala State Electricity Board Limited</td></tr>
  <tr><td class="label">Represented by</td><td class="colon">:</td><td class="value">[Names from petition]</td></tr>
  <tr class="spacer-row"><td colspan="3"></td></tr>
  <tr><td class="label">Hearing</td><td class="colon">:</td><td class="value">DD.MM.YYYY</td></tr>
</table>
<p class="center bold">Order Dated DD.MM.YYYY</p>

THEN write ALL of these sections in full:

SECTION 1 - INTRODUCTION (paras 1-6, MINIMUM 6 paragraphs):
Para 1: M/s {licensee} background — full license area description, consumer categories, network extent, date of license grant and license number.
Para 2: Filing history — when this petition was filed citing date, what previous Commission orders govern FY {fy} tariff, the MYT order reference.
Para 3: Legal basis — cite KSERC Tariff Regulations 2021 Regulation 3, 67, 68 on truing up process and what the Commission is required to do.
Para 4: TABLE 1 — Comparison of ARR and Revenue for FY {fy}. Full table with: Power Purchase, Employee Cost, R&M, A&G, Depreciation, Interest & Finance, Other Debits, Total Expenditure, Revenue from Sale, Non-Tariff Income, Total Revenue, Revenue Gap. Show Projected/Claimed and Approved columns.
Para 5: TABLE 2 — Year-on-year truing up comparison (at minimum show FY 2021-22, 2022-23, 2023-24, 2024-25 with Revenue Gap).
Para 6: Brief overview of the Commission's approach to examining each cost head.

SECTION 2 - HEARING ON THE PETITION (paras 7-15, MINIMUM 9 paragraphs):
Write one paragraph per point raised at the hearing. Cover ALL of these:
- Date and place of hearing
- Licensee's submissions on Energy Sales (actual sales vs approved)
- Licensee's submissions on Distribution Loss (actual % achieved)
- Licensee's submissions on Power Purchase Cost (units, rate, total)
- Licensee's submissions on Employee Cost (staff count, pay scale, PF, gratuity)
- Licensee's submissions on R&M Expenses (transformer maintenance, line maintenance)
- Licensee's submissions on A&G Expenses (insurance, audit fees, legal, etc.)
- Licensee's submissions on Capital Expenditure and asset additions
- Licensee's submissions on Interest and Depreciation
- Licensee's submissions on Revenue (category-wise tariff revenue)
- Respondent KSEB's position (always include KSEB letter reference and their view on each major item)
- Para for KSEB's comments on distribution loss, power purchase tallying, O&M excess
- Commission's observations and questions raised

SECTION 3 - ENERGY SALES AND CONSUMER MIX (paras 16-21, MINIMUM 5 paragraphs):
Para: Explain consumer categories in {licensee}'s supply area — HT, LT, domestic, commercial, industrial, public lighting, etc.
Para: Comparison of FY {fy} actual sales vs. approved in MYT order — units, increase/decrease and reasons.
Para: Category-wise analysis — which categories grew, which declined and why.
Para: Per-unit revenue realization analysis.
Para: Commission's finding and approval of energy sales figures.
TABLE 3 — Consumer Mix and Energy Sales: Columns: Sl.No | Category | Consumers (No.) Claimed | Energy Sales (MU) Claimed | Energy Sales (MU) Approved

TARGET: Part A must produce approximately 12 PRINTED A4 PAGES of HTML content.
Do NOT write the signature block. Stop after Energy Sales section.
Do NOT compress — write every paragraph in full detail with 4-6 sentences minimum per para."""

    logger.info("=== PART A: Header + Intro + Hearing + Energy Sales ===")
    t0 = time.time()
    ref_a, pet_a = _upload_pdfs()
    parts_a = [types.Part.from_uri(file_uri=ref_a.uri, mime_type="application/pdf")]
    if pet_a:
        parts_a.append(types.Part.from_uri(file_uri=pet_a.uri, mime_type="application/pdf"))
    parts_a.append(types.Part.from_text(text=prompt_a))
    part_a_html = _call_with_retry(parts_a, "Part A")
    logger.info(f"Part A: {len(part_a_html)} chars in {time.time()-t0:.1f}s")
    _delete_pdfs(ref_a, pet_a)

    tail_a = part_a_html[-2500:] if len(part_a_html) > 2500 else part_a_html

    # ==========================================================================
    # PART B: Distribution Loss + Power Purchase + O&M (Employee, R&M, A&G)
    # ==========================================================================
    prompt_b = f"""You are an expert legal drafter for KSERC.

TASK: Generate PART B of a Truing-Up Order for M/s {licensee} for FY {fy}.
Part A (Header/Intro/Hearing/Energy Sales) is already written. Continue from where it ends.

INPUTS:
- PDF 1 = Reference Order OP 82/2023 - FORMAT TEMPLATE
- PDF 2 = Petition by M/s {licensee} for FY {fy} - DATA SOURCE
- Audited Data:
{data_block}

{HTML_RULES}

CONTEXT - last 2500 chars of Part A:
---
{tail_a}
---

Continue paragraph numbering from where Part A ended.


MANDATORY 4-STEP JUSTIFICATION STRUCTURE (for EVERY cost head and revenue item):

For each item (Employee Cost, R&M, Depreciation, Interest, etc.) write exactly:
  STEP 1 - CLAIMED: "The licensee has claimed Rs.XX.XX lakh on account of [item]. 
    [Extract exact details from Petition PDF: amount, basis given, how calculated]."
  STEP 2 - REGULATION: "As per Regulation [NN] of KSERC (Terms and Conditions for 
    Determination of Tariff) Regulations, 2021, [quote the applicable norm/formula]."
  STEP 3 - ANALYSIS: "The Commission has examined the claim. [State what verification 
    was done, e.g. comparison with norm, previous year actuals, KSEB verification, 
    calculation recheck]. [State if claim matches norm or deviates, and by how much]."
  STEP 4 - DECISION (bold+italic using commission-decision class):
    "<p class='commission-decision'>The Commission, after analyzing the details and 
    duly considering [reason], hereby approves Rs.XX.XX lakh / [approves/disallows] 
    the claim of the licensee for [item] for the year [FY].</p>"

CRITICAL: 
- All Rs. values in STEPS 1-4 must come from Petition PDF (PDF 2), NOT from reference order.
- For items where the commission allows full claim: say so with reason (claim found to be in order).
- For disallowances: state the exact regulation ceiling, the excess amount, and why it's disallowed.
- Never just say "Commission approves Rs.X" without the reasoning in Step 3.


SECTION 4 - DISTRIBUTION LOSS (paras, MINIMUM 6 paragraphs):
Para 1: Explain what distribution loss means for {licensee}'s network, the input-output measurement methodology.
Para 2: The target distribution loss % set by the Commission in the MYT/ARR order for FY {fy}, and the actual distribution loss % achieved by the licensee per the petition.
Para 3: Quote Regulation 73 in full as <blockquote>Regulation 73: ...</blockquote>.
Para 4: Detailed arithmetic calculation of savings or excess loss:
  - Input energy (MU) and output energy (MU)
  - Actual loss % vs target loss %
  - MUs saved or lost = (Target% - Actual%) x Input MU / 100
  - Rs saved/lost = MUs x average power purchase cost per unit
Para 5: Commission's decision — whether savings are credited or excess loss is penalized, any mitigating factors considered.
Para 6: Final approved/disallowed amount on account of distribution loss.
TABLE 4 - Distribution Loss: Rows: Input Energy (MU), Output Energy (MU), Distribution Loss (MU), Distribution Loss (%), Target Distribution Loss (%), Savings/(Excess Loss) (MU), Rate (Rs/kWh), Savings/(Penalty) (Rs. Lakhs).

SECTION 5 - POWER PURCHASE COST (MINIMUM 5 paragraphs):
Para 1: Sources of power for {licensee} — KSEB grid supply, any captive/renewable sources, voltage of supply, nature of open access if any.
Para 2: Total units purchased in FY {fy} and total cost. Compare actual per-unit purchase cost vs approved in the ARR order.
Para 3: Analysis of any deviation — whether increased purchase was due to consumer growth or load management issues.
Para 4: Regulation citation for power purchase cost approval methodology.
Para 5: Commission's decision — approved units and cost, any disallowance.
TABLE 5 - Power Purchase Cost: Columns: Particulars | Claimed | Approved. Rows: Units Purchased (MU), Rate (Rs/kWh), Total Cost (Rs. Lakhs).

SECTION 6 - O&M EXPENSES (MINIMUM 20 paragraphs across 4 sub-sections — THIS IS THE LARGEST SECTION):

6a. O&M OVERVIEW (2 paragraphs):
Para: Introduce the three components of O&M — Employee Cost, R&M, A&G — and provide the summary overview.
TABLE 6 - O&M Summary: Employee Cost | R&M | A&G | Total — show Claimed and Approved.

6b. EMPLOYEE COST (MINIMUM 6 paragraphs):
Para 1: Total establishment — number of permanent employees by grade/category, contract staff, deputationists.
Para 2: Basic pay, DA, HRA, CCA, special allowances — total salary bill, comparison with previous year.
Para 3: PF/EPF contribution percentage, amount contributed.
Para 4: Gratuity, leave encashment, ex-gratia, bonus — statutory and non-statutory payments.
Para 5: Medical reimbursement, uniform allowance, other perquisites.
Para 6: Commission's analysis — what norm-based ceiling applies (cite Tariff Regulation), what is approved, what is disallowed and why.
TABLE 7 - Employee Expenses: Detailed rows for Basic Pay, DA, HRA, Other Allowances, PF, Gratuity, Leave Encashment, Medical, Bonus, Ex-Gratia, Others, Total.

6c. REPAIR & MAINTENANCE EXPENSES (MINIMUM 5 paragraphs):
Para 1: Scope of maintenance — distribution lines length maintained, transformer count, substation equipment, metering infrastructure, civil structures.
Para 2: Specific major maintenance activities carried out in FY {fy}.
Para 3: Year-on-year trend — compare with FY 2022-23 and FY 2023-24 actuals.
Para 4: Reasonableness check — per-km or per-consumer benchmark comparison.
Para 5: Commission's analysis and approved amount.
TABLE 8 - R&M Expenses: Rows: Lines & Cables, Transformers, Meters, Substation Equipment, Buildings & Civil, Vehicles, Other, Total.

6d. ADMINISTRATION & GENERAL EXPENSES (MINIMUM 6 paragraphs):
Para 1: Overview of A&G categories.
Para 2: Insurance premium — assets insured, premium rate, reasonableness vs. similar utilities.
Para 3: Audit fees (statutory auditor, internal auditor, tax auditor) — amounts and reasonableness.
Para 4: Legal expenses, consultancy fees, filing fees, BEE energy audit fee.
Para 5: Communication (telephone, internet, postage), printing & stationery, books/periodicals.
Para 6: Conveyance, vehicle running, miscellaneous — Commission's line-by-line decision.
TABLE 9 - A&G Expenses: One row per item — Insurance, Audit Fees, Legal Expenses, BEE Fee, Telephone/Postage, Printing, Conveyance, Miscellaneous, Total.

TARGET: Part B must produce approximately 12 PRINTED A4 PAGES of HTML content.
Do NOT include signature block. Stop after A&G expenses.
Write EVERY paragraph in full with 4-6 sentences per paragraph — do NOT compress."""

    logger.info("=== PART B: Distribution Loss + Power Purchase + O&M ===")
    t0 = time.time()
    ref_b, pet_b = _upload_pdfs()
    parts_b = [types.Part.from_uri(file_uri=ref_b.uri, mime_type="application/pdf")]
    if pet_b:
        parts_b.append(types.Part.from_uri(file_uri=pet_b.uri, mime_type="application/pdf"))
    parts_b.append(types.Part.from_text(text=prompt_b))
    part_b_html = _call_with_retry(parts_b, "Part B")
    logger.info(f"Part B: {len(part_b_html)} chars in {time.time()-t0:.1f}s")
    _delete_pdfs(ref_b, pet_b)

    tail_b = part_b_html[-2500:] if len(part_b_html) > 2500 else part_b_html

    # ==========================================================================
    # PART C: Depreciation + Interest + Revenue + ARR Summary + Orders + Signature
    # ==========================================================================
    prompt_c = f"""You are an expert legal drafter for KSERC.

TASK: Generate PART C (FINAL PART) of a Truing-Up Order for M/s {licensee} for FY {fy}.
Parts A and B are already written. This is the final continuation. End with the signature block.

INPUTS:
- PDF 1 = Reference Order OP 82/2023 - FORMAT TEMPLATE
- PDF 2 = Petition by M/s {licensee} for FY {fy} - DATA SOURCE
- Audited Data:
{data_block}

{HTML_RULES}

CONTEXT - last 2500 chars of Part B:
---
{tail_b}
---

Continue paragraph numbering sequentially from where Part B ended.


MANDATORY 4-STEP JUSTIFICATION STRUCTURE (for EVERY cost head and revenue item):

For each item (Employee Cost, R&M, Depreciation, Interest, etc.) write exactly:
  STEP 1 - CLAIMED: "The licensee has claimed Rs.XX.XX lakh on account of [item]. 
    [Extract exact details from Petition PDF: amount, basis given, how calculated]."
  STEP 2 - REGULATION: "As per Regulation [NN] of KSERC (Terms and Conditions for 
    Determination of Tariff) Regulations, 2021, [quote the applicable norm/formula]."
  STEP 3 - ANALYSIS: "The Commission has examined the claim. [State what verification 
    was done, e.g. comparison with norm, previous year actuals, KSEB verification, 
    calculation recheck]. [State if claim matches norm or deviates, and by how much]."
  STEP 4 - DECISION (bold+italic using commission-decision class):
    "<p class='commission-decision'>The Commission, after analyzing the details and 
    duly considering [reason], hereby approves Rs.XX.XX lakh / [approves/disallows] 
    the claim of the licensee for [item] for the year [FY].</p>"

CRITICAL: 
- All Rs. values in STEPS 1-4 must come from Petition PDF (PDF 2), NOT from reference order.
- For items where the commission allows full claim: say so with reason (claim found to be in order).
- For disallowances: state the exact regulation ceiling, the excess amount, and why it's disallowed.
- Never just say "Commission approves Rs.X" without the reasoning in Step 3.


SECTION 7 - DEPRECIATION (MINIMUM 4 paragraphs):
Para 1: Gross Fixed Assets composition — explain each asset category (land, buildings, lines & cables, plant & machinery, meters, vehicles, furniture & fixtures) and their opening values for FY {fy}.
Para 2: Methodology — straight-line depreciation per KSERC Tariff Regulations 2021 Schedule of Rates, cite the regulation.
Para 3: Asset-wise comparison of claimed vs approved depreciation — explain reasons for any variance.
Para 4: Commission's final approved depreciation amount.
TABLE 10 - Depreciation: Columns: Sl.No | Asset Category | Rate (%) | Opening GFA (Rs.Lakh) | Depreciation Claimed | Depreciation Approved.

SECTION 8 - INTEREST AND FINANCE CHARGES (MINIMUM 6 paragraphs):
Para 1: Normative loan — 70% of GFA as per Tariff Regulations. Opening normative loan for FY {fy}, additions during year (capex × 70%), repayments (1/10 of normative loan or actual), closing balance, average loan for year.
Para 2: Quote Regulation on normative loan and interest computation in <blockquote>.
Para 3: Interest on long-term loans — SBI base rate used, interest amount computed.
TABLE 11 - Interest on LT Loans computation.
Para 4: Working capital interest — detailed component-wise computation per regulation: O&M store (1 month), receivables (2 months), maintenance spares (15% of R&M), less consumer security deposits. Total working capital × SBI rate.
TABLE 12 - Working Capital Computation: each component shown.
Para 5: Interest on Consumer Security Deposits — deposit balance, rate applied, amount.
Para 6: Bank charges and other finance charges — whether approved or disallowed.
Para 7: Total approved interest and finance charges.

SECTION 9 - CARRYING COST ON PAST REVENUE GAPS (MINIMUM 3 paragraphs):
Para 1: State the cumulative revenue gap approved through FY 2022-23. Cite the previous order.
Para 2: Carrying cost calculation — gap × SBI MCLR rate × appropriate months.
Para 3: Commission's decision — amount approved for FY {fy}.

SECTION 10 - RETURN ON NET FIXED ASSETS (MINIMUM 3 paragraphs):
Para 1: Opening NFA = Opening GFA minus accumulated depreciation as of 31 March of previous year. State the actual opening NFA for FY {fy}.
Para 2: Cite Regulation 28 — RoNFA = 5.50% of opening NFA. Show calculation.
Para 3: Claimed vs approved RoNFA, Commission's decision.

SECTION 11 - REVENUE FROM SALE OF POWER (MINIMUM 4 paragraphs):
Para 1: Category-wise energy sales and revenue — actual tariff revenue collected during FY {fy}.
Para 2: Average realization per kWh — compare with approved tariff rates in tariff order.
Para 3: Check whether revenue claimed matches energy sales × approved tariff.
Para 4: Commission's approved revenue from sale of power.
TABLE 13 - Revenue from Sale: Columns: Category | Units Sold (MU) Claimed | Revenue (Rs.Lakh) Claimed | Avg Tariff (Rs/kWh) Claimed | Revenue (Rs.Lakh) Approved.

SECTION 12 - WHEELING CHARGES (MINIMUM 2 paragraphs):
Para 1: Details of open access consumers and Smart City wheeling arrangements, units wheeled, wheeling charge rate.
Para 2: Total wheeling income and Commission's approval.

SECTION 13 - NON-TARIFF INCOME (MINIMUM 3 paragraphs):
Para 1: Delayed payment surcharge — how computed, amount.
Para 2: Meter rent, miscellaneous receipts, interest on deposits.
Para 3: Commission's approved non-tariff income.
TABLE 14 - Non-Tariff Income: Particulars | Claimed | Approved (one row per item).

SECTION 14 - APPROVED ARR AND REVENUE GAP (MINIMUM 4 paragraphs + COMPREHENSIVE TABLE):
Para 1: Summarize all approved expense items.
Para 2: Summarize all approved revenue items.
Para 3: Revenue gap/surplus calculation and comparison with petition claim.
Para 4: How the gap will be carried forward and treated in the next tariff revision.
TABLE 15 - COMPLETE ARR & Revenue Summary (MOST IMPORTANT TABLE — must be comprehensive):
Columns: Sl.No | Particulars | Claimed by Licensee | Approved by Commission
Rows (ALL of these):
  EXPENDITURE:
  1. Power Purchase Cost
  2. Employee Cost
  3. Repair & Maintenance
  4. Administration & General Expenses
  5. Depreciation
  6. Interest on Long Term Loans
  7. Interest on Working Capital
  8. Interest on Consumer Security Deposits
  9. Bank & Finance Charges
  10. Carrying Cost on Revenue Gap
  11. Return on Net Fixed Assets
  12. Other Debits
  13. Taxes & Duties
  A. TOTAL APPROVED EXPENDITURE (total-row)
  REVENUE:
  14. Revenue from Sale of Power
  15. Wheeling Charges
  16. Non-Tariff Income
  17. Other Income
  B. TOTAL REVENUE (total-row)
  C. REVENUE GAP (A-B) (total-row, bold)
  D. Cumulative Revenue Gap from previous years
  E. TOTAL CUMULATIVE REVENUE GAP (total-row, bold)

SECTION 15 - ORDERS OF THE COMMISSION (MINIMUM 4 paragraphs):
Para 1: Operative order 1 — approve total expenditure of Rs. X lakhs for FY {fy}.
Para 2: Operative order 2 — approve total revenue of Rs. Y lakhs for FY {fy}.
Para 3: Operative order 3 — revenue gap/surplus of Rs. Z lakhs to be carried forward and treated in next tariff revision.
Para 4: Direction to licensee — submit audited accounts, update asset register, submit compliance report by specified date.

SECTION 16 - SIGNATURE BLOCK:
<table class="sig-table">
  <tr><td>Sd/-</td><td>Sd/-</td><td>Sd/-</td></tr>
  <tr><td><b>Sri. T.K Jose</b></td><td><b>Adv. A. J. Wilson</b></td><td><b>Sri. B. Pradeep</b></td></tr>
  <tr><td><b>Chairman</b></td><td><b>Member</b></td><td><b>Member</b></td></tr>
</table>
<div class="secretary-block">
  <p><b>Approved for issue</b></p>
  <p>Sd/-</p>
  <p><b>C.R.Satheesh Chandran</b></p>
  <p><b>Secretary</b></p>
</div>

TARGET: Part C must produce approximately 10 PRINTED A4 PAGES of HTML content.
Write all numbers from the Petition PDF — not from reference order.
Write every paragraph in full with minimum 4-6 sentences per paragraph — do NOT compress.
This is the FINAL part — include the complete signature block at the very end."""

    logger.info("=== PART C: Depreciation + Interest + Revenue + ARR Summary + Orders + Signature ===")
    t0 = time.time()
    ref_c, pet_c = _upload_pdfs()
    parts_c = [types.Part.from_uri(file_uri=ref_c.uri, mime_type="application/pdf")]
    if pet_c:
        parts_c.append(types.Part.from_uri(file_uri=pet_c.uri, mime_type="application/pdf"))
    parts_c.append(types.Part.from_text(text=prompt_c))
    part_c_html = _call_with_retry(parts_c, "Part C")
    logger.info(f"Part C: {len(part_c_html)} chars in {time.time()-t0:.1f}s")
    _delete_pdfs(ref_c, pet_c)

    combined_html = part_a_html + "\n\n" + part_b_html + "\n\n" + part_c_html
    logger.info(f"Combined: {len(combined_html)} chars ({len(part_a_html)} + {len(part_b_html)} + {len(part_c_html)})")
    return combined_html


def _postprocess_html(raw_html: str) -> str:
    """
    Clean up the Gemini HTML output before rendering to PDF.
    """
    html = raw_html

    # 1. Strip code fences if Gemini wrapped in ```html ... ```
    html = re.sub(r'^```(?:html)?\s*\n?', '', html)
    html = re.sub(r'\n?```\s*$', '', html)

    # 2. Remove meta-commentary preamble (anything before first <h1> or <table or <p>)
    first_tag = re.search(r'<(?:h[1-3]|table|p|div)', html, re.IGNORECASE)
    if first_tag and first_tag.start() > 0:
        preamble = html[:first_tag.start()].strip()
        # Only strip if preamble looks like commentary (not empty)
        if preamble and not preamble.startswith('<'):
            logger.info(f"Stripping preamble ({len(preamble)} chars)")
            html = html[first_tag.start():]

    # 3. Remove any <html>, <head>, <body> wrappers (we add our own)
    html = re.sub(r'</?html[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</?head[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</?body[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<meta[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<!DOCTYPE[^>]*>', '', html, flags=re.IGNORECASE)

    # 4. Fix any remaining markdown bold **text** → <b>text</b>
    html = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', html)

    # 5. Fix markdown italic *text* → <i>text</i>  (single asterisks)
    html = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', html)

    # 6. Convert any leftover markdown tables that Gemini may produce
    #    (this is a fallback — ideally Gemini produces clean HTML)
    if '| :---' in html or '|:---' in html:
        logger.warning("Gemini output contains markdown tables — attempting conversion")
        html = _convert_markdown_tables_to_html(html)

    # 7. Compact header-table spacer rows — replace &nbsp; spacer rows with tiny ones
    #    Gemini uses <tr><td colspan="3">&nbsp;</td></tr> which are too tall
    html = re.sub(
        r'<tr>\s*<td\s+colspan="3">\s*&nbsp;\s*</td>\s*</tr>',
        '<tr class="spacer-row"><td colspan="3" style="padding:2px 0;line-height:0.3;font-size:4pt;">&nbsp;</td></tr>',
        html, flags=re.IGNORECASE
    )

    # 8. Wrap each data-table + preceding captions in <div class="table-wrapper">
    #    This groups table-caption + table-subcaption + table-unit + table together for page-break control
    html = re.sub(
        r'(<p\s+class="table-caption"[^>]*>.*?</p>\s*'
        r'(?:<p\s+class="table-subcaption"[^>]*>.*?</p>\s*)?'
        r'(?:<p\s+class="table-unit"[^>]*>.*?</p>\s*)?'
        r'<table\s+class="data-table"[^>]*>.*?</table>)',
        r'<div class="table-wrapper">\1</div>',
        html, flags=re.IGNORECASE | re.DOTALL
    )

    return html.strip()


def _convert_markdown_tables_to_html(text: str) -> str:
    """
    Fallback: Convert any remaining markdown tables in the text to HTML tables.
    This handles cases where Gemini still outputs | pipe | tables | despite instructions.
    """
    lines = text.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect start of a markdown table (line with | separators)
        if '|' in line and line.startswith('|') and line.endswith('|'):
            # Collect all table lines
            table_lines = []
            while i < len(lines):
                tl = lines[i].strip()
                if '|' in tl and tl.startswith('|'):
                    table_lines.append(tl)
                    i += 1
                else:
                    break
            
            # Convert to HTML table
            result.append('<table class="data-table">')
            for row_idx, row_line in enumerate(table_lines):
                # Skip separator rows like | :--- | :--- |
                if re.match(r'^\|\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|$', row_line):
                    continue
                
                cells = [c.strip() for c in row_line.split('|')[1:-1]]
                tag = 'th' if row_idx == 0 else 'td'
                
                result.append('  <tr>')
                for cell in cells:
                    # Check if cell looks numeric
                    clean_cell = cell.replace('<b>', '').replace('</b>', '').replace('<br>', ' ').replace('<br/>', ' ').strip()
                    is_numeric = bool(re.match(r'^-?[\d,]+\.?\d*$', clean_cell.replace('(', '').replace(')', '')))
                    
                    cls = ' class="num"' if is_numeric and tag == 'td' else ''
                    result.append(f'    <{tag}{cls}>{cell}</{tag}>')
                result.append('  </tr>')
            
            result.append('</table>')
        else:
            result.append(lines[i])
            i += 1
    
    return '\n'.join(result)


def draft_order(state: dict) -> dict:
    """
    LangGraph node function.

    Generates the final KSERC-format Truing-Up Order PDF from the
    audited state data, using Gemini 2.5 Pro with reference PDF template.
    Gemini outputs clean HTML which is rendered to PDF via xhtml2pdf.
    """
    licensee = state["licensee_name"]
    fy = state["financial_year"]

    logger.info(f"Drafting order for {licensee} FY {fy} using HTML-based approach")

    # 1. Generate HTML document via Gemini with reference PDF
    raw_html = _generate_document_with_gemini(state)
    logger.info("Received HTML from Gemini. Length: %d chars", len(raw_html))

    # 2. Post-process / clean up the HTML
    body_html = _postprocess_html(raw_html)
    logger.info("Post-processed HTML. Length: %d chars", len(body_html))

    # 3. Wrap in full HTML document with CSS
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        {KSERC_CSS}
    </style>
</head>
<body>
    {body_html}
</body>
</html>"""

    # Always save the raw Gemini output and the final HTML for reference/debugging
    output_dir = Path(__file__).resolve().parents[2] / "output_orders"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = licensee.replace(" ", "_").replace("/", "-")
    
    md_path = output_dir / f"KSERC_TrueUp_Order_{safe_name}_FY_{fy}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(raw_html)
    logger.info(f"Raw Gemini output saved at: {md_path}")

    html_path = output_dir / f"KSERC_TrueUp_Order_{safe_name}_FY_{fy}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    logger.info(f"Final HTML saved at: {html_path}")

    # 4. Render PDF using Playwright headless Chromium
    logger.info("Converting HTML to PDF with Playwright...")
    filename = f"KSERC_TrueUp_Order_{safe_name}_FY_{fy}.pdf"
    output_path = output_dir / filename
    
    # Check if the PDF file is locked by opening in append mode
    final_pdf_path = output_path
    if output_path.exists():
        try:
            with open(output_path, "a"):
                pass
        except PermissionError:
            import datetime
            ts = datetime.datetime.now().strftime("%H%M%S")
            alt_filename = f"KSERC_TrueUp_Order_{safe_name}_FY_{fy}_{ts}.pdf"
            final_pdf_path = output_dir / alt_filename
            logger.warning(f"Original PDF is locked. Writing to: {final_pdf_path}")

    try:
        html_uri = f"file:///{str(html_path).resolve().as_posix()}"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(html_uri, wait_until='networkidle')
            page.pdf(
                path=str(final_pdf_path),
                format='A4',
                margin={
                    'top': '3.0cm',
                    'bottom': '3.0cm',
                    'left': '3.0cm',
                    'right': '3.0cm'
                },
                print_background=True,
                display_header_footer=True,
                header_template='<span style="font-size: 8px;"></span>',
                footer_template='<div style="font-size: 10px; width: 100%; text-align: center;"><span class="pageNumber"></span></div>'
            )
            browser.close()
        logger.info(f"Successfully generated PDF at: {final_pdf_path}")
    except Exception as e:
        logger.error(f"Error generating PDF with Playwright: {e}")

    state["output_pdf_path"] = str(output_path)
    return state
