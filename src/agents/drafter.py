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

try:
    from weasyprint import HTML as WeasyHTML
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from src.gemini_client import generate_with_pdf, get_client, get_api_key_client
from src.config import GEMINI_MODEL

logger = logging.getLogger(__name__)

# Path to the reference KSERC order that serves as the exact template
_BASE_DIR = Path(__file__).resolve().parents[2]
_DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", str(_BASE_DIR / ".." / "Documents"))).resolve()
REFERENCE_ORDER_PDF = _DOCUMENTS_DIR / "Infopark True-Up 2022-23 (OP 82 2023).pdf"

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

    /* ── Data tables (financial data) — matches reference KSERC order ── */
    table.data-table {
        border-collapse: collapse;
        width: 100%;
        table-layout: fixed;
        margin-top: 10px;
        margin-bottom: 18px;
        font-size: 10pt;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    table.data-table th,
    table.data-table td {
        border: 1px solid #000;
        padding: 3px 5px;
        font-size: 10pt;
        vertical-align: middle;
        line-height: 1.3;
    }
    table.data-table th {
        font-weight: bold;
        text-align: center;
        background: none;
        vertical-align: middle;
    }
    table.data-table td {
        text-align: left;
    }
    table.data-table td.num {
        text-align: right;
        white-space: nowrap;
    }
    table.data-table td.center-cell {
        text-align: center;
    }
    table.data-table tr.total-row td {
        font-weight: bold;
        border-top: 1px solid #000;
    }
    .table-wrapper {
        margin-bottom: 8px;
    }

    /* ── Table caption (ABOVE table, centered, bold) ────── */
    .table-caption {
        text-align: center;
        font-weight: bold;
        font-size: 12pt;
        margin-bottom: 0;
        margin-top: 14px;
        line-height: 1.4;
    }
    .table-subcaption {
        text-align: center;
        font-weight: normal;
        font-size: 11pt;
        margin-bottom: 2px;
        margin-top: 1px;
        line-height: 1.4;
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
        margin-top: 14px;
        margin-bottom: 14px;
        font-style: italic;
        border-left: none;
        padding-left: 0;
        font-size: 12pt;
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

    # Prefer API key client (avoids Vertex AI rate limits)
    # Falls back to Vertex AI client if no API key
    client = get_api_key_client() or get_client()
    logger.info(f"Drafter using client: {'API key' if get_api_key_client() else 'Vertex AI'}")
    licensee = state.get("licensee_name", "Licensee")
    fy = state.get("financial_year", "2024-25")

    # Compute previous financial years (e.g. "2024-25" -> "2023-24", "2022-23")
    try:
        start_year = int(fy.split("-")[0])
        prev_start = start_year - 1
        prev_end = start_year % 100  # e.g. 2024 -> 24
        prev_fy = f"{prev_start}-{prev_end:02d}"
        fy_minus_2_start = start_year - 2
        fy_minus_2_end = (start_year - 1) % 100
        fy_minus_2 = f"{fy_minus_2_start}-{fy_minus_2_end:02d}"
    except Exception:
        prev_fy = fy  # fallback
        fy_minus_2 = fy

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
    myt_norms   = state.get("myt_baseline_norms", {})
    detailed_tb = state.get("detailed_tables", {}) or {}

    # Fallback: load MYT norms from JSON/DB if not in state
    myt_loader_instance = None
    if not myt_norms:
        try:
            from src.knowledge.myt_loader import MYTLoader
            myt_loader_instance = MYTLoader()
            myt_norms = myt_loader_instance.load_myt_baselines(licensee, fy)
            if myt_norms:
                logger.info(f"Loaded MYT norms from fallback: {len(myt_norms)} fields for {licensee} FY {fy}")
            else:
                logger.warning(f"No MYT norms found for {licensee} FY {fy} — ARR columns will show 0.00")
        except Exception as e:
            logger.warning(f"MYT fallback loading failed: {e}")

    # Load previous year MYT norms (for comparison tables like Table 2, 8)
    prev_myt_norms = {}
    try:
        if not myt_loader_instance:
            from src.knowledge.myt_loader import MYTLoader
            myt_loader_instance = MYTLoader()
        prev_myt_norms = myt_loader_instance.load_myt_baselines(licensee, prev_fy)
        if prev_myt_norms:
            logger.info(f"Loaded previous year MYT norms: {len(prev_myt_norms)} fields for {licensee} FY {prev_fy}")
        # Also load full licensee data for control period context
        full_licensee_myt = myt_loader_instance.load_full_licensee_data(licensee)
        myt_order_ref = full_licensee_myt.get("myt_order", "")
        myt_control_period = full_licensee_myt.get("control_period", "")
    except Exception:
        full_licensee_myt = {}
        myt_order_ref = ""
        myt_control_period = ""

    # ── Load historical trued-up data from Firestore ────────────────────────
    historical_data = {}
    try:
        from src.tools.db import get_all_precedents
        all_precedents = get_all_precedents(licensee)
        for hist_fy in [prev_fy, fy_minus_2]:
            if hist_fy in all_precedents:
                historical_data[hist_fy] = all_precedents[hist_fy]
                logger.info(f"Loaded historical trued-up data for {licensee} FY {hist_fy}")
            else:
                logger.info(f"No historical trued-up data for {licensee} FY {hist_fy}")
    except Exception as e:
        logger.warning(f"Failed to load historical data: {e}")

    # ── 4-column data block: MYT ARR | Claimed | Approved | Variance ──────────
    # This is the AUTHORITATIVE source for all table values and justification numbers.
    # Gemini MUST use these exact numbers — NEVER hallucinate from the reference PDF.
    data_block  = "=== AUTHORITATIVE FINANCIAL DATA — USE THESE EXACT NUMBERS (Rs. Lakhs) ===\n"
    data_block += "\nCRITICAL: Column 'MYT ARR Approved' is the Commission's approved ceiling for this year.\n"
    data_block += "          Column 'For Truing Up (Claimed)' is what the licensee claimed in the petition.\n"
    data_block += "          Column 'Trued Up (Approved)' is what the Commission approves after prudence check.\n"
    data_block += "          Variance = Approved minus Claimed (negative = disallowance).\n\n"

    col_w = 42
    data_block += f"{'Component':<{col_w}} {'MYT ARR Approved':>18} {'For TrUp Claimed':>18} {'TrUp Approved':>15} {'Variance':>12}\n"
    data_block += "-" * (col_w + 67) + "\n"
    total_c, total_a, total_myt = 0.0, 0.0, 0.0
    for k in exp_keys:
        c = float(claimed_exp.get(k, 0.0) or 0.0)
        a = float(approved_exp.get(k, 0.0) or 0.0)
        m = float(myt_norms.get(k, 0.0) or 0.0)
        if c > 0 or a > 0 or m > 0:
            name = k.replace("_", " ").title()
            data_block += f"{name:<{col_w}} {m:>18.2f} {c:>18.2f} {a:>15.2f} {(a-c):>12.2f}\n"
            total_c   += c
            total_a   += a
            total_myt += m
    data_block += "-" * (col_w + 67) + "\n"
    data_block += f"{'TOTAL EXPENDITURE':<{col_w}} {total_myt:>18.2f} {total_c:>18.2f} {total_a:>15.2f} {(total_a-total_c):>12.2f}\n\n"

    # ── Revenue rows ──────────────────────────────────────────────────────────
    data_block += "REVENUES (approved = claimed unless stated otherwise):\n"
    rev_total = 0.0
    myt_rev   = {
        "revenue_from_sale": float(myt_norms.get("revenue_from_sale", 0.0) or 0.0),
        "wheeling_charges":  float(myt_norms.get("wheeling_charges",  0.0) or 0.0),
        "non_tariff_income": float(myt_norms.get("non_tariff_income", 0.0) or 0.0),
    }
    approved_rev = state.get("approved_revenues", {})
    for k in rev_keys:
        c = float(claimed_rev.get(k, 0.0) or 0.0)
        a = float(approved_rev.get(k, c) or c)
        m = float(myt_rev.get(k, 0.0) or 0.0)
        if c > 0 or a > 0:
            name = k.replace("_", " ").title()
            data_block += f"  {name}: MYT={m:.2f}  Claimed={c:.2f}  Approved={a:.2f}\n"
            rev_total += a
    data_block += f"  TOTAL APPROVED REVENUE: {rev_total:.2f}\n\n"

    # ── Summary ───────────────────────────────────────────────────────────────
    total_claimed_exp = float(state.get('total_claimed_expenditure', total_c) or total_c)
    total_approved_exp = float(state.get('total_approved_expenditure', total_a) or total_a)
    total_claimed_rev = float(state.get('total_claimed_revenue', rev_total) or rev_total)
    data_block += f"Total Claimed Expenditure   : {total_claimed_exp:.2f}\n"
    data_block += f"Total Approved Expenditure  : {total_approved_exp:.2f}\n"
    data_block += f"Total Approved Revenue      : {rev_total:.2f}\n"
    revenue_gap = state.get('final_revenue_gap_surplus', rev_total - total_a)
    gap_label   = "Surplus" if revenue_gap >= 0 else "Gap"
    data_block += f"Revenue {gap_label}            : {abs(revenue_gap):.2f} lakh\n"

    # ── TABLE 31 EXACT VALUES (Gemini MUST use these exact numbers) ─────────
    data_block += "\n=== TABLE 31 - TRUED UP INCOME & EXPENDITURE (USE THESE EXACT VALUES) ===\n"
    data_block += "Gemini: You MUST use these exact values for the Trued Up column in Table 31.\n"
    data_block += "Do NOT calculate or derive these values yourself. Copy them exactly.\n\n"
    data_block += f"EXPENDITURE ROWS (Trued Up = Approved):\n"
    for key in exp_keys:
        a = float(approved_exp.get(key, claimed_exp.get(key, 0.0)) or 0.0)
        c = float(claimed_exp.get(key, 0.0) or 0.0)
        m = float(myt_norms.get(key, 0.0) or 0.0)
        label = key.replace("_", " ").title()
        if c > 0 or a > 0:
            data_block += f"  {label}: ARR&ERC={m:.2f}  Claimed={c:.2f}  TruedUp={a:.2f}\n"
    data_block += f"  TOTAL EXPENDITURE: ARR&ERC=---  Claimed={total_claimed_exp:.2f}  TruedUp={total_approved_exp:.2f}\n\n"
    
    data_block += f"REVENUE ROWS (Trued Up = Approved):\n"
    for k in rev_keys:
        c = float(claimed_rev.get(k, 0.0) or 0.0)
        a = float(approved_rev.get(k, c) or c)
        if c > 0 or a > 0:
            name = k.replace("_", " ").title()
            data_block += f"  {name}: Claimed={c:.2f}  TruedUp={a:.2f}\n"
    data_block += f"  TOTAL REVENUE: Claimed={total_claimed_rev:.2f}  TruedUp={rev_total:.2f}\n\n"
    
    # Calculate claimed gap too
    claimed_gap = total_claimed_rev - total_claimed_exp
    claimed_gap_label = "Surplus" if claimed_gap >= 0 else "Gap"
    approved_gap_label = "Surplus" if revenue_gap >= 0 else "Gap"
    data_block += f"  Revenue ({claimed_gap_label}) for Claimed column: {abs(claimed_gap):.2f} lakh\n"
    data_block += f"  Revenue ({approved_gap_label}) for TruedUp column: {abs(revenue_gap):.2f} lakh\n"
    data_block += f"  IMPORTANT: Do NOT use negative signs. Write the value as a POSITIVE number.\n"
    data_block += f"  Use the row label 'Revenue (Gap)/Surplus' and show the value as a positive number.\n"
    data_block += "=== END TABLE 31 VALUES ===\n"

    # ── Court hearing details (if provided by user) ──────────────────────
    court_hearing = state.get("court_hearing", {})
    if court_hearing and court_hearing.get("hearing_date"):
        data_block += "\n=== COURT HEARING / ORAL SUBMISSIONS ===\n"
        data_block += f"Hearing Date: {court_hearing.get('hearing_date', 'Not specified')}\n"
        submissions = court_hearing.get("licensee_submissions", [])
        if submissions:
            data_block += "Licensee Submissions:\n"
            for i, sub in enumerate(submissions, 1):
                data_block += f"  {i}. {sub}\n"
        resp = court_hearing.get("respondent_position", "")
        if resp:
            data_block += f"Respondent Position: {resp}\n"
        obs = court_hearing.get("commission_observations", "")
        if obs:
            data_block += f"Commission Observations: {obs}\n"
        data_block += "=== END COURT HEARING ===\n"

    # ── Disallowances with full justification text ────────────────────────────
    disallowances = state.get("disallowance_log", [])
    if disallowances:
        data_block += "\n=== DISALLOWANCES & DETAILED JUSTIFICATIONS (USE THESE EXACT NUMBERS) ===\n"
        for d in disallowances:
            claimed_d  = d.get('claimed', 0.0)
            approved_d = d.get('approved', 0.0)
            variance_d = approved_d - claimed_d
            data_block += f"\n  ITEM: {d.get('item', d.get('component', 'Unknown'))}\n"
            data_block += f"    Claimed    : Rs. {claimed_d:.2f} Lakhs\n"
            data_block += f"    Approved   : Rs. {approved_d:.2f} Lakhs\n"
            data_block += f"    Variance   : Rs. {variance_d:.2f} Lakhs ({'disallowed' if variance_d < 0 else 'additional approved'})\n"
            data_block += f"    Justification: {d.get('justification', 'N/A')}\n"
            # Include any additional details from the log
            for extra_key in ['myt_norm', 'norm_used', 'opening_loan', 'interest_rate', 'equity_base',
                               'efficiency_gain', 'licensee_share', 'consumer_share',
                               'bee_fee', 'interim_relief', 'one_time_allowed',
                               'special_allowance', 'penalty', 'savings_lakh_kwh']:
                if extra_key in d:
                    data_block += f"    {extra_key}: {d[extra_key]}\n"

    # ── Distribution loss details ─────────────────────────────────────────────
    actual_loss = state.get('claimed_distribution_loss_pct', 0.0)
    target_loss = state.get('target_distribution_loss_pct', 0.0)
    data_block += f"\n=== DISTRIBUTION LOSS ===\n"
    data_block += f"  Actual (Claimed) : {actual_loss:.2f}%\n"
    data_block += f"  Target (MYT Norm): {target_loss:.2f}%\n"
    if actual_loss > 0 and target_loss > 0:
        if actual_loss < target_loss:
            data_block += f"  Status: EFFICIENCY GAIN (actual < target) → licensee retains 2/3 of savings\n"
        else:
            data_block += f"  Status: EXCESS LOSS (actual > target) → penalty applied per Regulation 73(3)\n"
    ei = state.get('energy_input_mu', 0.0)
    es = state.get('energy_sold_mu', 0.0)
    ew = state.get('energy_wheeled_mu', 0.0)
    if ei > 0:
        data_block += f"  Energy Input (MU)     : {ei:.4f}\n"
        data_block += f"  Energy Sold (MU)      : {es:.4f}\n"
        data_block += f"  Energy Wheeled (MU)   : {ew:.4f}\n"

    # ── Special items from detailed tables (BEE fee, one-time items, etc.) ────
    special_items = {}
    if detailed_tb:
        # BEE energy audit fee
        bee_fee = float(myt_norms.get('bee_energy_audit_fee', 0.0) or
                        detailed_tb.get('bee_energy_audit_fee', 0.0) or 0.0)
        if bee_fee > 0:
            special_items['BEE Energy Audit Fee (Change in Law — allow over norm)'] = bee_fee
        # Interim relief / DA arrears
        interim = float(detailed_tb.get('interim_relief', 0.0) or 0.0)
        if interim > 0:
            special_items['Interim Relief / DA Arrears (allow over norm)'] = interim
        # One-time R&M items
        one_time_rm = float(detailed_tb.get('one_time_rm', 0.0) or 0.0)
        if one_time_rm > 0:
            special_items['One-time R&M (allowed over norm after prudence check)'] = one_time_rm
        # Commission opening normative loan (from precedent / previous order)
        opening_loan = float(detailed_tb.get('approved_opening_normative_loan', 0.0) or 0.0)
        if opening_loan > 0:
            special_items['Commission-approved Opening Normative Loan'] = opening_loan
        # Equity base
        equity_base = float(detailed_tb.get('approved_equity_base', 0.0) or 0.0)
        if equity_base > 0:
            special_items['Commission-approved Equity Base'] = equity_base

    if special_items:
        data_block += "\n=== SPECIAL ITEMS & ALLOWANCES OVER NORM ===\n"
        for label, val in special_items.items():
            data_block += f"  {label}: Rs. {val:.2f} Lakhs\n"

    # ── MYT Order Reference & Previous Year ARR Norms ─────────────────────────
    if myt_order_ref or myt_control_period:
        data_block += f"\n=== MYT ORDER REFERENCE ===\n"
        if myt_order_ref:
            data_block += f"  MYT Order: {myt_order_ref}\n"
        if myt_control_period:
            data_block += f"  Control Period: {myt_control_period}\n"

    if prev_myt_norms:
        data_block += f"\n=== PREVIOUS YEAR MYT ARR NORMS (FY {prev_fy}) — for comparison tables ===\n"
        for k in exp_keys:
            m = float(prev_myt_norms.get(k, 0.0) or 0.0)
            if m > 0:
                name = k.replace("_", " ").title()
                data_block += f"  {name}: {m:.2f}\n"
        # Also include previous year revenue norms
        for k in rev_keys:
            m = float(prev_myt_norms.get(k, 0.0) or 0.0)
            if m > 0:
                name = k.replace("_", " ").title()
                data_block += f"  {name}: {m:.2f}\n"
        prev_target_loss = float(prev_myt_norms.get("target_distribution_loss_pct", 0.0) or 0.0)
        if prev_target_loss > 0:
            data_block += f"  Target Distribution Loss: {prev_target_loss:.2f}%\n"

    # ── Historical trued-up data for comparison tables ──────────────────────
    if historical_data:
        data_block += f"\n=== HISTORICAL TRUED UP DATA (for comparison tables) ===\n"
        data_block += f"Dynamic year columns: {fy_minus_2} | {prev_fy} | {fy}\n"
        data_block += f"IMPORTANT: Use these exact values for 'Trued Up' columns in multi-year tables.\n"
        data_block += f"If a year has no data, show '---' in that cell.\n\n"
        for hist_fy, hist_data in sorted(historical_data.items()):
            data_block += f"--- FY {hist_fy} TRUED UP VALUES ---\n"
            # Approved expenses
            hist_exp = hist_data.get("approved_expenses", {})
            if hist_exp:
                data_block += f"  Approved Expenses:\n"
                for k in exp_keys:
                    v = float(hist_exp.get(k, 0.0) or 0.0)
                    if v > 0:
                        data_block += f"    {k.replace('_', ' ').title()}: {v:.2f}\n"
                total_hist_exp = sum(float(hist_exp.get(k, 0.0) or 0.0) for k in exp_keys)
                data_block += f"    TOTAL: {total_hist_exp:.2f}\n"
            # Approved revenues
            hist_rev = hist_data.get("approved_revenues", {})
            if hist_rev:
                data_block += f"  Approved Revenues:\n"
                for k in rev_keys:
                    v = float(hist_rev.get(k, 0.0) or 0.0)
                    if v > 0:
                        data_block += f"    {k.replace('_', ' ').title()}: {v:.2f}\n"
            # Claimed expenses
            hist_claimed = hist_data.get("claimed_expenses", {})
            if hist_claimed:
                data_block += f"  Claimed Expenses (Truing Up petition):\n"
                for k in exp_keys:
                    v = float(hist_claimed.get(k, 0.0) or 0.0)
                    if v > 0:
                        data_block += f"    {k.replace('_', ' ').title()}: {v:.2f}\n"
            # A&G line items (approved)
            ag_items = hist_data.get("ag_line_items", {})
            if ag_items:
                data_block += f"  A&G Line Items (Trued Up):\n"
                for k, v in ag_items.items():
                    v = float(v or 0.0)
                    if v > 0:
                        data_block += f"    {k.replace('_', ' ').title()}: {v:.2f}\n"
            # A&G claimed line items
            ag_claimed = hist_data.get("ag_claimed_line_items", {})
            if ag_claimed:
                data_block += f"  A&G Line Items (Truing Up petition):\n"
                for k, v in ag_claimed.items():
                    v = float(v or 0.0)
                    if v > 0:
                        data_block += f"    {k.replace('_', ' ').title()}: {v:.2f}\n"
            # R&M line items (approved)
            rm_items = hist_data.get("rm_line_items", {})
            if rm_items:
                data_block += f"  R&M Line Items (Trued Up):\n"
                for k, v in rm_items.items():
                    v = float(v or 0.0)
                    if v > 0:
                        data_block += f"    {k.replace('_', ' ').title()}: {v:.2f}\n"
            # R&M claimed line items
            rm_claimed = hist_data.get("rm_claimed_line_items", {})
            if rm_claimed:
                data_block += f"  R&M Line Items (Truing Up petition):\n"
                for k, v in rm_claimed.items():
                    v = float(v or 0.0)
                    if v > 0:
                        data_block += f"    {k.replace('_', ' ').title()}: {v:.2f}\n"
            # Revenue gap/surplus
            gap = hist_data.get("revenue_gap_surplus", 0.0)
            if gap != 0:
                data_block += f"  Revenue {'Surplus' if gap >= 0 else 'Gap'}: {abs(float(gap)):.2f}\n"
            data_block += "\n"
        data_block += "=== END HISTORICAL DATA ===\n"

    data_block += "\n=== END OF AUTHORITATIVE DATA ===\n"

    petition_path = state.get("petition_pdf_path", "")

    HTML_RULES = """
=== OUTPUT FORMAT: CLEAN HTML ONLY ===
ABSOLUTELY NO markdown. NEVER use pipe tables (|). Do NOT include html/head/body tags.

=== CRITICAL NUMBER DISCIPLINE — READ THIS FIRST ===
You have been given AUTHORITATIVE FINANCIAL DATA above (the data_block). Follow this strictly:

1. PDF 1 (reference order OP 82/2023) is for FORMAT/STRUCTURE ONLY.
   NEVER copy ANY NUMBER from PDF 1. It has FY 2022-23 values which must NOT appear here.

2. The AUTHORITATIVE FINANCIAL DATA above is the SINGLE SOURCE OF TRUTH for all numbers:
   'MYT ARR Approved'     → use for Table 1's 'ARR Approved' / 'Projected ARR' column.
   'For TrUp Claimed'     → use for Table 1's 'For Truing Up' / 'Claimed' column.
   'TrUp Approved'        → use for Table 1's 'Trued Up' / 'Approved' column.
   These are the ONLY values to use in ALL tables. Do not invent or round differently.

3. JUSTIFICATION PARAGRAPHS — for each cost head you MUST state:
   a) Exact claimed amount: "The licensee has claimed Rs.XX.XX lakh on account of [item]..."
   b) MYT norm ceiling: "...the MYT approved norm for this component is Rs.YY.YY lakh..."
   c) Variance: "The claimed amount exceeds/equals the norm by Rs.ZZ.ZZ lakh..." (use data_block variance)
   d) Special allowances (if any in SPECIAL ITEMS section): name each one and its Rs. amount explicitly
   e) Commission decision amount = EXACTLY the 'TrUp Approved' value from data_block, no rounding

4. DISALLOWANCES section in data_block contains pre-computed justification text. Use it verbatim.
   It includes exact regulation citations, calculations, and intermediate values (efficiency gain,
   opening normative loan, equity base, BEE fee, interim relief). Include all of them.

5. If 'Trued Up Approved' > 'MYT ARR Approved' for any item, this means the Commission approved
   MORE than its original norm — explain why (e.g., higher actual normative loan, efficiency gain).

=== HTML ELEMENT RULES ===
- Table caption (ABOVE table, centered): <p class="table-caption">Table N<br/><b>Title of Table</b></p>
- Unit note BELOW caption: <p class="table-subcaption">(Rs. in Lakhs unless specified)</p>
- Every financial table: <table class="data-table">
- Number cells (right-aligned, no wrapping): <td class="num">123.45</td>
- Total rows: <tr class="total-row"><td><b>Total</b></td><td class="num"><b>123.45</b></td></tr>
- Numbered paragraphs: <p><b>5.</b>&nbsp;&nbsp;Text of paragraph...</p>
- Section headings: <h3>Section Title</h3>
- Commission decision (bold+italic): <p class="commission-decision">The Commission hereby approves Rs.XX.XX lakh...</p>
- Regulation quote: <blockquote>Regulation XX: exact text of regulation</blockquote>
- Sub-items: <p style="margin-left:32px;"><b>a)</b> Text...</p>

STYLE: No background-color on any table cell. Bold centered header row. 1px solid black borders.

=== CRITICAL TABLE RULE ===
For each cost head (Employee Cost, R&M, A&G, Depreciation, Interest, etc.), you MUST generate TWO separate tables:

  TABLE A — LICENSEE PETITION TABLE (what the licensee claimed):
    Shows ALL line items extracted from the Petition PDF.
    Columns: Sl.No | Particulars | Approved in ARR Order | Claimed in Truing Up Petition
    This table reproduces the licensee's own petition breakdown.

  TABLE B — COMMISSION TRUED-UP TABLE (what the Commission approved):
    Shows the same items but with the Commission's approved values.
    Columns: Sl.No | Particulars | Approved in ARR Order | Claimed in Truing Up Petition | Trued Up by Commission
    The 'Trued Up by Commission' column uses values from the AUTHORITATIVE DATA above.
    ALWAYS include a Total row that matches the data_block totals exactly.

Place Table A BEFORE the Commission's analysis paragraphs (to show what was claimed).
Place Table B AFTER the Commission's decision paragraph (to show what was approved).

=== GLOBAL ADAPTIVE RULE ===
This order must FULLY ADAPT to whatever the specific licensee's petition contains.
Different licensees (KDHP, Technopark, Infopark, etc.) have different:
- Consumer categories (HT/LT types vary by licensee)
- Asset groups and GFA composition
- Employee categories and staff structure
- R&M and A&G line items
- Revenue sources and non-tariff income items
YOU MUST extract the EXACT categories, line items, and structures from the Petition PDF.
Do NOT hardcode any category names — always derive from the actual petition data.
If the petition claims items not covered in the prompt template → CREATE sections for them.
If the petition does NOT claim certain items → SKIP those sections entirely.
Table numbering must always be sequential with no gaps.

=== CRITICAL: ANTI-HALLUCINATION RULES ===
NEVER fabricate or invent sub-component values. Follow these rules strictly:

1. SUB-COMPONENT BREAKDOWNS (e.g., employee cost by category, A&G by line item, 
   non-tariff income by source, consumer-category-wise revenue) MUST be extracted 
   from the Petition PDF (PDF 2) or Annexure PDFs (PDF 3+).
   Read the actual tables in these documents and reproduce the EXACT values shown there.

2. If the Petition PDF does NOT contain a specific breakdown table, do NOT invent one.
   Instead, show only the total claimed amount from the AUTHORITATIVE DATA above.

3. NEVER use the same repeated value (like 10.00) for all sub-items in a table.
   Each value must come from the actual petition data.

4. For previous year columns (e.g., "2023-24 Trued Up"), if this data is not available,
   write "---" (not available) rather than making up numbers.

5. The ONLY numbers you can trust are:
   - 'TrUp Approved' column from the AUTHORITATIVE DATA (Commission-approved totals)
   - 'For TrUp Claimed' column from the AUTHORITATIVE DATA (total claimed amounts)
   - Sub-component details read DIRECTLY from the Petition PDF tables
   
6. If you cannot read a value from the Petition PDF, use the total from AUTHORITATIVE DATA
   and note "As claimed by the licensee" without breaking it into sub-items.
"""


    config = types.GenerateContentConfig(
        temperature=0.15,
        response_mime_type="text/plain",
        max_output_tokens=65536,
    )

    # Pre-load PDF bytes once (inline bytes for Vertex AI — no Files API needed)
    ref_pdf_bytes = None
    if Path(REFERENCE_ORDER_PDF).exists():
        logger.info("Loading reference PDF into memory...")
        ref_pdf_bytes = Path(REFERENCE_ORDER_PDF).read_bytes()
        logger.info(f"  Reference PDF: {len(ref_pdf_bytes):,} bytes")
    else:
        logger.warning(f"Reference PDF not found: {REFERENCE_ORDER_PDF} — generating without format template")

    pet_pdf_bytes = None
    annexure_pdf_bytes_list = []  # Additional PDFs (annexures with detailed tables)
    
    # Try to load all uploaded PDFs (petition + annexures)
    upload_pdf_paths = state.get("upload_pdf_paths", [])
    if upload_pdf_paths and len(upload_pdf_paths) > 0:
        for i, pdf_path in enumerate(upload_pdf_paths):
            p = Path(pdf_path)
            if p.exists():
                pdf_data = p.read_bytes()
                if i == 0:
                    pet_pdf_bytes = pdf_data
                    logger.info(f"  Petition PDF: {len(pdf_data):,} bytes — {p.name}")
                else:
                    annexure_pdf_bytes_list.append(pdf_data)
                    logger.info(f"  Annexure PDF {i}: {len(pdf_data):,} bytes — {p.name}")
        if annexure_pdf_bytes_list:
            logger.info(f"  Total: 1 petition + {len(annexure_pdf_bytes_list)} annexure PDFs loaded")
    
    # Fallback: try single petition path
    if not pet_pdf_bytes and petition_path and Path(petition_path).exists():
        logger.info("Loading petition PDF into memory...")
        pet_pdf_bytes = Path(petition_path).read_bytes()
        logger.info(f"  Petition PDF: {len(pet_pdf_bytes):,} bytes")
    
    if not pet_pdf_bytes:
        # Fallback: try to find petition PDF in uploads folder
        upload_dir = Path("uploads")
        if upload_dir.exists():
            analysis_id = state.get("analysis_id", "")
            if analysis_id:
                matches = sorted(upload_dir.glob(f"{analysis_id}*"))
                if matches:
                    pet_pdf_bytes = matches[0].read_bytes()
                    logger.info(f"  Found petition PDF via fallback: {matches[0].name} ({len(pet_pdf_bytes):,} bytes)")
                    # Load remaining as annexures
                    for m in matches[1:]:
                        annexure_pdf_bytes_list.append(m.read_bytes())
                        logger.info(f"  Found annexure PDF via fallback: {m.name}")
        
        if not pet_pdf_bytes:
            logger.warning("⚠️ PETITION PDF NOT FOUND — Gemini will NOT have access to actual petition data!")
            logger.warning(f"  petition_path was: '{petition_path}'")

    def _build_pdf_parts():
        """Build inline byte parts for reference PDF + all petition/annexure PDFs."""
        parts = []
        if ref_pdf_bytes:
            parts.append(types.Part.from_bytes(data=ref_pdf_bytes, mime_type="application/pdf"))
        if pet_pdf_bytes:
            parts.append(types.Part.from_bytes(data=pet_pdf_bytes, mime_type="application/pdf"))
        # Include all annexure PDFs — these contain detailed tables
        for ann_bytes in annexure_pdf_bytes_list:
            parts.append(types.Part.from_bytes(data=ann_bytes, mime_type="application/pdf"))
        return parts

    def _call_with_retry(parts_list, label="API call", max_retries=3) -> str:
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
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
        return ""  # unreachable (raise above), but satisfies type checker

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
        ref_text_summary = str("\n".join(pages_text[:5]))[:3000]
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
- PDF 3+ = Annexures/additional documents (if provided). These contain DETAILED TABLES
  like category-wise revenue breakdown, consumer category details, employee cost split,
  A&G sub-items, depreciation schedules, etc. ALWAYS check these for detailed data.
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
<p class="center bold">Petition No: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</p>
<table class="header-table">
  <tr><td class="label">Present</td><td class="colon">:</td><td class="value"><b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;, Chairman</b><br/><b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;, Member</b><br/><b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;, Member</b></td></tr>
  <tr class="spacer-row"><td colspan="3"></td></tr>
  <tr><td class="label">In the matter of</td><td class="colon">:</td><td class="value">Petition for approval of truing up of accounts for the financial year {fy}</td></tr>
  <tr class="spacer-row"><td colspan="3"></td></tr>
  <tr><td class="label">Petitioner</td><td class="colon">:</td><td class="value">M/s {licensee} Kerala</td></tr>
  <tr><td class="label">Represented by</td><td class="colon">:</td><td class="value">[Names from petition]</td></tr>
  <tr class="spacer-row"><td colspan="3"></td></tr>
  <tr><td class="label">Respondent</td><td class="colon">:</td><td class="value">M/s Kerala State Electricity Board Limited</td></tr>
  <tr><td class="label">Represented by</td><td class="colon">:</td><td class="value">[Names from petition]</td></tr>
  <tr class="spacer-row"><td colspan="3"></td></tr>
  <tr><td class="label">Hearing</td><td class="colon">:</td><td class="value">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td></tr>
</table>
<p class="center bold">Order Dated &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</p>

PARAGRAPH NUMBERING RULES:
- For SECTION 1 (Introduction) and SECTION 3 (Energy Sales) onwards: use REAL sequential paragraph numbers starting from 1. Example: "1.&nbsp;&nbsp;M/s {licensee} is a distribution licensee..."
- For SECTION 2 (Hearing on the Petition): Do NOT number the paragraphs. Leave blank space before each paragraph where numbers would go. The user will add paragraph numbers later.
- Tables should be numbered sequentially: Table 1, Table 2, Table 3, etc.
- Sub-points within a paragraph use letters (a), (b), (c), etc.

THEN write ALL of these sections in full:

SECTION 1 - INTRODUCTION (MINIMUM 6 paragraphs, with sequential paragraph numbers starting from 1):
Para 1: M/s {licensee} background — full license area description, consumer categories, network extent, date of license grant and license number.
Para 2: Filing history — when this petition was filed citing date, what previous Commission orders govern FY {fy} tariff, the MYT order reference.
Para 3: Legal basis — cite KSERC Tariff Regulations 2021 Regulation 3, 67, 68 on truing up process and what the Commission is required to do.
Para 4: TABLE 1 — Comparison of ARR&ERC for FY {fy}.
Caption: "Table 1\\nComparison of ARR&ERC {fy}  (Rs. Lakh)"
Columns: Particulars | ARR&ERC Projected | ARR&ERC Approved | Truing Up petition
Rows (ALL of these in this exact order):
  Power purchase cost
  Employee Expenses
  Administration & General Expenses
  Repair & Maintenance Expenses
  Depreciation
  Interest on Working Capital and finance charges
  Other debits
  Return on Net Fixed Assets
  Total Expenditure/ARR (total-row, bold)
  Revenue from Sale of Power
  Other income
  Total Income/ERC (total-row, bold)
  Revenue (Gap)/Surplus (total-row, bold)
The 'ARR&ERC Projected' column = MYT ARR values from data_block.
The 'ARR&ERC Approved' column = the Commission's ARR-approved values (use MYT values if same).
The 'Truing Up petition' column = the licensee's claimed values from data_block.
Do NOT include 'Trued Up by Commission' in this table — that comes later in the final ARR summary table.

Para 5: TABLE 2 — Comparison of Income and Expenditure for the previous years.
Caption: "Table 2\\nComparison of Income and Expenditure for the previous years  (Rs. lakh)"
This is a multi-year comparison table. Show columns for: {prev_fy} and {fy}.
For {prev_fy}, show TWO sub-columns: "Truing Up" | "Trued Up" — use the HISTORICAL TRUED UP DATA block for exact values.
For the current FY {fy}, show only "Truing Up" column (since it's not yet trued up).
If historical data for a year is not in the data_block, show '---' in the Trued Up column.
Rows: same as Table 1 (Power purchase cost, Employee Expenses, etc. through Revenue (Gap)/Surplus).
Para 6: Brief overview of the Commission's approach to examining each cost head.

SECTION 2 - HEARING ON THE PETITION:
CRITICAL INSTRUCTIONS FOR THIS SECTION:
- This section must contain ONLY the text provided by the user in the COURT HEARING data block.
- Do NOT add any dates, paragraph numbers, auto-generated content, or commentary.
- ALWAYS write ALL of the following sub-headings, even if no data is provided for them:
  1. Write the section heading "Hearing on the Petition"
  2. Sub-heading "Licensee Submissions": paste the licensee_submissions text EXACTLY as provided, using (a), (b), (c) for each point. If no data, leave blank space under the heading.
  3. Sub-heading "Respondent's (KSEB) Position": paste the respondent_position text EXACTLY as provided, using (a), (b), (c) for each point. If no data, leave blank space under the heading.
  4. Sub-heading "Commission's Observations": paste the commission_observations text EXACTLY as provided, using (a), (b), (c) for each point. If no data, leave blank space under the heading.
- ALL THREE sub-headings must ALWAYS appear in the output regardless of whether data is provided.
- Do NOT rephrase, summarize, or expand the user's text. Copy it VERBATIM.

SECTION 3 - ENERGY SALES AND CONSUMER MIX (MINIMUM 5 paragraphs, continue sequential numbering from Section 1):
Para: Explain consumer categories in {licensee}'s supply area — HT, LT, domestic, commercial, industrial, public lighting, etc.
Para: Comparison of FY {fy} actual sales vs. approved in MYT order — units, increase/decrease and reasons.
Para: Category-wise analysis — which categories grew, which declined and why.
Para: Per-unit revenue realization analysis.
Para: Commission's finding and approval of energy sales figures.
TABLE 3 — Energy Sales and No. of Consumers.
Caption: "Table 3\\nEnergy Sales and No. of Consumers for {prev_fy} and {fy}"
This table compares the PREVIOUS year (Trued Up) with the CURRENT year (Truing Up petition) side by side.
Column groups:
  Particulars | Trued Up {prev_fy} (No. of Consumers | Sales (lakh units)) | Truing Up {fy} (No. of Consumers | Sales (lakh units))
Rows — list ALL consumer categories from the petition PDF, such as:
  HT I A Industrial, HT I B Industrial, HT II General, HT III Agriculture, HT IV Commercial,
  LT I Domestic, LT IV Industries, LT V Agriculture, LT VI Non-Domestic, LT VII Commercial,
  Street Lighting, LT TOD Tariff, Total.
Extract the exact category names and numbers from the Petition PDF.

TARGET: Part A must produce approximately 12 PRINTED A4 PAGES of HTML content.
Do NOT write the signature block. Stop after Energy Sales section.
Do NOT compress — write every paragraph in full detail with 4-6 sentences minimum per para."""

    logger.info("=== PART A: Header + Intro + Hearing + Energy Sales ===")
    t0 = time.time()
    parts_a = _build_pdf_parts()
    parts_a.append(types.Part.from_text(text=prompt_a))
    part_a_html = _call_with_retry(parts_a, "Part A")
    logger.info(f"Part A: {len(part_a_html)} chars in {time.time()-t0:.1f}s")

    tail_a = str(part_a_html)[-2500:] if len(part_a_html) > 2500 else part_a_html

    # ==========================================================================
    # PART B: Distribution Loss + Power Purchase + O&M (Employee, R&M, A&G)
    # ==========================================================================
    prompt_b = f"""You are an expert legal drafter for KSERC.

TASK: Generate PART B of a Truing-Up Order for M/s {licensee} for FY {fy}.
Part A (Header/Intro/Hearing/Energy Sales) is already written. Continue from where it ends.

INPUTS:
- PDF 1 = Reference Order OP 82/2023 - FORMAT TEMPLATE
- PDF 2 = Petition by M/s {licensee} for FY {fy} - DATA SOURCE
- PDF 3+ = Annexures with detailed tables (consumer categories, revenue split, cost breakdowns)
- Audited Data:
{data_block}

{HTML_RULES}

CONTEXT - last 2500 chars of Part A:
---
{tail_a}
---

Use real sequential paragraph numbers continuing from where Part A ended. Tables should be numbered sequentially. Sub-points use (a), (b), (c), etc.


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
TABLE 4 - Comparison of Distribution loss and energy requirement.
Caption: "Table 4\nComparison of Distribution loss and energy requirement"
Multi-year comparison table. Show columns for: {prev_fy} and {fy}.
For {prev_fy}, show TWO sub-columns: "For Truing up" | "Trued Up" — use HISTORICAL DATA block for exact values.
For the current FY {fy}, show only "For Truing up" column.
Rows (ALL of these in exact order):
  Energy purchased (In lakh Units)
  KSEB Energy Feedback (In lakh Units)
  Gross energy in the system (In lakh Units)
  Energy Sales (In lakh Units) (bold)
  Distribution loss (In lakh Units)
  Distribution loss %
Extract ALL values from the Petition PDF.

TABLE 5 - Approved Energy input & Distribution Loss for the year {fy}.
Caption: "Table 5\nApproved Energy input & Distribution Loss for the year {fy}"
Columns: Particulars | Approved in ARR | As per Truing up petition | Trued up
Rows:
  Energy Sales (lakh units) (1)
  KSEB Ltd Energy Feedback (lakh units) (2)
  Total Energy Output (lakh Units) (1+2)
  Distribution Loss (%)
  Distribution Loss (lakh Units)
  Gross energy in to the system (lakh units) (bold)
  KSEB Ltd Energy Feedback (lakh units)
  Energy purchase from KSEB Ltd (lakh units) (bold)

SECTION 5 - POWER PURCHASE COST (MINIMUM 5 paragraphs):
Para 1: Sources of power for {licensee} — KSEB grid supply, any captive/renewable sources, voltage of supply, nature of open access if any.
Para 2: Total units purchased in FY {fy} and total cost. Compare actual per-unit purchase cost vs approved in the ARR order.
Para 3: Analysis of any deviation — whether increased purchase was due to consumer growth or load management issues. Mention if licensee included excess demand charges and Commission's view on it.
Para 4: Regulation citation for power purchase cost approval methodology. If actual distribution loss is higher than approved, the quantum of power purchased corresponding to the excess distribution loss shall be disallowed at the average cost of power purchase.
Para 5: Commission's decision — approved units and cost, any disallowance.

TABLE 6 - Details of the cost of power purchase claimed (LICENSEE PETITION TABLE).
Caption: "Table 6\nDetails of the cost of power purchase claimed for {fy}"
Columns: Particulars | {fy}
Rows:
  Total Consumption in lakh units
  Less: Feed Back to KSEB in lakh units
  Billed Units (bold)
  Demand Charges (Rs. lakh)
  Excess Demand Charges (Rs. lakh)
  Energy Cost (Rs. lakh)
  Total Power purchase cost (Rs. lakh) (bold)
  Average power purchase Cost (Rs. /kWh)
Extract ALL values from the Petition PDF.

TABLE 7 - Details of approved power purchase cost (COMMISSION TABLE).
Caption: "Table 7\nDetails of approved power purchase cost for {fy}"
This is a NUMBERED COMPUTATION table showing Commission's step-by-step calculation.
Columns: Sl.No | Particulars | Amount (Rs. lakh)
Rows:
  1. Actual distribution loss (In lakh units)
  2. Approved distribution loss (In lakh units)
  3. Excess distribution loss (lakh units) (1-2)
  4. Average Power Purchase Cost (Rs. per unit)
  5. Excess power purchase cost to be disallowed (Rs. lakh) (4) * (3)
  6. Actual power purchase cost (Rs. lakh)
  7. Approved power purchase cost (Rs. lakh) (6-5) (bold)

SECTION 6 - O&M EXPENSES (MINIMUM 25 paragraphs across sub-sections — THIS IS THE LARGEST SECTION):

6a. O&M OVERVIEW (3-4 paragraphs):
Para: O&M expenses are controllable expenses and include expenses of Employee cost, Repair & Maintenance Expenses and Administrative & General Expenses.
Para: Cite Regulation 80(2) of the Tariff Regulations, 2021 — the distribution licensees shall be allowed to recover O&M expenses as per the norms specified in Annexure 7 of the Regulations.
Para: State the approved O&M norm amount vs the claimed amount. Note if the claimed O&M is higher than the norm.

TABLE 8 - Comparison of O&M expenses multi-year.
Caption: "Table 8\nComparison of O&M expenses for {prev_fy} and {fy} (Rs. lakh)"
Column groups: 
  Particulars | {prev_fy} (Truing Up petition | Trued Up) | {fy} (Norms | Truing Up petition)
Rows: Employee Expenses, A&G Expenses, R&M Expenses, Total O&M Expenses.
For {prev_fy} 'Trued Up' column: use approved expenses from HISTORICAL DATA block.
Extract current FY values from petition PDF and data_block.

6b. EMPLOYEE COST (MINIMUM 8 paragraphs):
Para 1: State the claimed amount vs ARR approved amount. State the details of the claim made by the licensee.
Para 2: Total establishment — number of permanent employees by grade/category, contract staff.

TABLE 9 - Comparison of Employee Cost multi-year detail.
Caption: "Table 9\nComparison of Employee Cost for the year {prev_fy} and {fy} (Rs.lakh)"
Column groups:
  Particulars | {prev_fy} (Truing Up | Trued Up) | {fy} (ARR Approved | Truing Up)
Rows — extract ALL from petition PDF:
  Basic Salary, Dearness Allowance (DA), Leave Travel Allowance, Earned Leave Encashment, 
  Other Allowances, Medical Reimbursement, Overtime Payment, Bonus/Ex-Gratia Payments,
  Staff welfare expenses, Provident Fund Contribution, Salary of Manager & Executive,
  Share of Directors/Mgmt Staff Salaries, Gross Employee Expenses.
For the {prev_fy} 'Trued Up' column and {fy} 'ARR Approved' column: use approved values from HISTORICAL DATA block / data_block. Note "Approved based on actual escalation of X% to the base year" text in the column header if applicable.

Para 3: Staff count and category-wise split.

TABLE 10 - Category-wise split of the employee cost.
Caption: "Table 10\nCategory-wise split of the employee cost for {prev_fy} and {fy}"
Column groups:
  Particulars | Actual {prev_fy} (No | Rs.Lakh) | Actual {fy} (No | Rs.Lakh)
Rows — extract from petition PDF:
  Technical Officers, Switching Station Operations, Technical Staff, Other Workers,
  Non-Technical Staff, Share of Management Staff Expenses,
  Other Allowances Medical & Welfare expense, Total.

Para 4: Employee cost increase analysis — state the increase amount and percentage over previous year.
Para 5: Reasons for increase submitted by licensee — bullet list of items like wage revision arrears, yearly increments, overtime increase, etc.
Para 6: Commission's examination — cite Tariff Regulations 2021, Annexure-7 norms.

TABLE 11 - O&M Expenses as per the Tariff Regulations, 2021.
Caption: "Table 11\nO&M Expenses as per the Tariff Regulations, 2021 (Rs. lakh)"
Columns: Particulars | Base year {fy_minus_2} | {prev_fy} | {fy} | next 3 years of control period
Rows: Employee Cost, R&M Expenses, A&G Expenses, Total.
Header: first column = "Base year", remaining = "Control period"
Use the MYT norm values from data_block or petition PDF.

Para 7: Explain Annexure-7 paragraph 1 methodology — escalation rate adopted, base year, inflation factor. State the average escalation rate approved by Commission. State how the actual inflation rate differs from the projected escalation rate.
Para 8: Quote the relevant Note to Annexure-7 about actual inflation being used at truing up stage.

TABLE 12 - Revised O&M expenses approved considering Actual Inflation.
Caption: "Table 12\nRevised O&M expenses of {licensee} approved for the year {fy} considering Actual Inflation (Rs. lakh)"
Columns: Particulars | {prev_fy} Approved | Control Period {fy} (Actual Inflation | O&M Approved)
Rows: Employee Cost, R&M Expenses, A&G Expenses, Total.
Use the actual inflation rate from data_block.

Para 9: Commission's decision on Employee Cost — state the approved amount based on actual inflation rate, state the approved amount vs claimed.

6c. ADMINISTRATION & GENERAL EXPENSES (MINIMUM 5 paragraphs):
Para 1: State the claimed A&G vs the norm. Provide a comparison of A&G expenses over the years.

TABLE 13 - Comparison of A&G expenses multi-year.
Caption: "Table 13\nComparison of A&G expenses (Rs.lakh)"
Column groups:
  Particulars | {prev_fy} (Truing Up | Trued Up) | {fy} (Truing Up)
For {prev_fy} 'Truing Up' column: use 'A&G Line Items (Truing Up petition)' from HISTORICAL DATA.
For {prev_fy} 'Trued Up' column: use 'A&G Line Items (Trued Up)' from HISTORICAL DATA.
For {fy} 'Truing Up': extract from the current petition PDF.
Rows — extract ALL from petition PDF:
  Rent Rates & Taxes, Insurance, Telephone & Postage etc., Legal charges, Audit Fees,
  Travelling expenses, Conveyance and vehicle hire charges, Electricity charges,
  Printing & Stationery, Miscellaneous Expenses, License Fee and other related fee,
  Security arrangements, Gross A&G Expenses.
For 'Trued Up' columns, note "Approved based on actual escalation of X% to the base year" text if applicable.

Para 2-3: Line-by-line analysis of A&G items — insurance, audit fees, legal charges, BEE fee, etc.
Para 4: Commission's position on legal expenses — consistent stand that legal proceedings cannot be charged unless court order exists.
Para 5: Commission's decision on A&G — state approved amount, what was allowed/disallowed.

6d. REPAIR & MAINTENANCE EXPENSES (MINIMUM 5 paragraphs):
Para 1: State the ARR approved R&M vs the petition claim. Overview of R&M comparison over years.

TABLE 14 - Comparison of R&M expenses multi-year.
Caption: "Table 14\nComparison of R&M expenses (Rs. lakh)"
Column groups:
  Particulars | {prev_fy} (Truing Up | Trued Up) | {fy} (Truing Up)
For {prev_fy} columns: use 'R&M Line Items' from HISTORICAL DATA block.
For {fy} 'Truing Up': extract from the current petition PDF.
Rows — extract ALL from petition PDF:
  Plant & Machinery, Buildings, Lines & Cable Networks, Vehicles,
  LT Lines/Upkeeps etc., Gross R&M Expenses.
For 'Trued Up' columns, note "Actual of {{year}} Approved based on actual escalation" text if applicable.

Para 2: Major R&M items — lines & cable networks, upkeeps, cutting charges, transformer maintenance, etc.
Para 3: Licensee's statement on type of expenses — routine maintenance, no one-time capital expenses.
Para 4: Commission's finding — whether R&M items are routine or one-time.
Para 5: Commission's decision — approved R&M based on actual inflation rate.

6e. SUMMARY OF O&M EXPENSES APPROVED:
Para: Summary of all approved O&M.

TABLE 15 - O&M expenses approved for {fy}.
Caption: "Table 15\nO&M expenses approved for {fy} (Rs. lakh)"
Columns: Particulars | ARR&ERC | Truing Up | Trued Up
Rows: Employee Expenses, Administration & General Expenses, Repair & Maintenance Expenses, Total O&M Expenses.
Use exact values from data_block for the 'Trued Up' column.

TARGET: Part B must produce approximately 15 PRINTED A4 PAGES of HTML content.
Do NOT include signature block. Stop after O&M expenses summary.
Write EVERY paragraph in full with 4-6 sentences per paragraph — do NOT compress."""

    logger.info("=== PART B: Distribution Loss + Power Purchase + O&M ===")
    t0 = time.time()
    parts_b = _build_pdf_parts()
    parts_b.append(types.Part.from_text(text=prompt_b))
    part_b_html = _call_with_retry(parts_b, "Part B")
    logger.info(f"Part B: {len(part_b_html)} chars in {time.time()-t0:.1f}s")

    tail_b = str(part_b_html)[-2500:] if len(part_b_html) > 2500 else part_b_html

    # ==========================================================================
    # PART C: Depreciation + Interest + Revenue + ARR Summary + Orders + Signature
    # ==========================================================================
    prompt_c = f"""You are an expert legal drafter for KSERC.

TASK: Generate PART C (FINAL PART) of a Truing-Up Order for M/s {licensee} for FY {fy}.
Parts A and B are already written. This is the final continuation. End with the signature block.

INPUTS:
- PDF 1 = Reference Order OP 82/2023 - FORMAT TEMPLATE
- PDF 2 = Petition by M/s {licensee} for FY {fy} - DATA SOURCE
- PDF 3+ = Annexures with detailed tables (consumer categories, revenue split, cost breakdowns)
- Audited Data:
{data_block}

{HTML_RULES}

CONTEXT - last 2500 chars of Part B:
---
{tail_b}
---

Use real sequential paragraph numbers continuing from where the previous Part ended. Tables should be numbered sequentially. Sub-points use (a), (b), (c), etc.


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


SECTION 7 - DEPRECIATION (MINIMUM 5 paragraphs):
Para 1: State the claimed depreciation amount. Cite straight-line method as per Tariff Regulations, 2021.
Para 2: Quote Regulation 27 "Depreciation" in full as a blockquote — all sub-clauses (1) through (vi).
Para 3: For assets over 13 years, explain the depreciation has been allowed at lower rates. Explain the asset groups.

TABLE 16 - Depreciation claimed for the year {fy} (LICENSEE PETITION TABLE).
Caption: "Table 16\nDepreciation claimed for the year {fy} (Rs. lakh)"
Columns: Asset Group | GFA as at 01.04.XX | Asset Addition | Rate of depreciation | Depreciation
TWO sections:
  "Asset over 13 years": Transformers, Distribution lines, Meters, IT Equipment, Others, Sub-total
  "Asset below 13 years": Transformers, Distribution lines, Meters, IT Equipment, Others, Sub-total
Then: Grand Total, As per audited accounts, Excess depreciation.
Extract ALL values from the Petition PDF.

Para 4: Asset addition details — mention if new additions are approved and to be met from accumulated regulatory surplus. State that assets funded by consumer contribution shall not be eligible for depreciation.

TABLE 17 - Depreciation approved for the year {fy} (COMMISSION TABLE).
Caption: "Table 17\nDepreciation approved for the year {fy} (Rs. lakh)"
Columns: Asset Group | Rate of depreciation | GFA | Depreciation
TWO sections same as Table 16:
  "Asset over 13 years": items with Sub-total
  "Asset below 13 years": items with Sub-total
Then: Total, Asset Addition {fy}, (Less) Consumer contribution (with rate), Net Assets and depreciation, Grand Total.
Use approved values from data_block.

Para 5: Commission's decision — state the approved depreciation amount after deducting consumer contribution depreciation.

SECTION 8 - INTEREST AND FINANCE CHARGES (MINIMUM 10 paragraphs):
Para 1: Overview — state ARR approved interest & finance charges vs claimed amount. List all components claimed.

TABLE 18 - Interest & Finance charges for {fy} (PETITION OVERVIEW).
Caption: "Table 18\nInterest & Finance charges for {fy} (Rs. lakh)"
Columns: Particulars | Truing Up
Rows:
  Interest on Security Deposits from Customers
  Bank Charges - On the Bank Guarantee to KSEB Ltd as per direction of Hon. Supreme Court of India
  Other Bank Charges including on the Letter of Credit to secure cost of mostly power purchase from KSEB Ltd
  As per petition (subtotal, bold)
  Interest on Normative Loan
  Interest on Working capital
  Total Regulatory Adjustments (subtotal)
  Total (bold)
Extract all values from Petition PDF.

Para 2: Heading "a) Interest on normative loan"
Para 3: State the licensee's claimed interest on normative loan and details.

TABLE 19 - Interest on Normative Loan Claimed {fy} (PETITION).
Caption: "Table 19\nInterest on Normative Loan Claimed {fy} (Rs. lakh)"
Columns: Particulars | Truing Up Petition
Rows:
  Net Normative loan – Opening (01.04.YYYY)
  Increase/Decrease due to ACE/de-capitalization during the year
  Less - Repayment of Normative Loan during the year
  Net Normative loan – Closing (31.03.YYYY)
  Average Normative Loan during the year
  Average Base Rate of SBI during the year (%)
  Interest on the normative loan for the year
Extract from Petition PDF.

Para 4: Commission's examination of normative loan — cite Regulation 29(2), explain opening normative loan, repayment, closing balance. State SBI EBLR rate used.

TABLE 20 - Normative loan approved for {fy} (COMMISSION).
Caption: "Table 20\nNormative loan approved for {fy}"
Columns: No | Particulars | (Rs. lakh)
Rows:
  1) Normative loan at the beginning of the year
  2) Less: Allowable Depreciation/ Repayment for the year
  3) Closing Normative loan for the year
  4) Average Loan for the year (1+3)/2
  5) Rate of Interest (%)  *EBLR of SBI as on 01-04-YYYY
  6) Interest on Normative loan for the year

