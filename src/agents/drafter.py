"""
KSERC SDL Truing Up — PDF Order Generator (Drafter Agent)
===========================================================

Uses ReportLab to programmatically generate the final PDF artifact
replicating KSERC's official Truing-Up Order format.

Output includes:
  - Official KSERC header
  - Petition information ("In the Matter Of")
  - Side-by-side comparison table (Claimed vs Approved)
  - Detailed justification sections for disallowances
  - "Orders of the Commission" summary
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)

logger = logging.getLogger(__name__)

# ── Page dimensions ────────────────────────────────────────────────────
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 2 * cm


# ═══════════════════════════════════════════════════════════════════════
# Styles
# ═══════════════════════════════════════════════════════════════════════

def _build_styles() -> dict:
    """Create all paragraph styles for the KSERC order PDF."""
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "KSERCTitle",
            parent=base["Title"],
            fontSize=14,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=18,
        ),
        "subtitle": ParagraphStyle(
            "KSERCSubtitle",
            parent=base["Normal"],
            fontSize=11,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            spaceAfter=12,
            leading=14,
        ),
        "heading": ParagraphStyle(
            "KSERCHeading",
            parent=base["Heading2"],
            fontSize=12,
            fontName="Helvetica-Bold",
            alignment=TA_LEFT,
            spaceBefore=18,
            spaceAfter=8,
            leading=15,
        ),
        "subheading": ParagraphStyle(
            "KSERCSubHeading",
            parent=base["Heading3"],
            fontSize=11,
            fontName="Helvetica-Bold",
            alignment=TA_LEFT,
            spaceBefore=12,
            spaceAfter=6,
            leading=14,
        ),
        "body": ParagraphStyle(
            "KSERCBody",
            parent=base["Normal"],
            fontSize=10,
            fontName="Helvetica",
            alignment=TA_JUSTIFY,
            spaceBefore=4,
            spaceAfter=4,
            leading=13,
        ),
        "body_bold": ParagraphStyle(
            "KSERCBodyBold",
            parent=base["Normal"],
            fontSize=10,
            fontName="Helvetica-Bold",
            alignment=TA_LEFT,
            spaceBefore=4,
            spaceAfter=4,
            leading=13,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            leading=11,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica",
            alignment=TA_LEFT,
            leading=11,
        ),
        "table_cell_right": ParagraphStyle(
            "TableCellRight",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica",
            alignment=TA_RIGHT,
            leading=11,
        ),
        "order_item": ParagraphStyle(
            "OrderItem",
            parent=base["Normal"],
            fontSize=10,
            fontName="Helvetica",
            alignment=TA_LEFT,
            leftIndent=20,
            spaceBefore=4,
            spaceAfter=4,
            leading=13,
            bulletIndent=10,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontSize=8,
            fontName="Helvetica-Oblique",
            alignment=TA_CENTER,
            textColor=colors.grey,
        ),
    }
    return styles


# ═══════════════════════════════════════════════════════════════════════
# PDF Building Blocks
# ═══════════════════════════════════════════════════════════════════════

def _build_header(
    styles: dict,
    licensee_name: str,
    financial_year: str,
    petition_number: str = "",
) -> list:
    """Build the official KSERC header block."""
    elements = []

    # Optional placeholder for Emblem
    elements.append(Paragraph(
        "<b>[ KSERC EMBLEM ]</b>",
        ParagraphStyle("EmblemPlaceholder", parent=styles["subtitle"], fontSize=9, textColor=colors.grey)
    ))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph(
        "KERALA STATE ELECTRICITY REGULATORY COMMISSION",
        styles["title"],
    ))
    elements.append(Paragraph(
        "THIRUVANANTHAPURAM",
        styles["subtitle"],
    ))
    
    # Members Present
    elements.append(Paragraph(
        "<b>Present:</b><br/>"
        "Shri. T.K. Jose, Chairman<br/>"
        "Adv. A.J. Wilson, Member<br/>"
        "Shri. B. Pradeep, Member",
        ParagraphStyle("MembersPresent", parent=styles["body"], alignment=TA_CENTER, leading=14)
    ))

    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(
        width="100%", thickness=2, color=colors.black,
        spaceAfter=10, spaceBefore=4,
    ))

    # Petition and date info
    if not petition_number:
        petition_number = f"OP No. __/{ datetime.now().year}"

    elements.append(Paragraph(
        f"<b>Petition No.:</b> {petition_number}",
        styles["body"],
    ))
    elements.append(Paragraph(
        f"<b>Date of Order:</b> {datetime.now().strftime('%d-%m-%Y')}",
        styles["body"],
    ))
    elements.append(Spacer(1, 12))

    # "In the Matter Of" section
    elements.append(Paragraph(
        "<b>In the Matter Of:</b>",
        styles["body_bold"],
    ))
    elements.append(Paragraph(
        f"Petition filed by M/s <b>{licensee_name}</b> for the "
        f"Truing Up of Accounts for the Financial Year "
        f"<b>{financial_year}</b>.",
        styles["body"],
    ))
    elements.append(Spacer(1, 16))

    return elements


def _build_comparison_table(
    styles: dict,
    claimed_expenses: Dict[str, float],
    approved_expenses: Dict[str, float],
    claimed_revenues: Dict[str, float],
) -> list:
    """Build the side-by-side comparison table."""
    elements = []

    elements.append(Paragraph(
        "Summary of Claimed vs Approved Expenditure and Revenue",
        styles["heading"],
    ))

    # Display-friendly names
    display_names = {
        "power_purchase_cost": "Power Purchase Cost",
        "employee_cost": "Employee Cost",
        "repair_maintenance": "Repairs & Maintenance",
        "admin_general": "Administration & General",
        "depreciation": "Depreciation",
        "interest_finance": "Interest & Finance Charges",
        "return_on_nfa": "Return on Net Fixed Assets",
        "section3_1_duty": "Section 3(1) Electricity Duty",
        "other_expenses": "Other Expenses",
        "energy_charges": "Revenue from Energy Charges",
        "non_tariff_income": "Non-Tariff Income",
        "other_revenue": "Other Revenue",
    }

    # Table header
    header = [
        Paragraph("Sl.<br/>No.", styles["table_header"]),
        Paragraph("Particulars", styles["table_header"]),
        Paragraph("Claimed<br/>(Rs. Lakhs)", styles["table_header"]),
        Paragraph("Approved<br/>(Rs. Lakhs)", styles["table_header"]),
        Paragraph("Variance<br/>(Rs. Lakhs)", styles["table_header"]),
    ]

    data = [header]
    sl_no = 1

    # ── Expenditure rows ────────────────────────────────────────────
    data.append([
        "", Paragraph("<b>EXPENDITURE</b>", styles["table_cell"]),
        "", "", "",
    ])

    total_claimed_exp = 0.0
    total_approved_exp = 0.0

    for key in [
        "power_purchase_cost", "employee_cost", "repair_maintenance",
        "admin_general", "depreciation", "interest_finance",
        "return_on_nfa", "section3_1_duty", "other_expenses",
    ]:
        claimed = claimed_expenses.get(key, 0.0)
        approved = approved_expenses.get(key, 0.0)
        variance = round(approved - claimed, 2)

        total_claimed_exp += claimed
        total_approved_exp += approved

        data.append([
            Paragraph(str(sl_no), styles["table_cell"]),
            Paragraph(display_names.get(key, key), styles["table_cell"]),
            Paragraph(f"{claimed:,.2f}", styles["table_cell_right"]),
            Paragraph(f"{approved:,.2f}", styles["table_cell_right"]),
            Paragraph(f"{variance:,.2f}", styles["table_cell_right"]),
        ])
        sl_no += 1

    # Total expenditure row
    data.append([
        "", Paragraph("<b>TOTAL EXPENDITURE</b>", styles["table_cell"]),
        Paragraph(f"<b>{total_claimed_exp:,.2f}</b>", styles["table_cell_right"]),
        Paragraph(f"<b>{total_approved_exp:,.2f}</b>", styles["table_cell_right"]),
        Paragraph(
            f"<b>{total_approved_exp - total_claimed_exp:,.2f}</b>",
            styles["table_cell_right"],
        ),
    ])

    # ── Revenue rows ────────────────────────────────────────────────
    data.append([
        "", Paragraph("<b>REVENUE</b>", styles["table_cell"]),
        "", "", "",
    ])

    total_claimed_rev = 0.0
    for key in ["energy_charges", "non_tariff_income", "other_revenue"]:
        claimed = claimed_revenues.get(key, 0.0)
        total_claimed_rev += claimed
        data.append([
            Paragraph(str(sl_no), styles["table_cell"]),
            Paragraph(display_names.get(key, key), styles["table_cell"]),
            Paragraph(f"{claimed:,.2f}", styles["table_cell_right"]),
            Paragraph(f"{claimed:,.2f}", styles["table_cell_right"]),  # Revenue approved as claimed
            Paragraph("0.00", styles["table_cell_right"]),
        ])
        sl_no += 1

    data.append([
        "", Paragraph("<b>TOTAL REVENUE</b>", styles["table_cell"]),
        Paragraph(f"<b>{total_claimed_rev:,.2f}</b>", styles["table_cell_right"]),
        Paragraph(f"<b>{total_claimed_rev:,.2f}</b>", styles["table_cell_right"]),
        Paragraph("<b>0.00</b>", styles["table_cell_right"]),
    ])

    # ── Build table ─────────────────────────────────────────────────
    col_widths = [
        0.8 * cm, 6.5 * cm, 3.0 * cm, 3.0 * cm, 3.0 * cm,
    ]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        # Header styling
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        # Section header rows (Expenditure, Revenue)
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ECF0F1")),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),

        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),

        # Alternating row colors
        ("ROWBACKGROUNDS", (0, 2), (-1, -1), [
            colors.white, colors.HexColor("#F8F9FA"),
        ]),

        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    return elements


def _generate_approval_justification(
    key: str,
    display_name: str,
    claimed: float,
    approved: float,
    financial_year: str,
) -> str:
    """Generate detailed justification for approved/unchanged items."""
    if claimed == 0.0:
        return f"No amount claimed under {display_name} for FY {financial_year}."

    if abs(approved - claimed) < 0.01:
        justifications = {
            "power_purchase_cost": (
                f"The Power Purchase Cost of Rs. {claimed:,.2f} Lakhs as "
                f"claimed by the licensee for FY {financial_year} has been "
                f"verified against the energy purchase agreements and the "
                f"actual quantum of energy purchased. The Commission finds "
                f"the claim to be in order and approves the same."
            ),
            "employee_cost": (
                f"The Employee Cost of Rs. {claimed:,.2f} Lakhs claimed for "
                f"FY {financial_year} is within the normative limits prescribed "
                f"under the KSERC Tariff Regulations, 2021, after applying the "
                f"70:30 CPI/WPI escalation formula as per Annexure-7. "
                f"The claim is hereby approved."
            ),
            "repair_maintenance": (
                f"The Repairs & Maintenance expenditure of Rs. {claimed:,.2f} "
                f"Lakhs for FY {financial_year} is found to be within the "
                f"normative O&M allocation. The actual expenditure does not "
                f"exceed the escalated baseline. Approved as claimed."
            ),
            "admin_general": (
                f"The Administration & General Expenses of Rs. {claimed:,.2f} "
                f"Lakhs are within permissible limits after verification of "
                f"actual expenditure against the escalated norms for "
                f"FY {financial_year}. Approved as claimed."
            ),
            "depreciation": (
                f"Depreciation of Rs. {claimed:,.2f} Lakhs has been verified "
                f"against the asset register. The rates applied are in "
                f"accordance with the CERC norms adopted by the Commission. "
                f"No assets funded by grants or surplus were identified. "
                f"Approved as claimed."
            ),
            "interest_finance": (
                f"Interest & Finance Charges of Rs. {claimed:,.2f} Lakhs have "
                f"been verified against the loan schedules and applicable "
                f"interest rates. The Commission finds the charges to be "
                f"legitimate and approves the same for FY {financial_year}."
            ),
            "return_on_nfa": (
                f"Return on Net Fixed Assets of Rs. {claimed:,.2f} Lakhs has "
                f"been computed at 5.5% on the eligible NFA base after "
                f"excluding assets funded by consumer contributions, Government "
                f"grants, and normative loans. The claim is approved."
            ),
            "other_expenses": (
                f"Other Expenses of Rs. {claimed:,.2f} Lakhs claimed for "
                f"FY {financial_year} have been examined and found to be "
                f"reasonable. Approved as claimed."
            ),
        }
        return justifications.get(key, f"{display_name} of Rs. {claimed:,.2f} Lakhs approved as claimed for FY {financial_year}.")

    # If there's a variance but no disallowance entry
    diff = approved - claimed
    if diff < 0:
        return (
            f"The {display_name} has been reduced from Rs. {claimed:,.2f} Lakhs "
            f"to Rs. {approved:,.2f} Lakhs (reduction of Rs. {abs(diff):,.2f} Lakhs). "
            f"The adjustment is based on the Commission's scrutiny of the actual "
            f"expenditure vis-à-vis the normative limits for FY {financial_year}."
        )
    else:
        return (
            f"The {display_name} has been adjusted from Rs. {claimed:,.2f} Lakhs "
            f"to Rs. {approved:,.2f} Lakhs for FY {financial_year} based on "
            f"the Commission's determination of eligible expenditure."
        )

def _build_justification_sections(
    styles: dict,
    state: dict,
) -> list:
    """Build detailed justification paragraphs for all items."""
    elements = []
    elements.append(Paragraph("Detailed Analysis and Justification", styles["heading"]))
    
    financial_year = state.get("financial_year", "2022-23")
    claimed_expenses = state.get("claimed_expenses", {})
    approved_expenses = state.get("approved_expenses", {})
    disallowance_log = state.get("disallowance_log", [])

    display_names = {
        "power_purchase_cost": "Power Purchase Cost",
        "employee_cost": "Employee Cost",
        "repair_maintenance": "Repairs & Maintenance",
        "admin_general": "Administration & General Expenses",
        "depreciation": "Depreciation",
        "interest_finance": "Interest & Finance Charges",
        "return_on_nfa": "Return on Net Fixed Assets",
        "section3_1_duty": "Section 3(1) Electricity Duty",
        "other_expenses": "Other Expenses",
    }
    
    # 1. First, list everything from claimed_expenses
    i = 1
    for key, display_name in display_names.items():
        claimed = claimed_expenses.get(key, 0.0)
        approved = approved_expenses.get(key, 0.0)
        variance = approved - claimed
        
        # Check if there is a specific disallowance entry
        justification = ""
        for d in disallowance_log:
            d_item = d.get("item", "").lower()
            if (key.replace("_", " ") in d_item or
                display_name.lower() in d_item or
                any(word in d_item for word in key.split("_") if len(word) > 3)):
                justification = d.get("justification", "")
                break
                
        if not justification:
            justification = _generate_approval_justification(
                key, display_name, claimed, approved, financial_year
            )

        elements.append(Paragraph(f"{i}. {display_name}", styles["subheading"]))
        elements.append(Paragraph(
            f"<b>Amount Claimed:</b> Rs. {claimed:,.2f} Lakhs &nbsp;&nbsp;|&nbsp;&nbsp;"
            f"<b>Amount Approved:</b> Rs. {approved:,.2f} Lakhs &nbsp;&nbsp;|&nbsp;&nbsp;"
            f"<b>Variance:</b> Rs. {variance:,.2f} Lakhs",
            styles["body_bold"],
        ))
        elements.append(Paragraph(justification, styles["body"]))
        elements.append(Spacer(1, 8))
        i += 1
        
    # 2. Add any other specific disallowance logs that weren't captured above
    for entry in disallowance_log:
        item = entry.get("item", "Unknown Item")
        # Check if we already covered it
        if any(word.lower() in item.lower() for word in display_names.values()) and "Penalty" not in item and "Limit" not in item and "asset" not in item.lower():
            continue
            
        claimed = entry.get("claimed", 0.0)
        approved = entry.get("approved", 0.0)
        amount_cut = entry.get("amount_cut", 0.0)
        justification = entry.get("justification", "")
        
        elements.append(Paragraph(f"{i}. {item}", styles["subheading"]))
        
        if claimed > 0 or approved > 0 or amount_cut > 0:
            elements.append(Paragraph(
                f"<b>Amount Claimed:</b> Rs. {claimed:,.2f} Lakhs &nbsp;&nbsp;|&nbsp;&nbsp;"
                f"<b>Amount Approved:</b> Rs. {approved:,.2f} Lakhs &nbsp;&nbsp;|&nbsp;&nbsp;"
                f"<b>Disallowed:</b> Rs. {amount_cut:,.2f} Lakhs",
                styles["body_bold"],
            ))
            
        elements.append(Paragraph(justification, styles["body"]))
        elements.append(Spacer(1, 8))
        i += 1

    return elements

def _build_orders_section(
    styles: dict,
    licensee_name: str,
    financial_year: str,
    total_claimed_exp: float,
    total_approved_exp: float,
    total_revenue: float,
    final_gap_surplus: float,
    imputed_interest: float,
) -> list:
    """Build the concluding 'Orders of the Commission' section."""
    elements = []

    elements.append(HRFlowable(
        width="100%", thickness=1.5, color=colors.black,
        spaceAfter=10, spaceBefore=16,
    ))

    elements.append(Paragraph(
        "Orders of the Commission",
        styles["heading"],
    ))

    elements.append(Paragraph(
        f"Having examined the petition filed by M/s <b>{licensee_name}</b> "
        f"for the Truing Up of Accounts for the Financial Year "
        f"<b>{financial_year}</b>, and having considered the submissions "
        f"made therein, the Commission hereby orders as follows:",
        styles["body"],
    ))
    elements.append(Spacer(1, 8))

    position = "surplus" if final_gap_surplus >= 0 else "gap"
    abs_amount = abs(final_gap_surplus)

    order_items = [
        f"The Total Revenue Requirement as claimed by the licensee is "
        f"Rs. <b>{total_claimed_exp:,.2f} Lakhs</b>.",

        f"The Total Approved Expenditure after detailed scrutiny is "
        f"Rs. <b>{total_approved_exp:,.2f} Lakhs</b>.",

        f"The Total Revenue (including imputed interest of "
        f"Rs. {imputed_interest:,.2f} Lakhs on accumulated surplus) "
        f"is Rs. <b>{total_revenue:,.2f} Lakhs</b>.",

        f"The Revenue {position.title()} for the Financial Year "
        f"{financial_year} is hereby determined as "
        f"Rs. <b>{abs_amount:,.2f} Lakhs</b> ({position}).",
    ]

    if position == "surplus":
        order_items.append(
            f"The surplus of Rs. {abs_amount:,.2f} Lakhs shall be "
            f"retained in the regulatory surplus account of {licensee_name} "
            f"and adjusted against future revenue gaps, subject to "
            f"imputation of notional interest as per KSERC practice."
        )
    else:
        order_items.append(
            f"The revenue gap of Rs. {abs_amount:,.2f} Lakhs shall be "
            f"addressed through tariff adjustments in the next tariff "
            f"determination cycle, or as otherwise directed by the "
            f"Commission."
        )

    for item_text in order_items:
        elements.append(Paragraph(
            f"• {item_text}",
            styles["order_item"],
        ))

    elements.append(Spacer(1, 40))

    # Signature block
    sig_data = [
        [
            Paragraph("Sd/-<br/><b>Adv. A.J. Wilson</b><br/>Member", styles["table_cell"]),
            Paragraph("Sd/-<br/><b>B. Pradeep</b><br/>Member", styles["table_cell_right"]),
        ],
        [
            "",
            Paragraph("Sd/-<br/><b>T.K. Jose</b><br/>Chairman", ParagraphStyle("ChairmanSig", parent=styles["table_cell"], alignment=TA_CENTER)),
            "",
        ]
    ]

    sig_table = Table(
        [[sig_data[0][0], "", sig_data[0][1]], [ "", sig_data[1][1], ""]],
        colWidths=[6*cm, 4*cm, 6*cm]
    )
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 1), (-1, 1), 20), # Space before chairman
    ]))

    elements.append(sig_table)

    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        "Approved for issue",
        ParagraphStyle("Approved", parent=styles["body_bold"], alignment=TA_CENTER)
    ))
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Sd/-", ParagraphStyle("SecSd", parent=styles["body"], alignment=TA_CENTER)))
    elements.append(Paragraph("<b>Secretary</b>", ParagraphStyle("SecTitle", parent=styles["body_bold"], alignment=TA_CENTER)))

    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(
        width="100%", thickness=1, color=colors.grey,
        spaceAfter=8, spaceBefore=12,
    ))

    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"Order dated {datetime.now().strftime('%d %B %Y')}",
        styles["footer"],
    ))

    return elements


# ═══════════════════════════════════════════════════════════════════════
# Main Drafting Function (LangGraph Node)
# ═══════════════════════════════════════════════════════════════════════

def draft_order(state: dict) -> dict:
    """
    LangGraph node function.

    Generates the final KSERC-format Truing-Up Order PDF from the
    audited state data.

    Parameters
    ----------
    state : dict
        Fully audited LangGraph state.

    Returns
    -------
    dict
        Updated state with 'output_pdf_path'.
    """
    licensee = state["licensee_name"]
    fy = state["financial_year"]

    logger.info(f"Drafting order for {licensee} FY {fy}")

    # ── Determine output path ──────────────────────────────────────
    output_dir = Path(__file__).resolve().parents[2] / "output_orders"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = licensee.replace(" ", "_")
    filename = f"KSERC_TrueUp_Order_{safe_name}_FY_{fy}.pdf"
    output_path = output_dir / filename

    # ── Build PDF ──────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=f"KSERC True-Up Order - {licensee} FY {fy}",
        author="KSERC SDL Truing Up System",
    )

    styles = _build_styles()
    elements = []

    # 1. Header
    elements.extend(_build_header(styles, licensee, fy))

    # 2. Comparison Table
    elements.extend(_build_comparison_table(
        styles,
        state.get("claimed_expenses", {}),
        state.get("approved_expenses", {}),
        state.get("claimed_revenues", {}),
    ))

    # 3. Justification Sections
    elements.extend(_build_justification_sections(
        styles,
        state,
    ))

    # 4. Orders of the Commission
    elements.extend(_build_orders_section(
        styles,
        licensee,
        fy,
        state.get("total_claimed_expenditure", 0.0),
        state.get("total_approved_expenditure", 0.0),
        state.get("total_approved_revenue", 0.0),
        state.get("final_revenue_gap_surplus", 0.0),
        state.get("imputed_interest_on_surplus", 0.0),
    ))

    # ── Generate PDF ────────────────────────────────────────────────
    doc.build(elements)
    logger.info(f"PDF generated: {output_path}")

    return {"output_pdf_path": str(output_path)}