Para 5: Commission's decision on normative loan interest.
Para 6: Heading "b) Interest on Working Capital"
Para 7: State the licensee's claimed working capital interest.

TABLE 21 - Working capital proposed by the licensee for {fy} (PETITION).
Caption: "Table 21\nWorking capital proposed by the licensee for {fy} (Rs. lakh)"
Columns: Particulars | Approved ARR/ERC | Truing up Petition
Rows:
  O & M Expenses- One month
  Receivables- 2 months
  Less: security Deposit from consumers
  Total working Capital
  Interest rate (%)  *SBI 1-year EBLR + 2%
  Interest on working capital

Para 8: Quote Regulation 32 on working capital computation in blockquote — sub-clauses (v)(I-III) and proviso about security deposits. State the Commission's calculation.

TABLE 22 - Interest on Working capital approved for {fy} (COMMISSION).
Caption: "Table 22\nInterest on Working capital approved for {fy} (Rs. lakh)"
Columns: Particulars | (Rs. lakh)
Rows:
  Approved O & M Expenses for One month (approved_om/12)
  Receivables-2 months Revenue from sale of power (revenue × 2 / 12)
  Less: Security Deposit from Consumers
  Total Working Capital
  Interest Rate (%)  *SBI 1-year EBLR + 2%
  Interest on Working Capital

Para 9: Heading "c) Interest on the security deposit". Explain the licensee's claim, rate increase, Commission's examination. State the approved amount.

Para 10: Heading "d) Bank Charges on Bank Guarantee/L.C to KSEB Ltd". State the claimed bank charges.

TABLE 23 - Bank Charges Claimed for the year {fy}.
Caption: "Table 23\nBank Charges Claimed or the year {fy}"
Columns: Particulars | Rs. lakh
Rows:
  Bank Charges on LC to secure cost of monthly power purchase from KSEB Ltd
  Bank Guarantee to KSEB Ltd
  Total
Extract from Petition PDF.

Para 11: Commission's analysis of bank charges — approve LC charges, disallow bank guarantee charges citing Supreme Court/APTEL directions.
Para 12: Heading "Summary of the interest and finance charges"

TABLE 24 - Interest & Finance charges approved for the year {fy} (SUMMARY).
Caption: "Table 24\nInterest & Finance charges approved for the year {fy} (Rs.lakh)"
Columns: Particulars | ARR Approved | Truing Up Petition | Trued Up
Rows:
  Interest on Normative Loan
  Interest on Working Capital
  Interest on Security deposits
  Bank Charges on LC to secure cost of monthly power purchases from KSEB Ltd
  Bank Charges on Bank Guarantee to KSEB
  Total

SECTION 9 - OTHER DEBITS (MINIMUM 3 paragraphs):
Para 1: State claimed other debits amount and components.

TABLE 25 - Details of other debits multi-year.
Caption: "Table 25\nDetails of other debits (Rs. lakh)"
Column groups:
  Particulars | {prev_fy} (Truing Up Petition | Trued Up) | {fy} (Truing Up Petition)
For {prev_fy} 'Trued Up' column: use HISTORICAL DATA block. If not available, show '---'.
Rows: Section 3 Duty, Inspection Charges, Provision for doubtful Debt, Total.

Para 2: Commission's analysis — Section 3(1) Duty consistently disallowed as revenue expenditure, provision for doubtful debts disallowed as not declared bad debt.
Para 3: Commission's decision — approve only inspection charges, disallow Section 3 duty and provision for doubtful debts.

SECTION 10 - RETURN ON NET FIXED ASSETS (MINIMUM 4 paragraphs):
Para 1: State the licensee's claimed RoNFA. Cite Regulation 28 on RoNFA at 5.50%.

TABLE 26 - Computation of RONFA claimed for {fy} (PETITION).
Caption: "Table 26\nComputation of RONFA claimed for {fy} (Rs.lakh)"
Columns: Particulars | Approved ARR-ERC | Truing up Claim
Rows:
  Gross fixed assets as at 1st April YYYY
  Less: Accumulated depreciation
  Less: Consumer contribution
  Less: GFA for which interest is allowed
  Balance value of Net fixed assets at the beginning of the year
  Rate of Return
  Eligible Return

Para 2: Commission's examination — explain how NFA is correctly computed for RoNFA, interest on normative loan basis.

TABLE 27 - Computation of RoNFA for the year {fy} (COMMISSION).
Caption: "Table 27\nComputation of RoNFA for the year {fy}"
Columns: Particulars | Rs. Lakh
Rows:
  Gross fixed assets as at 1st April YYYY
  Less: Accumulated depreciation (XX.XX lakh + Rs.XX.XX lakh)
  Less: Consumer contribution
  Less: NFA for which interest is allowed
  Balance value of Net fixed assets at the beginning of the year
  Rate of Return (5.50%)
  Eligible Return

Para 3-4: Commission's decision on RoNFA.

SECTION 11 - REVENUE FROM SALE OF POWER, NON-TARIFF INCOME, AND ARR SUMMARY will be in the NEXT part.
END Part C here after Interest/Finance Charges and Return on NFA sections.
Do NOT include signature block or "Order of the Commission" text in Part C. That goes in Part D only.

TARGET: Part C must produce approximately 10 PRINTED A4 PAGES of HTML content.
Write all numbers from the Petition PDF — not from reference order.
Write every paragraph in full with minimum 4-6 sentences per paragraph — do NOT compress."""

    logger.info("=== PART C: Depreciation + Interest + Return on NFA ===")
    t0 = time.time()
    parts_c = _build_pdf_parts()
    parts_c.append(types.Part.from_text(text=prompt_c))
    part_c_html = _call_with_retry(parts_c, "Part C")
    logger.info(f"Part C: {len(part_c_html)} chars in {time.time()-t0:.1f}s")

    # ==========================================================================
    # PART D: Revenue + Non-Tariff Income + ARR Summary + Orders + Signature
    # ==========================================================================
    tail_c = str(part_c_html)[-2500:] if len(part_c_html) > 2500 else part_c_html

    prompt_d = f"""You are an expert legal drafter for KSERC.

TASK: Generate PART D (FINAL PART) of a Truing-Up Order for M/s {licensee} for FY {fy}.
Parts A, B and C are already written. This is the final continuation covering Revenue, Non-Tariff Income, ARR Summary, Orders, and Signature.

INPUTS:
- PDF 1 = Reference Order OP 82/2023 - FORMAT TEMPLATE
- PDF 2 = Petition by M/s {licensee} for FY {fy} - DATA SOURCE
- PDF 3+ = Annexures with detailed tables (consumer categories, revenue split, cost breakdowns)
- Audited Data:
{data_block}

{HTML_RULES}

CONTEXT - last 2500 chars of Part C:
---
{{tail_c}}
---

Use real sequential paragraph numbers continuing from where the previous Part ended. Tables should be numbered sequentially. Sub-points use (a), (b), (c), etc.

SECTION 11 - REVENUE FROM SALE OF POWER (MINIMUM 3 paragraphs):
Para 1: State the total revenue from sale of power and total units sold. Note increase/decrease compared to previous year.

TABLE 28 - Revenue from sale of power multi-year.
Caption: "Table 28\\nRevenue from sale of power for {prev_fy} and {fy}"
Column groups per FY:
  {prev_fy}: No. of Consumers | Sales in lakh units | Total Revenue | Average Realization
  {fy}: No. of Consumers | Sales in lakh units | Total Revenue | Average Realization
Rows — ALL consumer categories from petition PDF:
  HT I A Industrial, HT I B (IT Industrial), HT II General, HT III Agriculture,
  HT IV Commercial, LT I Domestic, LT IV Industries, LT V Agriculture,
  LT VI Non-Domestic, LT VII Commercial, LT VIII Public Lighting, LT TOD Tariff, Total.

Para 2: Analysis of sales — majority category, growth areas, reasons for increase.
Para 3: Commission's decision — approve the revenue from sale of power.

SECTION 12 - NON-TARIFF INCOME (MINIMUM 3 paragraphs):
Para 1: State the claimed non-tariff income amount. Comparison with previous year.

TABLE 29 - Details of Non-Tariff income claimed multi-year.
Caption: "Table 29\\nDetails of Non-Tariff income claimed"
Column groups:
  Particulars | {prev_fy} (Truing Up Petition | Trued Up) | {fy} (Truing Up Petition)
Rows — extract from Petition PDF:
  Interest on Deposit with KSEB
  Provision for Interest on Deposit with KSEB
  Miscellaneous recoveries
  Interest on accumulated Surplus
  Other Operational Income
  Less: Writeback of excess provision for doubt full debts
  Less: Reversal of provision for interest on security deposit from KSEB Ltd being already claimed in regulatory accounts
  Total

Para 2: Commission's analysis of each non-tariff income item.
Para 3: Commission's approved non-tariff income.

TABLE 30 - Non-Tariff Income approved for {fy} (COMMISSION).
Caption: "Table 30\\nNon-Tariff Income approved for {fy} (Rs lakh)"
Columns: Particulars | {fy} (Truing Up Petition | Trued Up)
Rows — same as Table 29. Use data_block values for Trued Up column.

GLOBAL ADAPTIVE INSTRUCTION:
This order must ADAPT to whatever the petition PDF contains. Different licensees may have different consumer categories, revenue sources, and claims.
ALL values in petition tables must come from the Petition PDF. ALL values in commission tables must come from data_block.
Table numbering must be sequential from Part C.

TARGET: Part D must produce approximately 5 PRINTED A4 PAGES of HTML content.
Write all numbers from the Petition PDF — not from reference order.

CRITICAL STOP INSTRUCTION:
- Do NOT write "Orders of the Commission" section. That will be in Part E.
- Do NOT write any signature block. That will be in Part E.
- Do NOT write the ARR Summary table. That will be in Part E.
- STOP IMMEDIATELY after the Non-Tariff Income approval paragraph and table.
- The LAST thing in Part D must be the Non-Tariff Income approved table and its approval paragraph."""

    # Replace the tail_c placeholder in the prompt
    prompt_d = prompt_d.replace("{tail_c}", tail_c)

    logger.info("=== PART D: Revenue + Non-Tariff Income ===")
    t0 = time.time()
    parts_d = _build_pdf_parts()
    parts_d.append(types.Part.from_text(text=prompt_d))
    part_d_html = _call_with_retry(parts_d, "Part D")
    logger.info(f"Part D: {len(part_d_html)} chars in {time.time()-t0:.1f}s")

    tail_d = str(part_d_html)[-2500:] if len(part_d_html) > 2500 else part_d_html

    # ==========================================================================
    # PART E: ARR Summary + Orders + Signature
    # ==========================================================================
    prompt_e = f"""You are an expert legal drafter for KSERC.

TASK: Generate PART E (FINAL PART) of a Truing-Up Order for M/s {licensee} for FY {fy}.
Parts A-D (Header/Intro/Hearing/Energy Sales/Distribution Loss/Power Purchase/O&M/Depreciation/Interest/Revenue/Non-Tariff) are already written. Continue from where Part D ends.

INPUTS:
- PDF 1 = Reference Order OP 82/2023 - FORMAT TEMPLATE
- PDF 2 = Petition by M/s {licensee} for FY {fy} - DATA SOURCE
- PDF 3+ = Annexures with detailed tables
- Audited Data:
{data_block}

{HTML_RULES}

CONTEXT - last 2500 chars of Part D:
---
{{tail_d}}
---

Use real sequential paragraph numbers continuing from where the previous Part ended. Tables should be numbered sequentially. Sub-points use (a), (b), (c), etc.

SECTION - WHEELING CHARGES (INCLUDE ONLY IF THE PETITION CLAIMS WHEELING CHARGES):
Para 1: Details of open access consumers and wheeling arrangements.
Para 2: Total wheeling income and Commission's approval.

SECTION - CARRYING COST ON PAST REVENUE GAPS (INCLUDE ONLY IF APPLICABLE):
Para 1: State the cumulative revenue gap approved through previous years.
Para 2: Carrying cost calculation — gap x SBI MCLR rate x appropriate months.
Para 3: Commission's decision — amount approved for FY {fy}.

SECTION - REVENUE SURPLUS/GAP FOR {fy} (FINAL ARR SUMMARY):
Para 1: Based on the above, state the approved expenditure and revenue for the year {fy} after truing up.

TABLE - Trued up Income and Expenditure for the Year {fy} (MOST IMPORTANT TABLE).
Caption: "Table\\nTrued up Income and Expenditure for the Year {fy} (Rs. lakh)"
Columns: Particulars | ARR&ERC Approved | Truing Up (Claimed) | Trued Up (Approved)
Rows:
  Power purchase cost
  Employee Expenses
  Administration & General Expenses
  Repair & Maintenance Expenses
  Depreciation
  Interest and Finance charges
  Other debits
  Other Expenses
  Return on Net Fixed Assets
  Total Expenditure/ARR (total-row, bold)
  Revenue from Sale of Power
  Non-Tariff Income
  Total Income/ERC (total-row, bold)
  Revenue (Gap)/Surplus (total-row, bold)
CRITICAL TABLE DATA INSTRUCTIONS:
- ARR&ERC Approved column = use the 'arr_erc_approved' values from data_block (these are the MYT/ARR order amounts).
- Truing Up (Claimed) column = use the 'claimed_expenses' values from data_block. These are the amounts the licensee claimed in the petition. Do NOT leave as 0.00.
- Trued Up (Approved) column = use the 'approved_expenses' values from data_block. These are what the Commission approved.
- ALL THREE columns must have non-zero values for each row.
- Revenue (Gap)/Surplus: show as POSITIVE number ALWAYS. The row label '(Gap)' indicates deficit.

SECTION - ORDERS OF THE COMMISSION:
Para: "The Commission after considering the petition filed by M/s. {licensee} for Truing up of accounts for the year {fy}, and details provided by the licensee, the Commission approves the following."
Then list specific orders as lettered items:
  a) Total revenue is Rs.XXXX.XX lakh.
  b) Total expenditure is Rs.XXXX.XX lakh.
  c) The revenue surplus/gap for the year is Rs.XXX.XX lakh.
  d) The cumulative revenue surplus/gap till {fy} will be Rs.XXXX.XX lakh. 
     The licensee shall keep the surplus arrived at after the truing up process in a separate fund and utilize it 
     as per orders of the Commission.
Final para: "The petition is disposed of. Ordered accordingly."

SECTION - SIGNATURE BLOCK:
<table class="sig-table">
  <tr><td>Sd/-</td><td>Sd/-</td><td>Sd/-</td></tr>
  <tr><td><b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</b></td><td><b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</b></td><td><b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</b></td></tr>
  <tr><td><b>Chairman</b></td><td><b>Member</b></td><td><b>Member</b></td></tr>
</table>
<div class="secretary-block">
  <p><b>Approved for issue</b></p>
  <p>Sd/-</p>
  <p><b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</b></p>
  <p><b>Secretary</b></p>
</div>

GLOBAL ADAPTIVE INSTRUCTION:
This order must ADAPT to whatever the petition PDF contains.
ALL values in petition tables must come from the Petition PDF. ALL commission values must come from data_block.
Table numbering must be sequential from Part D.

TARGET: Part E must produce approximately 4 PRINTED A4 PAGES of HTML content.
This is the FINAL part — include the complete signature block at the very end."""

    prompt_e = prompt_e.replace("{tail_d}", tail_d)

    logger.info("=== PART E: ARR Summary + Orders + Signature ===")
    t0 = time.time()
    parts_e = _build_pdf_parts()
    parts_e.append(types.Part.from_text(text=prompt_e))
    part_e_html = _call_with_retry(parts_e, "Part E")
    logger.info(f"Part E: {len(part_e_html)} chars in {time.time()-t0:.1f}s")

    # Clean intermediate parts: strip </body></html>, <html><head>..., and signature blocks
    def _strip_intermediate(html_part):
        """Remove closing tags, duplicate headers, and signature blocks from intermediate parts."""
        h = html_part or ""
        # Remove </body></html> closings
        h = re.sub(r'</body>\s*</html>\s*$', '', h, flags=re.IGNORECASE)
        # Remove signature blocks (Sd/-, Chairman, Secretary)
        h = re.sub(r'<table\s+class="sig-table">[\s\S]*?</table>', '', h, flags=re.IGNORECASE)
        h = re.sub(r'<div\s+class="secretary-block">[\s\S]*?</div>', '', h, flags=re.IGNORECASE)
        return h.rstrip()

    def _strip_header(html_part):
        """Remove <html><head>...</head><body> from non-first parts."""
        h = html_part or ""
        h = re.sub(r'^.*?<body[^>]*>', '', h, count=1, flags=re.IGNORECASE | re.DOTALL)
        return h

    # Part A keeps its header, intermediate parts strip headers + closings
    clean_a = _strip_intermediate(part_a_html or "")
    clean_b = _strip_intermediate(_strip_header(part_b_html or ""))
    clean_c = _strip_intermediate(_strip_header(part_c_html or ""))
    clean_d = _strip_intermediate(_strip_header(part_d_html or ""))
    clean_e = _strip_header(part_e_html or "")  # Part E keeps its closing + signature

    combined_html = clean_a + "\n\n" + clean_b + "\n\n" + clean_c + "\n\n" + clean_d + "\n\n" + clean_e
    logger.info(f"Combined: {len(combined_html)} chars ({len(part_a_html)} + {len(part_b_html)} + {len(part_c_html)} + {len(part_d_html)} + {len(part_e_html)})")
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
            html = html[int(first_tag.start()):]

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

    Generates the final KSERC-format Truing-Up Order PDF using Gemini 2.5 Flash
    to produce rich HTML with detailed petition tables, then renders to PDF
    via Playwright headless Chromium.
    """
    licensee = state["licensee_name"]
    fy = state["financial_year"]

    logger.info(f"Drafting order for {licensee} FY {fy} using Gemini drafter")

    # 1. Generate comprehensive HTML via Gemini (reads petition PDF for detail tables)
    raw_html = _generate_document_with_gemini(state)
    body_html = _postprocess_html(raw_html)

    # 2. Wrap in full HTML document with KSERC CSS
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

    logger.info("Generated HTML via Gemini. Length: %d chars", len(full_html))

    # Save rendered HTML for reference/debugging
    output_dir = Path(__file__).resolve().parents[2] / "output_orders"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = licensee.replace(" ", "_").replace("/", "-")

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
    html_uri = f"file:///{html_path.resolve().as_posix()}"
    try:
        if HAS_WEASYPRINT:
            # WeasyPrint — works in Docker/Cloud Run without a browser
            logger.info("Using WeasyPrint for PDF generation")
            html_doc = WeasyHTML(filename=str(html_path))
            html_doc.write_pdf(str(final_pdf_path))
        elif HAS_PLAYWRIGHT:
            # Playwright fallback — needs Chromium installed
            logger.info("Using Playwright for PDF generation")
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
        else:
            raise ImportError("Neither weasyprint nor playwright is installed")
        logger.info(f"Successfully generated PDF at: {final_pdf_path}")
        state["output_pdf_path"] = str(final_pdf_path)
        state["output_html_path"] = str(html_path)
    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        raise  # Propagate so pipeline marks FAILED — no silent swallow

    return state
