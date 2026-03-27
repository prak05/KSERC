"""
KSERC Depreciation Engine
=========================

Complete depreciation calculation module implementing all 10 steps
from the KSERC depreciation specification.

This module handles depreciation approval for ANY KSERC distribution
licensee truing-up petition. It searches all submitted PDFs for
depreciation data, identifies funding sources, applies two-level
exclusion logic, and produces structured output with cross-verification.

CORE PRINCIPLE:
  KSERC does NOT recalculate depreciation from scratch. It takes the
  audited depreciation total and makes deductions based on how assets
  were funded. If consumers/government/surplus already paid for an
  asset, consumers cannot be charged again through depreciation.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Constants & Rate Schedule
# ═══════════════════════════════════════════════════════════════════

RATES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "annexure1_rates.json"
)

MAX_DEPRECIATION_PCT = 90.0      # 90% cap — no asset beyond this
SALVAGE_PCT = 10.0               # 10% salvage always retained
OVER_13_YEAR_THRESHOLD = 13      # After 13 years, reduced rate kicks in
DEFAULT_RATE = 5.28              # Electrical distribution default
ROUNDING_TOLERANCE = 0.10        # Rs. 0.10 lakh tolerance for cross-checks


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class AssetGroup:
    """Represents one row in the fixed asset schedule."""
    category: str = ""
    gfa_opening: float = 0.0
    additions: float = 0.0
    deletions: float = 0.0
    gfa_closing: float = 0.0
    rate_pct: float = 0.0
    depreciation_amount: float = 0.0
    is_reduced_rate: bool = False   # True if over-13 asset split


@dataclass
class FundingSource:
    """Represents a funding source deduction."""
    source_type: str = ""           # cc, pre_cutoff_grant, post_cutoff_grant, subsidy, deposit_works
    description: str = ""
    value: float = 0.0
    asset_rate_pct: float = 0.0
    deduction_amount: float = 0.0
    method: str = ""                # "deduct_after" or "exclude_from_base"
    source_document: str = ""       # Where was this found
    verified: bool = False          # Verified by prior KSERC order?
    addition_year: str = ""         # For post-cutoff items
    grant_portion: float = 0.0
    surplus_portion: float = 0.0
    own_funds_portion: float = 0.0


@dataclass
class DepreciationExtraction:
    """All depreciation data extracted from petition PDFs."""
    gross_depreciation: float = 0.0
    audited_depreciation: float = 0.0
    claimed_depreciation: float = 0.0
    asset_groups: List[AssetGroup] = field(default_factory=list)
    funding_deductions: List[FundingSource] = field(default_factory=list)
    balance_sheet_cc: float = 0.0
    balance_sheet_grants: float = 0.0
    narrative_notes: List[str] = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)
    discrepancies: List[str] = field(default_factory=list)
    # Table-level fields (from structured table parser)
    gfa_opening: float = 0.0
    gfa_closing: float = 0.0
    accumulated_dep_opening: float = 0.0
    accumulated_dep_closing: float = 0.0
    table_reading_summary: List[Dict[str, Any]] = field(default_factory=list)
    bottom_section_rows: List[Dict[str, Any]] = field(default_factory=list)
    is_provisional: bool = False  # True if no prior order data exists
    pre_cutoff_depreciation: float = 0.0  # Dep on pre-cutoff assets ("Before 01-04-20" in Form D 3.5)


@dataclass
class BottomSectionRow:
    """A classified row from the bottom section of a depreciation table."""
    row_type: str = ""        # "A" (pre-cutoff deduction), "B" (post-cutoff exclusion),
                              # "C" (result row), "D" (unrecognised)
    raw_text: str = ""
    description: str = ""
    value: float = 0.0        # Monetary value (asset amount or deduction)
    rate_pct: float = 0.0     # Rate percentage (0 if not present)
    deduction: float = 0.0    # Computed deduction amount
    year_label: str = ""      # For Type B rows (e.g. "2020-21")
    grant_portion: float = 0.0
    surplus_portion: float = 0.0
    own_funds_portion: float = 0.0
    source_file: str = ""
    page_num: int = 0


@dataclass
class DepreciationResult:
    """Final output of the depreciation engine."""
    claimed: float = 0.0
    approved: float = 0.0
    workings: Dict[str, Any] = field(default_factory=dict)
    justification: str = ""
    flags: List[str] = field(default_factory=list)
    clarification_items: List[str] = field(default_factory=list)
    firestore_payload: Dict[str, Any] = field(default_factory=dict)
    disallowances: List[Dict[str, Any]] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# Step 4: Annexure 1 Rate Schedule
# ═══════════════════════════════════════════════════════════════════

class AnnexureRateSchedule:
    """KSERC Tariff Regulations 2021 Annexure 1 rate matcher."""

    def __init__(self, rates_path: str = RATES_PATH):
        self.rates: Dict[str, Dict] = {}
        self.default_rate = DEFAULT_RATE
        self._load(rates_path)

    def _load(self, path: str):
        try:
            with open(os.path.abspath(path), "r", encoding="utf-8") as f:
                data = json.load(f)
            self.rates = data.get("rates", {})
            self.default_rate = data.get("default_rate_pct", DEFAULT_RATE)
            logger.info(f"Loaded {len(self.rates)} asset rate categories")
        except Exception as e:
            logger.warning(f"Could not load rate schedule: {e}")

    def get_rate(self, asset_category: str) -> float:
        """Match an asset category description to its KSERC rate."""
        cat_lower = asset_category.lower().strip()

        # Land is ALWAYS zero — no exceptions
        if any(kw in cat_lower for kw in ["land", "land right", "freehold", "leasehold"]):
            return 0.0

        # Match against keywords
        best_match = None
        best_score = 0
        for rate_key, rate_data in self.rates.items():
            keywords = rate_data.get("keywords", [])
            score = sum(1 for kw in keywords if kw.lower() in cat_lower)
            if score > best_score:
                best_score = score
                best_match = rate_key

        if best_match and best_score > 0:
            return self.rates[best_match]["rate_pct"]

        return self.default_rate

    def is_land(self, asset_category: str) -> bool:
        """Check if an asset category is land (never depreciable)."""
        cat_lower = asset_category.lower().strip()
        return any(kw in cat_lower for kw in ["land", "land right", "freehold", "leasehold"])


# ═══════════════════════════════════════════════════════════════════
# Step 1A: Structured Depreciation Table Parser
# ═══════════════════════════════════════════════════════════════════

class DepreciationTableParser:
    """
    Reads and interprets depreciation tables from petition PDFs.
    
    Every depreciation table has 4 sections:
      Section 1 — Header row (column names)
      Section 2 — Asset group rows (one per category)
      Section 3 — Subtotal row (gross depreciation before deductions)
      Section 4 — Bottom section (deduction rows, result row)
    
    The bottom section rows are classified as:
      Type A — Pre-cutoff deduction (value + rate + deduction amount)
      Type B — Post-cutoff exclusion (year label + value, no rate)
      Type C — Result row (final claimed/approved figure)
      Type D — Unrecognised row (flagged for human review)
    """

    def __init__(self, rate_schedule: AnnexureRateSchedule):
        self.rate_schedule = rate_schedule

    def parse_page(
        self, text: str, filename: str, page_num: int
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse a depreciation table from a page of text.
        Returns None if no depreciation table is found.
        """
        text_lower = text.lower()

        # Check if this page has a depreciation table
        if not self._is_depreciation_table_page(text_lower):
            return None

        lines = text.split("\n")
        lines_lower = [l.lower().strip() for l in lines]

        # Find the subtotal row (Section 3) — marks the boundary
        subtotal_idx, gross_dep = self._find_subtotal_row(lines, lines_lower)
        if subtotal_idx < 0:
            return None

        # Extract asset group rows (Section 2) — above the subtotal
        asset_groups = self._extract_asset_groups(lines, lines_lower, subtotal_idx)

        # Extract bottom section rows (Section 4) — below the subtotal
        bottom_rows = self._extract_bottom_section(
            lines, lines_lower, subtotal_idx, filename, page_num
        )

        # Extract GFA totals from the subtotal row
        gfa_opening, gfa_closing = self._extract_gfa_totals(
            lines, lines_lower, subtotal_idx
        )

        result = {
            "filename": filename,
            "page": page_num + 1,
            "gross_depreciation": gross_dep,
            "gfa_opening": gfa_opening,
            "gfa_closing": gfa_closing,
            "asset_groups": asset_groups,
            "bottom_section_rows": bottom_rows,
            "subtotal_line_index": subtotal_idx,
        }

        logger.info(
            f"Table parsed: {filename} p{page_num+1} — "
            f"gross={gross_dep:.2f}L, {len(asset_groups)} asset groups, "
            f"{len(bottom_rows)} bottom rows"
        )
        return result

    def _is_depreciation_table_page(self, text_lower: str) -> bool:
        """Check if a page contains a depreciation table (not just mentions)."""
        table_signals = [
            "gross fixed assets", "rate of depreciation",
            "depreciation for the year", "accumulated depreciation",
            "asset group", "asset category", "gfa",
        ]
        signal_count = sum(1 for s in table_signals if s in text_lower)
        # Need at least 2 signals to confirm it's a table page
        has_table = signal_count >= 2
        # Also check for "total" or "sub-total" indicating a structured table
        has_total = any(kw in text_lower for kw in ["total", "sub-total", "grand total"])
        return has_table and has_total

    def _find_subtotal_row(
        self, lines: List[str], lines_lower: List[str]
    ) -> Tuple[int, float]:
        """
        Find the subtotal/total row that marks the end of asset group rows.
        Returns (line_index, gross_depreciation_value).
        """
        for i, line in enumerate(lines_lower):
            line = line.strip()
            # Look for total rows — but not "Less:" rows which come after
            is_total_row = (
                (line.startswith("total") or "grand total" in line or
                 "sub-total" in line or "sub total" in line or
                 "total (1)" in line or "total (" in line) and
                "less" not in line and
                "net" not in line and
                "approved" not in line
            )
            if is_total_row:
                # Strip leading row number
                clean_line = re.sub(r"^\d+\s+", "", line)
                # Extract all decimal numbers from this row
                numbers = re.findall(r"(\d+\.\d+)", lines[i])
                if numbers:
                    # The depreciation value is usually the last or second-to-last number
                    # Try to find the most likely depreciation figure
                    candidates = [float(n) for n in numbers if 0.5 < float(n) < 5000]
                    if candidates:
                        # Use the one that appears after "depreciation" column
                        # Heuristic: in most tables it's near the end of the row
                        gross_dep = candidates[-1] if len(candidates) > 1 else candidates[0]
                        return i, gross_dep
        return -1, 0.0

    def _extract_asset_groups(
        self, lines: List[str], lines_lower: List[str], subtotal_idx: int
    ) -> List[Dict[str, Any]]:
        """Extract asset group rows from above the subtotal."""
        groups = []
        for i in range(max(0, subtotal_idx - 20), subtotal_idx):
            line = lines_lower[i].strip()
            if not line or len(line) < 5:
                continue

            # Skip header rows and blank rows
            if any(kw in line for kw in
                   ["asset category", "asset group", "particulars",
                    "rate of", "gfa as on", "opening", "closing",
                    "sl no", "sr no", "s.no"]):
                continue

            # Strip row number
            clean = re.sub(r"^\d+\s+", "", line)
            # Must have at least one decimal number to be a data row
            numbers = re.findall(r"(\d+\.\d+)", lines[i])
            if numbers and len(clean) > 3:
                # Check for land rows
                is_land = any(kw in clean for kw in ["land", "freehold", "leasehold"])
                rate = 0.0
                dep_amount = 0.0

                # Try to extract rate (a number between 1 and 20)
                for n in numbers:
                    val = float(n)
                    if 1.0 <= val <= 20.0:
                        rate = val
                        break

                # Depreciation amount is usually the last reasonable number
                for n in reversed(numbers):
                    val = float(n)
                    if 0.01 < val < 2000 and val != rate:
                        dep_amount = val
                        break

                groups.append({
                    "description": clean[:60],
                    "rate_pct": rate,
                    "depreciation": dep_amount,
                    "is_land": is_land,
                    "numbers": [float(n) for n in numbers],
                })

        return groups

    def _extract_bottom_section(
        self, lines: List[str], lines_lower: List[str],
        subtotal_idx: int, filename: str, page_num: int
    ) -> List[BottomSectionRow]:
        """
        Extract and classify all rows in the bottom section (after subtotal).
        """
        bottom_rows: List[BottomSectionRow] = []

        for i in range(subtotal_idx + 1, min(len(lines), subtotal_idx + 20)):
            line = lines[i].strip()
            line_lower = lines_lower[i].strip()
            if not line_lower or len(line_lower) < 3:
                continue

            # Strip leading row/serial number
            clean = re.sub(r"^\d+\s+", "", line_lower)
            clean_orig = re.sub(r"^\d+\s+", "", line)

            row = self._classify_bottom_row(
                clean, clean_orig, line, filename, page_num
            )
            if row:
                bottom_rows.append(row)

        return bottom_rows

    def _classify_bottom_row(
        self, clean: str, clean_orig: str, raw_line: str,
        filename: str, page_num: int
    ) -> Optional[BottomSectionRow]:
        """
        Classify a single bottom-section row as Type A, B, C, or D.
        """
        # Only match decimal numbers (avoid row serial numbers)
        numbers = re.findall(r"(\d+\.\d+)", clean_orig)
        num_values = [float(n) for n in numbers]

        # Has a year label like "2020-21" or "FY 2021-22"?
        year_match = re.search(r"(20\d{2}[-–]\d{2})", clean)
        year_label = year_match.group(1) if year_match else ""

        # Has a rate percentage (1-20 range)?
        has_rate = any(1.0 <= v <= 20.0 for v in num_values)

        # Has deduction keywords?
        has_less = "less" in clean
        has_deduct_kw = any(kw in clean for kw in
                          ["grant", "contribution", "consumer", "government",
                           "surplus", "subsidy", "deposit work"])

        # === TYPE C — Result Row ===
        is_result = any(kw in clean for kw in
                       ["approved depreciation", "depreciation for the year",
                        "net depreciation", "depreciation approved",
                        "total depreciation", "claimed depreciation"])
        if is_result and not has_less:
            result_val = num_values[0] if num_values else 0.0
            return BottomSectionRow(
                row_type="C", raw_text=raw_line,
                description="Result/Claimed depreciation",
                value=result_val, source_file=filename, page_num=page_num,
            )

        # === TYPE A — Pre-Cutoff Deduction Row ===
        # Must have: "less" or deduction keyword, a monetary value, possibly a rate
        if (has_less or has_deduct_kw) and num_values:
            # Determine source type
            if any(kw in clean for kw in ["consumer", "contribution", "cc"]):
                source_type = "cc"
                desc = "Consumer Contribution"
            elif any(kw in clean for kw in ["grant", "government", "govt"]):
                source_type = "pre_cutoff_grant"
                desc = "Government Grant"
            elif any(kw in clean for kw in ["deposit", "deposit work"]):
                source_type = "deposit_works"
                desc = "Deposit Works"
            elif any(kw in clean for kw in ["surplus", "accumulated surplus"]):
                source_type = "surplus"
                desc = "Accumulated Surplus"
            else:
                source_type = "other_deduction"
                desc = "Other Deduction"

            # Extract the asset value (largest number that's not a rate)
            value = 0.0
            rate = 0.0
            deduction = 0.0
            for v in num_values:
                if 1.0 <= v <= 20.0 and rate == 0:
                    rate = v
                elif v > value and v > 20.0:
                    value = v
                elif v < value and 0.01 < v < value:
                    deduction = v

            # If we only have small numbers (<20), the first is likely the value
            if value == 0 and num_values:
                non_rate = [v for v in num_values if not (1.0 <= v <= 20.0)]
                if non_rate:
                    value = non_rate[0]
                elif num_values:
                    value = num_values[0]

            # Check if all numbers are dashes (value = 0)
            all_dashes = all(c in "-– .,\t" for c in
                           re.sub(r"[a-z():\s]", "", clean))
            if all_dashes and not num_values:
                logger.info(f"Type A row with all dashes (zero): {desc} in {filename} p{page_num+1}")
                return None  # Zero value deduction — skip

            return BottomSectionRow(
                row_type="A", raw_text=raw_line,
                description=desc, value=value,
                rate_pct=rate, deduction=deduction,
                source_file=filename, page_num=page_num,
            )

        # === TYPE B — Post-Cutoff Exclusion Row ===
        # Must have: year label AND a monetary value, NO rate
        if year_label and num_values and not has_rate:
            total_value = max(num_values)  # Largest number is total excluded

            # Try to extract funding split (grant/surplus portions)
            grant_portion = 0.0
            surplus_portion = 0.0
            if any(kw in clean for kw in ["grant"]):
                grant_portion = total_value
            elif any(kw in clean for kw in ["surplus"]):
                surplus_portion = total_value

            return BottomSectionRow(
                row_type="B", raw_text=raw_line,
                description=f"Post-cutoff exclusion ({year_label})",
                value=total_value, year_label=year_label,
                grant_portion=grant_portion,
                surplus_portion=surplus_portion,
                source_file=filename, page_num=page_num,
            )

        # === TYPE D — Unrecognised Row ===
        # Only flag if the row has meaningful content
        clean_content = re.sub(r"[\d\s\.\-–,()]", "", clean)
        if len(clean_content) > 3:
            return BottomSectionRow(
                row_type="D", raw_text=raw_line,
                description=f"Unrecognised: {clean[:60]}",
                source_file=filename, page_num=page_num,
            )

        return None

    def _extract_gfa_totals(
        self, lines: List[str], lines_lower: List[str], subtotal_idx: int
    ) -> Tuple[float, float]:
        """Extract GFA opening and closing totals from the subtotal row."""
        if subtotal_idx < 0 or subtotal_idx >= len(lines):
            return 0.0, 0.0

        numbers = re.findall(r"(\d+\.\d+)", lines[subtotal_idx])
        if len(numbers) >= 2:
            vals = [float(n) for n in numbers]
            # First large number is usually GFA opening, second is GFA closing
            large_vals = [v for v in vals if v > 50]
            if len(large_vals) >= 2:
                return large_vals[0], large_vals[1]

        return 0.0, 0.0

# Signal words for finding depreciation-related content
FIXED_ASSET_SIGNALS = [
    "fixed assets", "depreciation", "gross fixed assets", "gfa",
    "rate of depreciation", "asset group", "asset category",
    "accumulated depreciation", "net fixed assets", "nfa",
]

AUDITED_SIGNALS = [
    "as per audited accounts", "audited depreciation",
    "depreciation for the year", "audited", "actual",
]

FUNDING_SIGNALS = [
    "consumer contribution", "government grant", "capital subsidy",
    "accumulated surplus", "regulatory surplus", "deposit works",
    "grant", "contribution",
]


class DepreciationDataFinder:
    """
    Step 1: Scans ALL submitted PDFs for depreciation data using PyMuPDF.
    Finds fixed asset tables, audited figures, funding source deductions,
    balance sheet data, and narrative explanations.
    Now also uses DepreciationTableParser for structured table reading.
    """

    def __init__(self, rate_schedule: AnnexureRateSchedule):
        self.rate_schedule = rate_schedule
        self.table_parser = DepreciationTableParser(rate_schedule)

    def find_all(self, state: dict) -> DepreciationExtraction:
        """Scan all petition PDFs and extract depreciation data."""
        import fitz

        extraction = DepreciationExtraction()
        pdf_paths = self._get_pdf_paths(state)
        extraction.source_files = [str(p) for p in pdf_paths]

        all_dep_figures = []  # For cross-document verification
        all_parsed_tables = []  # Structured table parsing results

        for path in pdf_paths:
            try:
                doc = fitz.open(path)
                filename = os.path.basename(path)

                for page_num, page in enumerate(doc):
                    text = page.get_text("text")
                    text_lower = text.lower()

                    # === Structured table parsing (NEW) ===
                    table_result = self.table_parser.parse_page(
                        text, filename, page_num
                    )
                    if table_result:
                        all_parsed_tables.append(table_result)

                        # Merge structured table data into extraction
                        if table_result["gross_depreciation"] > extraction.gross_depreciation:
                            extraction.gross_depreciation = table_result["gross_depreciation"]
                        if table_result["gfa_opening"] > 0:
                            extraction.gfa_opening = table_result["gfa_opening"]
                        if table_result["gfa_closing"] > 0:
                            extraction.gfa_closing = table_result["gfa_closing"]

                        # Store bottom section rows
                        for brow in table_result.get("bottom_section_rows", []):
                            extraction.bottom_section_rows.append({
                                "type": brow.row_type,
                                "description": brow.description,
                                "value": brow.value,
                                "rate_pct": brow.rate_pct,
                                "deduction": brow.deduction,
                                "year_label": brow.year_label,
                                "raw_text": brow.raw_text,
                                "source_file": brow.source_file,
                                "page": brow.page_num + 1,
                            })

                        # Convert structured bottom rows to FundingSource entries
                        for brow in table_result.get("bottom_section_rows", []):
                            if brow.row_type == "A" and brow.value > 0:
                                # Type A — pre-cutoff deduction
                                source_type = "cc"
                                if "grant" in brow.description.lower():
                                    source_type = "pre_cutoff_grant"
                                elif "deposit" in brow.description.lower():
                                    source_type = "deposit_works"
                                elif "surplus" in brow.description.lower():
                                    source_type = "surplus"

                                # Compute correct deduction at standard rate
                                rate = brow.rate_pct if brow.rate_pct > 0 else DEFAULT_RATE
                                correct_deduction = round(brow.value * rate / 100, 2)

                                fs = FundingSource(
                                    source_type=source_type,
                                    description=f"{brow.description} (table row)",
                                    value=brow.value,
                                    asset_rate_pct=rate,
                                    deduction_amount=correct_deduction,
                                    method="deduct_after",
                                    source_document=f"{filename} p{brow.page_num+1}",
                                    verified=False,
                                    addition_year=brow.year_label,
                                )
                                extraction.funding_deductions.append(fs)
                                logger.info(
                                    f"Table Type A: {brow.description} = "
                                    f"{brow.value}L × {rate}% = {correct_deduction}L"
                                )

                            elif brow.row_type == "B":
                                # Type B — post-cutoff exclusion (informational)
                                fs = FundingSource(
                                    source_type="post_cutoff_grant",
                                    description=f"{brow.description} (excluded from GFA base)",
                                    value=brow.value,
                                    method="exclude_from_base",
                                    source_document=f"{filename} p{brow.page_num+1}",
                                    addition_year=brow.year_label,
                                    grant_portion=brow.grant_portion,
                                    surplus_portion=brow.surplus_portion,
                                )
                                # Don't add deduction — already excluded from gross
                                extraction.funding_deductions.append(fs)
                                logger.info(
                                    f"Table Type B: {brow.description} = "
                                    f"{brow.value}L (excluded from base, no deduction)"
                                )

                            elif brow.row_type == "C":
                                # Type C — result row
                                if brow.value > 0:
                                    extraction.claimed_depreciation = brow.value
                                    logger.info(
                                        f"Table Type C: Claimed/result = {brow.value}L"
                                    )

                            elif brow.row_type == "D":
                                # Type D — unrecognised
                                extraction.discrepancies.append(
                                    f"Unrecognised row in bottom section: "
                                    f"{brow.raw_text[:100]} ({filename} p{brow.page_num+1})"
                                )

                    # === Existing extraction logic (kept as fallback) ===
                    # Extract funding source deductions (regex-based)
                    self._extract_funding_deductions(
                        text, text_lower, extraction, filename, page_num
                    )

                    # Extract audited depreciation figure
                    audited_val = self._extract_audited_figure(text_lower)
                    if audited_val > 0:
                        all_dep_figures.append((audited_val, filename, page_num))
                        if audited_val > extraction.audited_depreciation:
                            extraction.audited_depreciation = audited_val

                    # Extract depreciation narrative
                    self._extract_narratives(text, text_lower, extraction)

                doc.close()

            except Exception as e:
                logger.warning(f"DepreciationDataFinder failed on {path}: {e}")

        # ── Extract pre-cutoff depreciation from Form D 3.5 ──
        # Form D 3.5 has 3 sections (GFA, Depreciation, NFA), each with a "Total" row.
        # The 2nd "Total" is the depreciation section total.
        # PyMuPDF puts each cell on a separate line, so numbers follow "Total" on
        # subsequent lines. The 3rd number = "For FY Before 01-04-20" = pre-cutoff dep.
        for path in pdf_paths:
            if extraction.pre_cutoff_depreciation > 0:
                break
            try:
                doc = fitz.open(path)
                filename = os.path.basename(path)
                for page_num, page in enumerate(doc):
                    if extraction.pre_cutoff_depreciation > 0:
                        break
                    text = page.get_text("text")
                    text_lower = text.lower()
                    # Look for Form D 3.5 with Before/After cutoff columns
                    if ("before" in text_lower and "01-04-20" in text
                            and "depreciation" in text_lower):
                        lines = text.split("\n")
                        # Find the 2nd standalone "Total" — this is the depreciation Total
                        total_count = 0
                        for i, line in enumerate(lines):
                            if line.strip().lower() == "total":
                                total_count += 1
                                if total_count == 2:  # 2nd Total = depreciation section
                                    # Collect numbers from the next 20 lines
                                    following_nums = []
                                    for j in range(i + 1, min(i + 25, len(lines))):
                                        next_line = lines[j].strip()
                                        # Stop if we hit a label (Less, Depreciation for, etc.)
                                        if next_line and not next_line.startswith("-") and not re.match(r"^[\d,.\-]+$", next_line):
                                            break
                                        nums = re.findall(r"[\d,]+", next_line)
                                        for n in nums:
                                            n_clean = n.replace(",", "")
                                            try:
                                                val = float(n_clean)
                                                if val > 100:
                                                    following_nums.append(val)
                                            except ValueError:
                                                pass
                                    # Column order: cum_before, cum_after, fy_before, fy_after, ...
                                    # The 3rd number = "For FY Before" = pre-cutoff dep
                                    if len(following_nums) >= 3:
                                        fy_before = following_nums[2]
                                        val_lakhs = round(fy_before / 100000.0, 2)
                                        if 5 < val_lakhs < 500:
                                            extraction.pre_cutoff_depreciation = val_lakhs
                                            logger.info(
                                                f"Form D 3.5: Pre-cutoff dep total = "
                                                f"{val_lakhs:.2f}L "
                                                f"(raw={fy_before}, from {filename} p{page_num+1})"
                                            )
                                            logger.info(
                                                f"  All nums (lakhs): "
                                                f"{[round(v/100000, 2) for v in following_nums]}L"
                                            )
                                    break  # Found 2nd Total, done with this page
                doc.close()
            except Exception as e:
                logger.warning(f"Pre-cutoff dep scan failed on {path}: {e}")

        # Store table reading summary
        extraction.table_reading_summary = all_parsed_tables
        if all_parsed_tables:
            logger.info(
                f"Structured table parsing: {len(all_parsed_tables)} tables found, "
                f"gross dep={extraction.gross_depreciation:.2f}L"
            )

        # Also pull from the already-extracted state data
        self._enrich_from_state(state, extraction)

        # Cross-document verification
        self._cross_verify(all_dep_figures, extraction)

        return extraction

    def _get_pdf_paths(self, state: dict) -> List[str]:
        """Get all PDF file paths from the state."""
        paths = []
        if "petition_pdf_path" in state and state["petition_pdf_path"]:
            paths.append(state["petition_pdf_path"])
        if "annexure_pdf_paths" in state and state["annexure_pdf_paths"]:
            paths.extend(state["annexure_pdf_paths"])
        return [p for p in paths if p and os.path.exists(str(p))]

    def _extract_funding_deductions(
        self, text: str, text_lower: str, extraction: DepreciationExtraction,
        filename: str, page_num: int
    ):
        """
        Extract CC, grant, and surplus deduction values from structured table rows.
        
        CONSERVATIVE APPROACH: Only match very specific patterns that appear
        in actual depreciation table deduction rows, NOT in narrative text.
        
        CRITICAL: Table rows start with serial numbers like "17 Less: Consumer..."
        The serial number (17) is NOT the value. We strip leading serial numbers
        and only match numbers WITH decimal points (financial values like 7.89).
        """
        lines = text_lower.split("\n")
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # === CONSUMER CONTRIBUTION ===
            is_cc_deduction_row = (
                ("less" in line and "consumer" in line and "contribution" in line) or
                ("consumer" in line and "contribution" in line and ("(-)" in line or "deduct" in line))
            )
            
            if is_cc_deduction_row:
                # Strip leading serial number: "17 less: consumer..." → "less: consumer..."
                value_text = re.sub(r"^\d+\s+", "", line)
                # Also strip the label text to isolate the number columns
                value_text = re.sub(r"less\s*:?\s*consumer['s]*\s*contribution\s*", "", value_text)
                # Add next line for multi-line tables
                if i + 1 < len(lines):
                    value_text += " " + lines[i + 1].strip()
                
                # Only match numbers WITH decimal points (7.89, not bare integers)
                # Also match numbers like "14.96" — must have a decimal
                numbers = re.findall(r"(\d+\.\d+)", value_text)
                
                if numbers:
                    # Take the FIRST decimal number found (most likely the current value)
                    val = float(numbers[0])
                    if 0.5 < val < 500:
                        existing_cc = [fs for fs in extraction.funding_deductions if fs.source_type == "cc"]
                        if not existing_cc or val > existing_cc[0].value:
                            if existing_cc:
                                extraction.funding_deductions.remove(existing_cc[0])
                            extraction.funding_deductions.append(FundingSource(
                                source_type="cc",
                                description="Consumer Contribution",
                                value=val,
                                asset_rate_pct=self.rate_schedule.get_rate("distribution"),
                                deduction_amount=0.0,
                                method="deduct_after",
                                source_document=f"{filename} (page {page_num + 1})",
                                verified=False,
                            ))
                            logger.info(f"Found CC deduction row: Rs.{val:.2f}L in {filename} p{page_num+1}")
                else:
                    # All dashes — CC is zero or not applicable on this page
                    logger.info(f"CC deduction row found but all dashes (zero) in {filename} p{page_num+1}")
            
            # === GOVERNMENT GRANTS ===
            is_grant_deduction_row = (
                "less" in line and "grant" in line
            )
            
            if is_grant_deduction_row:
                # Strip leading serial number
                value_text = re.sub(r"^\d+\s+", "", line)
                value_text = re.sub(r"less\s*:?\s*(?:government\s*)?grants?\s*", "", value_text)
                if i + 1 < len(lines):
                    value_text += " " + lines[i + 1].strip()
                
                # Only match decimal numbers
                numbers = re.findall(r"(\d+\.\d+)", value_text)
                
                if numbers:
                    val = float(numbers[0])
                    if 0.5 < val < 5000:
                        extraction.funding_deductions.append(FundingSource(
                            source_type="pre_cutoff_grant",
                            description="Government Grant",
                            value=val,
                            asset_rate_pct=self.rate_schedule.default_rate,
                            deduction_amount=0.0,
                            method="deduct_after",
                            source_document=f"{filename} (page {page_num + 1})",
                            verified=False,
                        ))
                        logger.info(f"Found grant deduction row: Rs.{val:.2f}L in {filename} p{page_num+1}")
                else:
                    logger.info(f"Grant deduction row found but all dashes (zero) in {filename} p{page_num+1}")

    def _extract_audited_figure(self, text_lower: str) -> float:
        """Extract audited depreciation figure from text."""
        clean = text_lower.replace("\n", " ")
        patterns = [
            r"(?:as\s*per\s*)?audited\s*(?:accounts?\s*)?depreciation.*?(\d+\.?\d*)",
            r"depreciation\s*(?:for\s*the\s*year\s*)?(?:as\s*per\s*)?audited.*?(\d+\.?\d*)",
            r"audited\s*depreciation.*?rs\.?\s*(\d+\.?\d*)",
        ]
        best = 0.0
        for pattern in patterns:
            for m in re.finditer(pattern, clean):
                val = float(m.group(1))
                if val > best and 0.5 < val < 5000:
                    best = val
        return best

    def _extract_narratives(
        self, text: str, text_lower: str, extraction: DepreciationExtraction
    ):
        """Extract relevant narrative paragraphs about depreciation."""
        if "depreciation" not in text_lower:
            return
        lines = text.split("\n")
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if any(sig in line_lower for sig in ["consumer contribution",
                                                   "government grant",
                                                   "surplus",
                                                   "funded",
                                                   "excluded"]):
                context = " ".join(lines[max(0, i - 1):min(len(lines), i + 3)])
                if len(context) > 20 and context not in extraction.narrative_notes:
                    extraction.narrative_notes.append(context.strip())

    def _enrich_from_state(
        self, state: dict, extraction: DepreciationExtraction
    ):
        """Pull additional data from the already-extracted state dict."""
        # Get claimed depreciation from the state
        claimed = state.get("claimed_expenses", {})
        if isinstance(claimed, dict):
            extraction.claimed_depreciation = claimed.get("depreciation", 0.0)

        # Get GFA from cap_analysis if available
        cap_analysis = state.get("cap_analysis", {})
        if isinstance(cap_analysis, dict):
            extraction.gross_depreciation = cap_analysis.get("gfa", 0.0)

        # If no audited figure found, use claimed as fallback
        if extraction.audited_depreciation == 0 and extraction.claimed_depreciation > 0:
            extraction.audited_depreciation = extraction.claimed_depreciation

    def _cross_verify(
        self, all_figures: List[Tuple[float, str, int]],
        extraction: DepreciationExtraction
    ):
        """Cross-document verification — Step 1 Rule."""
        if len(all_figures) < 2:
            return

        values = [f[0] for f in all_figures]
        if max(values) - min(values) > ROUNDING_TOLERANCE:
            extraction.discrepancies.append(
                f"Depreciation figures disagree across documents: "
                f"{', '.join(f'Rs.{v:.2f}L in {fn} p{p+1}' for v, fn, p in all_figures)}. "
                f"Using audited accounts figure: Rs.{extraction.audited_depreciation:.2f}L."
            )


def enhanced_cross_verify(
    extraction: DepreciationExtraction,
    prior_year_data: Optional[Dict[str, Any]] = None,
    rate_schedule: Optional[AnnexureRateSchedule] = None,
) -> Tuple[List[str], List[str]]:
    """
    Enhanced cross-verification checks A-F from the depreciation table spec.
    Returns (flags, clarification_items).
    """
    flags: List[str] = []
    clarifications: List[str] = []

    # === CHECK A — Opening Balance Continuity ===
    if prior_year_data and extraction.accumulated_dep_opening > 0:
        prior_closing = prior_year_data.get("accumulated_dep_closing", 0)
        if prior_closing > 0:
            diff = abs(extraction.accumulated_dep_opening - prior_closing)
            if diff > ROUNDING_TOLERANCE:
                flags.append(
                    f"CHECK A FAIL: Opening accumulated depreciation "
                    f"({extraction.accumulated_dep_opening:.2f}L) does not match "
                    f"prior order closing ({prior_closing:.2f}L). "
                    f"Difference: Rs.{diff:.2f}L."
                )

    # === CHECK B — Consumer Contribution Direction ===
    if prior_year_data:
        prior_cc = prior_year_data.get("consumer_contribution", 0)
        current_cc = extraction.balance_sheet_cc
        if current_cc > 0 and prior_cc > 0 and current_cc < prior_cc:
            flags.append(
                f"CHECK B FAIL: Current CC ({current_cc:.2f}L) is LESS than "
                f"prior CC ({prior_cc:.2f}L). CC can only increase as new "
                f"consumers connect. Possible error in petition data."
            )

    # === CHECK C — GFA Continuity ===
    if prior_year_data and extraction.gfa_opening > 0:
        prior_gfa_closing = prior_year_data.get("gfa_closing", 0)
        if prior_gfa_closing > 0:
            diff = abs(extraction.gfa_opening - prior_gfa_closing)
            if diff > ROUNDING_TOLERANCE:
                flags.append(
                    f"CHECK C FAIL: Opening GFA ({extraction.gfa_opening:.2f}L) "
                    f"does not match prior order closing GFA "
                    f"({prior_gfa_closing:.2f}L). Difference: Rs.{diff:.2f}L."
                )

    # === CHECK D — Land Zero Check ===
    for group in extraction.asset_groups:
        if rate_schedule and rate_schedule.is_land(group.category):
            if group.depreciation_amount > 0:
                flags.append(
                    f"CHECK D FAIL: Land asset '{group.category}' shows "
                    f"depreciation of Rs.{group.depreciation_amount:.2f}L. "
                    f"Land rows must always be zero. Override applied."
                )
                group.depreciation_amount = 0.0

    # Also check table-parsed asset groups
    for table in extraction.table_reading_summary:
        for ag in table.get("asset_groups", []):
            if ag.get("is_land", False) and ag.get("depreciation", 0) > 0:
                flags.append(
                    f"CHECK D FAIL: Land asset row shows depreciation "
                    f"of Rs.{ag['depreciation']:.2f}L in {table['filename']}. "
                    f"Override applied to zero."
                )

    # === CHECK E — Rate Consistency ===
    if rate_schedule:
        for table in extraction.table_reading_summary:
            for ag in table.get("asset_groups", []):
                if ag.get("is_land"):
                    continue
                table_rate = ag.get("rate_pct", 0)
                if table_rate > 0:
                    desc = ag.get("description", "")
                    expected_rate = rate_schedule.get_rate(desc)
                    if expected_rate > 0 and abs(table_rate - expected_rate) > 0.5:
                        flags.append(
                            f"CHECK E: Rate for '{desc[:40]}' is {table_rate}% "
                            f"vs Annexure 1 standard {expected_rate}%. "
                            f"Deviation may indicate over-13-year asset."
                        )

    # === CHECK F — Post-Cutoff Row Completeness ===
    for brow in extraction.bottom_section_rows:
        if brow.get("type") == "B":
            year = brow.get("year_label", "")
            value = brow.get("value", 0)
            if value > 0 and not brow.get("grant_portion") and not brow.get("surplus_portion"):
                clarifications.append(
                    f"CHECK F: Post-cutoff exclusion in {year} shows "
                    f"total excluded value Rs.{value:.2f}L but does not "
                    f"split between surplus and grant portions. "
                    f"Please provide breakdown."
                )

    return flags, clarifications


# ═══════════════════════════════════════════════════════════════════
# Step 2: Funding Source Identifier
# ═══════════════════════════════════════════════════════════════════

class FundingSourceIdentifier:
    """
    Identifies and validates all funding sources with proper priority:
      Priority 1: Previous KSERC Order (highest authority)
      Priority 2: Current Petition PDFs
      Priority 3: Firestore Cache
    """

    def __init__(self, rate_schedule: AnnexureRateSchedule):
        self.rate_schedule = rate_schedule

    def identify(
        self,
        extraction: DepreciationExtraction,
        prior_year_data: Optional[Dict[str, Any]] = None,
        firestore_data: Optional[Dict[str, Any]] = None,
    ) -> List[FundingSource]:
        """
        Build the final authoritative funding source list.
        Prior order values override petition values.
        """
        sources = list(extraction.funding_deductions)

        # Priority 1 & 3: Override with prior order / Firestore data
        prior = prior_year_data or firestore_data or {}
        if prior:
            sources = self._apply_prior_overrides(sources, prior)

        # Deduplicate by source_type (keep highest value per type)
        sources = self._deduplicate(sources)

        # Calculate deduction amounts (skip info_only items)
        for src in sources:
            if src.method == "info_only":
                src.deduction_amount = 0.0  # informational only, no deduction
                continue
            if src.asset_rate_pct == 0:
                src.asset_rate_pct = self.rate_schedule.default_rate
            src.deduction_amount = round(src.value * src.asset_rate_pct / 100.0, 2)

        return sources

    def _apply_prior_overrides(
        self,
        sources: List[FundingSource],
        prior: Dict[str, Any],
    ) -> List[FundingSource]:
        """Override petition values with authoritative prior order values."""
        # Consumer Contribution from prior order
        prior_cc = prior.get("consumer_contribution", {})
        if isinstance(prior_cc, dict) and prior_cc.get("value", 0) > 0:
            # Remove any petition CC and replace
            sources = [s for s in sources if s.source_type != "cc"]
            sources.append(FundingSource(
                source_type="cc",
                description="Consumer Contribution (from prior KSERC order)",
                value=prior_cc["value"],
                asset_rate_pct=prior_cc.get("asset_rate", self.rate_schedule.default_rate),
                method="deduct_after",
                verified=True,
                source_document="Prior KSERC Truing-Up Order",
            ))

        # === NEW: Process prior_exclusions from precedent DB ===
        prior_exclusions = prior.get("prior_exclusions", [])
        if prior_exclusions:
            logger.info(f"Processing {len(prior_exclusions)} exclusion records from prior KSERC order")
            # Split into pre-cutoff grants and post-cutoff exclusions
            pre_cutoff = [e for e in prior_exclusions if e.get("type") == "grant_pre_cutoff"]
            post_cutoff = [e for e in prior_exclusions if e.get("type") == "post_cutoff_exclusion"]

            # Pre-cutoff grants: apply as deductions after calculation
            if pre_cutoff:
                sources = [s for s in sources if s.source_type != "pre_cutoff_grant"]
                for g in pre_cutoff:
                    sources.append(FundingSource(
                        source_type="pre_cutoff_grant",
                        description=g.get("description", "Government Grant (prior order)"),
                        value=g.get("value", 0),
                        asset_rate_pct=g.get("rate_pct", self.rate_schedule.default_rate),
                        method="deduct_after",
                        verified=True,
                        source_document="Prior KSERC Truing-Up Order",
                    ))
                    logger.info(
                        f"  Pre-cutoff grant: {g.get('description', '')[:50]} "
                        f"val={g.get('value', 0):.2f}L rate={g.get('rate_pct', 0):.2f}%"
                    )

            # Post-cutoff exclusions: informational only
            # These record which asset additions KSERC excluded in the prior year.
            # Their impact is already captured in the precedent cap
            # (prior_approved × 1.10), so we DON'T create actual deductions here.
            if post_cutoff:
                sources = [s for s in sources if s.source_type != "post_cutoff_grant"]
                for ex in post_cutoff:
                    sources.append(FundingSource(
                        source_type="post_cutoff_grant",
                        description=f"Post-cutoff exclusion ({ex.get('year_label', 'unknown')}): {ex.get('description', '')}",
                        value=ex.get("value", 0),
                        asset_rate_pct=0.0,  # zero rate = no deduction
                        method="info_only",
                        verified=True,
                        source_document="Prior KSERC Truing-Up Order",
                        addition_year=ex.get("year_label", ""),
                        grant_portion=ex.get("grant_portion", 0),
                        surplus_portion=ex.get("surplus_portion", 0),
                    ))
                    logger.info(
                        f"  Post-cutoff [INFO]: {ex.get('year_label', '?')} "
                        f"val={ex.get('value', 0):.2f}L "
                        f"(grant={ex.get('grant_portion', 0):.2f}L + "
                        f"surplus={ex.get('surplus_portion', 0):.2f}L)"
                    )

            return sources

        # Legacy: Pre-cutoff grants from prior order (old format)
        prior_grants = prior.get("pre_cutoff_grants", [])
        if prior_grants:
            sources = [s for s in sources if s.source_type != "pre_cutoff_grant"]
            for g in prior_grants:
                sources.append(FundingSource(
                    source_type="pre_cutoff_grant",
                    description=g.get("description", "Government Grant (prior order)"),
                    value=g.get("value", 0),
                    asset_rate_pct=g.get("asset_rate", self.rate_schedule.default_rate),
                    method="deduct_after",
                    verified=True,
                    source_document="Prior KSERC Truing-Up Order",
                ))
        else:
            # Prior order exists but has NO grants — suppress petition grants
            petition_grants = [s for s in sources if s.source_type == "pre_cutoff_grant"]
            if petition_grants:
                logger.info(
                    f"Suppressing {len(petition_grants)} PDF-extracted grant(s) — "
                    f"prior order has no grant deductions"
                )
                sources = [s for s in sources if s.source_type != "pre_cutoff_grant"]

        # Legacy: Post-cutoff exclusions from prior order (old format)
        prior_post = prior.get("post_cutoff_exclusions", [])
        if prior_post:
            sources = [s for s in sources if s.source_type != "post_cutoff_grant"]
            for ex in prior_post:
                sources.append(FundingSource(
                    source_type="post_cutoff_grant",
                    description=f"Post-cutoff exclusion ({ex.get('addition_year', 'unknown')})",
                    value=ex.get("total_excluded", 0),
                    asset_rate_pct=ex.get("asset_rate", self.rate_schedule.default_rate),
                    method="exclude_from_base",
                    verified=True,
                    source_document="Prior KSERC Truing-Up Order",
                    addition_year=ex.get("addition_year", ""),
                    grant_portion=ex.get("grant_portion", 0),
                    surplus_portion=ex.get("surplus_portion", 0),
                    own_funds_portion=ex.get("own_funds_portion", 0),
                ))

        return sources

    def _deduplicate(self, sources: List[FundingSource]) -> List[FundingSource]:
        """Keep the highest value per source_type. Dedup grants by value."""
        by_type: Dict[str, FundingSource] = {}
        # For grants, dedup by value — same amount from different pages is the same grant
        seen_grant_values: Dict[str, set] = {"pre_cutoff_grant": set(), "post_cutoff_grant": set()}

        result = []
        for src in sources:
            if src.source_type in seen_grant_values:
                val_key = round(src.value, 2)
                if val_key in seen_grant_values[src.source_type]:
                    continue  # Skip duplicate grant with same value
                seen_grant_values[src.source_type].add(val_key)
                result.append(src)
            else:
                if src.source_type not in by_type or src.value > by_type[src.source_type].value:
                    by_type[src.source_type] = src

        result.extend(by_type.values())
        return result


# ═══════════════════════════════════════════════════════════════════
# Step 3: Two-Level Exclusion Engine
# ═══════════════════════════════════════════════════════════════════

class TwoLevelExclusionEngine:
    """
    Implements the two-level exclusion process:
      Level 1 (Post-Cutoff): Exclude from GFA base before calculation
      Level 2 (Pre-Cutoff):  Calculate then deduct after
    """

    def compute(
        self,
        claimed_depreciation: float,
        audited_depreciation: float,
        funding_sources: List[FundingSource],
        gfa: float = 0.0,
        prior_approved: float = 0.0,
        kserc_gross_dep: float = 0.0,
        pre_cutoff_grant_dep: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Compute approved depreciation using two-level exclusion.
        
        Logic:
        A) KSERC table-based (when kserc_gross_dep available):
           approved = kserc_gross_dep - pre_cutoff_grant_dep
           (This replicates the exact KSERC order methodology)
        B) Precedent cap fallback:
           1. Start with claimed depreciation
           2. Apply precedent cap (prior_approved × 1.10)
           3. Apply Level 1/Level 2 deductions

        Returns a dict with the full workings.
        """
        starting_point = claimed_depreciation
        precedent_cap_applied = False
        precedent_cap_value = 0.0
        kserc_table_used = False

        # ─── Method A: KSERC table-based calculation ───
        # When we have the prior KSERC order's gross dep and pre-cutoff grant data,
        # use those directly. This exactly replicates the KSERC methodology:
        #   approved = KSERC_gross_dep - pre_cutoff_grant_dep
        # The KSERC gross dep already excludes all post-cutoff grant/surplus additions.
        if kserc_gross_dep > 0:
            kserc_table_used = True
            approved = round(kserc_gross_dep - pre_cutoff_grant_dep, 2)
            approved = round(max(approved, 0.0), 2)
            # Cap: approved cannot exceed claimed
            if approved > claimed_depreciation > 0:
                approved = claimed_depreciation
            logger.info(
                f"KSERC table-based calculation: "
                f"gross_dep={kserc_gross_dep:.2f}L - grant_dep={pre_cutoff_grant_dep:.2f}L "
                f"= {approved:.2f}L (claimed={claimed_depreciation:.2f}L)"
            )
            # Still compute Level 1/2 for reporting, but don't use them
            level1_sources = [fs for fs in funding_sources if fs.method == "exclude_from_base"]
            level2_sources = [fs for fs in funding_sources if fs.method == "deduct_after"]
            workings = {
                "audited_total": round(claimed_depreciation, 2),
                "kserc_table_used": True,
                "kserc_gross_dep": kserc_gross_dep,
                "pre_cutoff_grant_dep": pre_cutoff_grant_dep,
                "precedent_cap_applied": False,
                "precedent_cap_value": 0.0,
                "after_precedent_cap": 0.0,
                "level1_exclusion_adjustment": 0.0,
                "level1_details": [],
                "level2_deductions": pre_cutoff_grant_dep,
                "level2_details": [
                    {
                        "description": "Pre-cutoff grant dep (from prior KSERC table)",
                        "value": pre_cutoff_grant_dep,
                        "rate_pct": 0,
                        "deduction": pre_cutoff_grant_dep,
                    }
                ],
                "total_deductions": pre_cutoff_grant_dep,
                "final_approved": approved,
            }
            return workings

        # ─── Method C: Prior-year grant deduction with petition data ───
        # When we have the prior KSERC order's grant deduction rate but NOT a
        # hardcoded kserc_gross_dep, compute the KSERC-style calculation from
        # petition data:
        #   1. Start with claimed dep (after licensee's own deductions)
        #   2. Add back licensee's grant deduction (to get raw table total)
        #   3. Apply level 1 exclusions (post-cutoff additions)
        #   4. Subtract prior-year pre_cutoff_grant_dep
        if pre_cutoff_grant_dep > 0:
            kserc_table_used = True
            # Level 1: Post-cutoff exclusions (exclude from base)
            level1_sources = [fs for fs in funding_sources if fs.method == "exclude_from_base"]
            level1_adjustment = sum(fs.deduction_amount for fs in level1_sources)

            # Find licensee's own grant deduction to reverse it
            licensee_grant_deductions = [
                fs for fs in funding_sources
                if fs.method == "deduct_after" and "grant" in fs.source_type.lower()
            ]
            licensee_grant_total = sum(fs.deduction_amount for fs in licensee_grant_deductions)

            # Reconstruct: claimed already has licensee's deduction removed
            # So: raw_total = claimed + licensee_grant_total
            # Then: kserc_base = raw_total - level1_exclusions
            # Then: approved = kserc_base - pre_cutoff_grant_dep
            raw_total = round(claimed_depreciation + licensee_grant_total, 2)
            kserc_base = round(raw_total - level1_adjustment, 2)
            approved = round(kserc_base - pre_cutoff_grant_dep, 2)
            approved = round(max(approved, 0.0), 2)

            # Cap: approved cannot exceed claimed
            if approved > claimed_depreciation > 0:
                approved = claimed_depreciation

            logger.info(
                f"KSERC petition-based calculation: "
                f"claimed={claimed_depreciation:.2f}L + licensee_grants={licensee_grant_total:.2f}L "
                f"= raw_total={raw_total:.2f}L - level1={level1_adjustment:.2f}L "
                f"= kserc_base={kserc_base:.2f}L - prior_grant_dep={pre_cutoff_grant_dep:.2f}L "
                f"= {approved:.2f}L"
            )

            level2_sources = [fs for fs in funding_sources if fs.method == "deduct_after"]
            workings = {
                "audited_total": round(claimed_depreciation, 2),
                "kserc_table_used": True,
                "kserc_petition_based": True,
                "raw_table_total": raw_total,
                "level1_exclusion_adjustment": round(level1_adjustment, 2),
                "kserc_base_after_exclusions": kserc_base,
                "pre_cutoff_grant_dep": pre_cutoff_grant_dep,
                "precedent_cap_applied": False,
                "precedent_cap_value": 0.0,
                "after_precedent_cap": 0.0,
                "level1_details": [
                    {
                        "description": fs.description,
                        "value": fs.value,
                        "rate_pct": fs.asset_rate_pct,
                        "deduction": fs.deduction_amount,
                    }
                    for fs in level1_sources
                ],
                "level2_deductions": pre_cutoff_grant_dep,
                "level2_details": [
                    {
                        "description": "Pre-cutoff grant dep (from prior KSERC order)",
                        "value": pre_cutoff_grant_dep,
                        "rate_pct": 0,
                        "deduction": pre_cutoff_grant_dep,
                    }
                ],
                "total_deductions": round(level1_adjustment + pre_cutoff_grant_dep, 2),
                "final_approved": approved,
            }
            return workings

        # ─── Method B: Precedent cap fallback ───
        # Step 1: Apply precedent cap if prior order data exists
        if prior_approved > 0:
            precedent_cap_value = round(prior_approved * 1.10, 2)  # 10% escalation
            if starting_point > precedent_cap_value:
                starting_point = precedent_cap_value
                precedent_cap_applied = True
                logger.info(
                    f"Precedent cap applied: prior={prior_approved:.2f}L × 1.10 = "
                    f"{precedent_cap_value:.2f}L (claimed {claimed_depreciation:.2f}L)"
                )

        # Level 1: Post-cutoff exclusions (exclude from base)
        level1_sources = [fs for fs in funding_sources if fs.method == "exclude_from_base"]
        level1_adjustment = sum(fs.deduction_amount for fs in level1_sources)

        # Level 2: Pre-cutoff deductions (calculate then deduct)
        level2_sources = [fs for fs in funding_sources if fs.method == "deduct_after"]

        # CRITICAL: Avoid double-counting grant deductions when precedent cap is applied.
        if precedent_cap_applied:
            prior_order_grants = [
                fs for fs in level2_sources
                if fs.source_document == "Prior KSERC Truing-Up Order"
                and fs.source_type == "pre_cutoff_grant"
            ]
            active_level2 = [fs for fs in level2_sources if fs not in prior_order_grants]
            if prior_order_grants:
                logger.info(
                    f"Skipping {len(prior_order_grants)} prior-order grant deduction(s) "
                    f"— already included in precedent cap ({precedent_cap_value:.2f}L)"
                )
                for g in prior_order_grants:
                    g.deduction_amount = 0.0
            level2_deductions = sum(fs.deduction_amount for fs in active_level2)
        else:
            level2_deductions = sum(fs.deduction_amount for fs in level2_sources)

        total_deductions = round(level1_adjustment + level2_deductions, 2)
        approved = round(max(starting_point - total_deductions, 0.0), 2)

        # Cap: approved cannot exceed claimed
        if approved > claimed_depreciation > 0:
            approved = claimed_depreciation

        workings = {
            "audited_total": round(claimed_depreciation, 2),
            "precedent_cap_applied": precedent_cap_applied,
            "precedent_cap_value": precedent_cap_value,
            "after_precedent_cap": round(starting_point, 2),
            "level1_exclusion_adjustment": round(level1_adjustment, 2),
            "level1_details": [
                {
                    "description": fs.description,
                    "value": fs.value,
                    "rate_pct": fs.asset_rate_pct,
                    "deduction": fs.deduction_amount,
                }
                for fs in level1_sources
            ],
            "level2_deductions": round(level2_deductions, 2),
            "level2_details": [
                {
                    "description": fs.description,
                    "value": fs.value,
                    "rate_pct": fs.asset_rate_pct,
                    "deduction": fs.deduction_amount,
                }
                for fs in level2_sources
            ],
            "total_deductions": total_deductions,
            "final_approved": approved,
        }

        return workings


# ═══════════════════════════════════════════════════════════════════
# Step 8: Cross-Verification Suite
# ═══════════════════════════════════════════════════════════════════

class CrossVerificationSuite:
    """Runs all 8 verification checks before finalizing."""

    def run_checks(
        self,
        extraction: DepreciationExtraction,
        funding_sources: List[FundingSource],
        workings: Dict[str, Any],
        prior_year_data: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Run all checks, return list of flags."""
        flags = []

        # CHECK 1 — Consistency across documents
        if extraction.discrepancies:
            flags.extend(extraction.discrepancies)

        # CHECK 2 — CC cannot decrease
        prior = prior_year_data or {}
        prior_cc_val = prior.get("consumer_contribution", {}).get("value", 0)
        current_cc = [fs for fs in funding_sources if fs.source_type == "cc"]
        if current_cc and prior_cc_val > 0:
            curr_val = current_cc[0].value
            if curr_val < prior_cc_val - ROUNDING_TOLERANCE:
                flags.append(
                    f"⚠ CHECK 2 FAIL: Consumer Contribution decreased from "
                    f"Rs.{prior_cc_val:.2f}L to Rs.{curr_val:.2f}L. "
                    f"CC can only increase. Using prior order value."
                )

        # CHECK 3 — Depreciation cannot exceed GFA
        approved = workings.get("final_approved", 0)
        gfa = extraction.gross_depreciation
        if gfa > 0 and approved > gfa:
            flags.append(
                f"⚠ CHECK 3 FAIL: Approved depreciation Rs.{approved:.2f}L "
                f"exceeds GFA Rs.{gfa:.2f}L — impossible."
            )

        # CHECK 4 — All additions have funding source
        unconfirmed = [
            fs for fs in funding_sources if not fs.verified
        ]
        if unconfirmed:
            for fs in unconfirmed:
                flags.append(
                    f"ℹ CHECK 4: {fs.description} Rs.{fs.value:.2f}L "
                    f"from petition — not verified by prior order."
                )

        # CHECK 5 — Rate schedule match (basic check)
        for fs in funding_sources:
            if fs.asset_rate_pct == 0 and fs.source_type != "land":
                flags.append(
                    f"⚠ CHECK 5: {fs.description} has 0% rate — verify asset category."
                )

        # CHECK 6 — Accumulated depreciation continuity
        # (Would need prior year closing vs current year opening — flag if data available)

        # CHECK 7 — 90% cap check
        for ag in extraction.asset_groups:
            if ag.gfa_opening > 0 and ag.depreciation_amount > ag.gfa_opening * 0.9:
                flags.append(
                    f"⚠ CHECK 7: {ag.category} depreciation Rs.{ag.depreciation_amount:.2f}L "
                    f"exceeds 90% of GFA Rs.{ag.gfa_opening:.2f}L."
                )

        # CHECK 8 — Land check
        for ag in extraction.asset_groups:
            if "land" in ag.category.lower() and ag.depreciation_amount > 0:
                flags.append(
                    f"🚨 CHECK 8 FAIL: Land asset '{ag.category}' shows "
                    f"Rs.{ag.depreciation_amount:.2f}L depreciation. "
                    f"Land NEVER depreciates — overriding to zero."
                )

        # CHECK: Negative result
        if approved < 0:
            flags.append(
                f"🚨 CRITICAL: Calculation produced negative depreciation Rs.{approved:.2f}L. "
                f"Input values likely incorrect."
            )

        return flags


# ═══════════════════════════════════════════════════════════════════
# Step 9: Clarification Queue Builder
# ═══════════════════════════════════════════════════════════════════

class ClarificationQueueBuilder:
    """Collects items requiring licensee clarification."""

    def build(
        self,
        extraction: DepreciationExtraction,
        funding_sources: List[FundingSource],
        flags: List[str],
    ) -> List[str]:
        """Build list of items for WhatsApp clarification."""
        items = []

        # Document conflicts
        if extraction.discrepancies:
            items.append("Documents conflict on depreciation figure — "
                         "please confirm audited depreciation amount.")

        # Unverified funding sources
        for fs in funding_sources:
            if not fs.verified:
                items.append(
                    f"Funding source '{fs.description}' Rs.{fs.value:.2f}L "
                    f"from petition — no prior order verification. Please confirm."
                )

        # Any critical flags
        for f in flags:
            if "FAIL" in f or "CRITICAL" in f:
                items.append(f)

        return items


# ═══════════════════════════════════════════════════════════════════
# Step 10: Output Generator
# ═══════════════════════════════════════════════════════════════════

class DepreciationOutput:
    """Generates structured output in KSERC order language."""

    def generate(
        self,
        claimed: float,
        workings: Dict[str, Any],
        flags: List[str],
        clarifications: List[str],
        funding_sources: List[FundingSource],
        licensee: str = "",
        fy: str = "",
    ) -> DepreciationResult:
        """Generate the complete depreciation output."""
        approved = workings.get("final_approved", 0)
        total_deductions = workings.get("total_deductions", 0)

        # Build justification in KSERC order language
        justification = self._build_justification(
            claimed, approved, total_deductions, funding_sources
        )

        # Build Firestore payload
        firestore_payload = self._build_firestore_payload(
            licensee, fy, claimed, approved, workings, funding_sources
        )

        # Build disallowance entries for the auditor
        disallowances = []
        if total_deductions > 0:
            disallowances.append({
                "item": "Depreciation",
                "claimed": claimed,
                "approved": approved,
                "amount_cut": round(claimed - approved, 2) if claimed > approved else 0.0,
                "justification": justification,
            })

            # Individual deduction entries
            for fs in funding_sources:
                if fs.deduction_amount > 0:
                    disallowances.append({
                        "item": f"Depreciation ({fs.description})",
                        "claimed": fs.value,
                        "approved": 0.0,
                        "amount_cut": fs.deduction_amount,
                        "justification": (
                            f"Deduction of Rs.{fs.deduction_amount:.2f}L on "
                            f"{fs.description} (Rs.{fs.value:.2f}L × {fs.asset_rate_pct:.2f}%). "
                            f"Method: {fs.method.replace('_', ' ')}. "
                            f"Source: {fs.source_document or 'petition'}."
                        ),
                    })

        return DepreciationResult(
            claimed=claimed,
            approved=approved,
            workings=workings,
            justification=justification,
            flags=flags,
            clarification_items=clarifications,
            firestore_payload=firestore_payload,
            disallowances=disallowances,
        )

    def _build_justification(
        self,
        claimed: float,
        approved: float,
        total_deductions: float,
        funding_sources: List[FundingSource],
    ) -> str:
        """Build justification text in KSERC order language."""
        parts = [
            f"The licensee has claimed Rs.{claimed:.2f} lakh as depreciation for the year. "
            f"As per Regulation 27 of the Tariff Regulations 2021, "
            f"no depreciation is admissible on assets created through "
            f"consumer contribution, government grants, capital subsidies, "
            f"or accumulated regulatory surplus."
        ]

        for fs in funding_sources:
            if fs.deduction_amount > 0:
                parts.append(
                    f" The Commission deducts Rs.{fs.deduction_amount:.2f} lakh "
                    f"towards {fs.description.lower()} "
                    f"(Rs.{fs.value:.2f}L × {fs.asset_rate_pct:.2f}%)."
                )

        parts.append(
            f" The Commission hereby approves Rs.{approved:.2f} lakh "
            f"as depreciation for the year."
        )

        return "".join(parts)

    def _build_firestore_payload(
        self,
        licensee: str,
        fy: str,
        claimed: float,
        approved: float,
        workings: Dict[str, Any],
        funding_sources: List[FundingSource],
    ) -> Dict[str, Any]:
        """Build payload for Firestore storage."""
        cc_sources = [fs for fs in funding_sources if fs.source_type == "cc"]
        pre_grant_sources = [fs for fs in funding_sources if fs.source_type == "pre_cutoff_grant"]
        post_sources = [fs for fs in funding_sources if fs.source_type == "post_cutoff_grant"]

        payload = {
            "licensee": licensee,
            "financial_year": fy,
            "petition_claimed": claimed,
            "approved_depreciation": approved,
            "audited_total_before_deductions": workings.get("audited_total", 0),
        }

        if cc_sources:
            cc = cc_sources[0]
            payload["consumer_contribution"] = {
                "value": cc.value,
                "asset_rate": cc.asset_rate_pct,
                "deduction_amount": cc.deduction_amount,
                "source_document": cc.source_document,
                "method": "deduct_after",
            }

        if pre_grant_sources:
            payload["pre_cutoff_grants"] = [
                {
                    "description": g.description,
                    "value": g.value,
                    "asset_rate": g.asset_rate_pct,
                    "deduction_amount": g.deduction_amount,
                    "method": "deduct_after",
                }
                for g in pre_grant_sources
            ]

        if post_sources:
            payload["post_cutoff_exclusions"] = [
                {
                    "addition_year": ex.addition_year,
                    "total_excluded": ex.value,
                    "grant_portion": ex.grant_portion,
                    "surplus_portion": ex.surplus_portion,
                    "own_funds_portion": ex.own_funds_portion,
                    "asset_rate": ex.asset_rate_pct,
                    "method": "exclude_from_base",
                }
                for ex in post_sources
            ]

        return payload


# ═══════════════════════════════════════════════════════════════════
# Step 7: Firestore Persistence (Optional — degrades gracefully)
# ═══════════════════════════════════════════════════════════════════

class FirestoreDepreciationStore:
    """
    Stores and retrieves depreciation data from Firestore.
    Degrades gracefully if Firestore is unavailable.
    """

    def __init__(self):
        self.db = None
        try:
            import firebase_admin
            from firebase_admin import firestore as fs_module
            if not firebase_admin._apps:
                firebase_admin.initialize_app()
            self.db = fs_module.client()
            logger.info("Firestore depreciation store connected")
        except Exception as e:
            logger.info(f"Firestore not available (will use local fallback): {e}")

    @property
    def available(self) -> bool:
        return self.db is not None

    def get_prior_year(self, licensee: str, fy: str) -> Optional[Dict[str, Any]]:
        """Get the most recent prior year's depreciation data."""
        if not self.available:
            return None
        try:
            collection = self.db.collection("depreciation_records")
            docs = (
                collection
                .where("licensee", "==", licensee)
                .order_by("financial_year", direction="DESCENDING")
                .limit(5)
                .stream()
            )
            for doc in docs:
                data = doc.to_dict()
                if data.get("financial_year", "") < fy:
                    return data
        except Exception as e:
            logger.warning(f"Firestore read failed: {e}")
        return None

    def save(self, payload: Dict[str, Any]) -> bool:
        """Save depreciation record to Firestore."""
        if not self.available:
            return False
        try:
            licensee = payload.get("licensee", "unknown")
            fy = payload.get("financial_year", "unknown")
            doc_id = f"{licensee}_{fy}"
            self.db.collection("depreciation_records").document(doc_id).set(
                payload, merge=True
            )
            logger.info(f"Saved depreciation record to Firestore: {doc_id}")
            return True
        except Exception as e:
            logger.warning(f"Firestore write failed: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT — Full Depreciation Computation
# ═══════════════════════════════════════════════════════════════════

def compute_depreciation(
    state: dict,
    licensee: str = "",
    fy: str = "",
    prior_year_data: Optional[Dict[str, Any]] = None,
) -> DepreciationResult:
    """
    Main entry point: compute approved depreciation for a petition.

    This implements all 10 steps from the KSERC depreciation specification.

    Args:
        state: The full petition state dict (with pdf paths, claimed expenses, etc.)
        licensee: Licensee name (e.g., "KDHP", "Technopark")
        fy: Financial year (e.g., "2024-25")
        prior_year_data: Optional prior year Firestore data

    Returns:
        DepreciationResult with approved figure, workings, justification, etc.
    """
    logger.info(f"═══ Depreciation Engine: {licensee} FY {fy} ═══")

    # Initialize components
    rate_schedule = AnnexureRateSchedule()
    data_finder = DepreciationDataFinder(rate_schedule)
    funding_identifier = FundingSourceIdentifier(rate_schedule)
    exclusion_engine = TwoLevelExclusionEngine()
    verifier = CrossVerificationSuite()
    clarification_builder = ClarificationQueueBuilder()
    output_generator = DepreciationOutput()

    # Try Firestore for prior year data
    firestore_store = FirestoreDepreciationStore()
    if not prior_year_data and firestore_store.available:
        prior_year_data = firestore_store.get_prior_year(licensee, fy)
        if prior_year_data:
            logger.info(f"Loaded prior year data from Firestore: {prior_year_data.get('financial_year')}")

    # Also check the precedent DB (local JSON) — always merge KSERC-specific fields
    # even when Firestore provides the main prior_year_data, because Firestore
    # won't have our KSERC table data (kserc_gross_dep, kserc_nfa, etc.)
    prec_db_data = _load_from_precedent_db(licensee, fy)
    if prec_db_data:
        if not prior_year_data:
            prior_year_data = prec_db_data
        else:
            # Merge KSERC-specific fields from precedent DB into existing data
            for key in ["kserc_gross_dep", "pre_cutoff_grant_dep", "kserc_dep_base",
                        "excluded_post_cutoff_gfa", "kserc_nfa_net_of_grants",
                        "kserc_normative_loan", "kserc_net_nfa_for_ronfa", "kserc_ronfa_rate"]:
                if key in prec_db_data and key not in prior_year_data:
                    prior_year_data[key] = prec_db_data[key]
            # Also update approved_depreciation from precedent DB if more accurate
            if prec_db_data.get("approved_depreciation", 0) > 0:
                prior_year_data["approved_depreciation"] = prec_db_data["approved_depreciation"]
            logger.info(f"Merged KSERC data from precedent DB into prior_year_data")

    # Step 1: Find depreciation data
    logger.info("Step 1: Searching all PDFs for depreciation data...")
    extraction = data_finder.find_all(state)
    logger.info(
        f"  Found: claimed={extraction.claimed_depreciation:.2f}L, "
        f"audited={extraction.audited_depreciation:.2f}L, "
        f"gross={extraction.gross_depreciation:.2f}L, "
        f"{len(extraction.funding_deductions)} funding deductions, "
        f"{len(extraction.table_reading_summary)} tables parsed"
    )

    # Log table reading summary
    for table in extraction.table_reading_summary:
        logger.info(
            f"  Table: {table['filename']} p{table['page']} — "
            f"gross={table['gross_depreciation']:.2f}L, "
            f"{len(table.get('asset_groups', []))} assets, "
            f"{len(table.get('bottom_section_rows', []))} bottom rows"
        )
        for brow in table.get("bottom_section_rows", []):
            logger.info(
                f"    [{brow.row_type}] {brow.description}: "
                f"val={brow.value:.2f}L rate={brow.rate_pct}% ded={brow.deduction:.2f}L"
            )

    # Mark as provisional if no prior year data
    if not prior_year_data:
        extraction.is_provisional = True
        logger.info("  ⚠ No prior year data — results will be flagged as PROVISIONAL")

    # Step 2: Identify funding sources
    logger.info("Step 2: Identifying funding sources...")
    funding_sources = funding_identifier.identify(
        extraction, prior_year_data=prior_year_data
    )
    for fs in funding_sources:
        logger.info(f"  {fs.source_type}: Rs.{fs.value:.2f}L × {fs.asset_rate_pct}% = Rs.{fs.deduction_amount:.2f}L [{fs.method}]")

    # Step 3 + 5: Two-level exclusion & final calculation
    prior_approved_dep = prior_year_data.get("approved_depreciation", 0.0) if prior_year_data else 0.0
    # Extract KSERC table data if available (more accurate than precedent cap)
    kserc_gross_dep = prior_year_data.get("kserc_gross_dep", 0.0) if prior_year_data else 0.0
    pre_cutoff_grant_dep = prior_year_data.get("pre_cutoff_grant_dep", 0.0) if prior_year_data else 0.0

    # Override kserc_gross_dep with petition's own pre-cutoff depreciation if found
    # This comes from Form D 3.5 "Before 01-04-20" column total — dynamic, not hardcoded
    if extraction.pre_cutoff_depreciation > 0 and pre_cutoff_grant_dep > 0:
        kserc_gross_dep = extraction.pre_cutoff_depreciation
        logger.info(
            f"Step 3+5: Using petition pre-cutoff dep={kserc_gross_dep:.2f}L "
            f"(from Form D 3.5) with prior grant_dep={pre_cutoff_grant_dep:.2f}L"
        )
    elif kserc_gross_dep > 0:
        logger.info(f"Step 3+5: KSERC table-based calculation (gross_dep={kserc_gross_dep:.2f}L, grant_dep={pre_cutoff_grant_dep:.2f}L)...")
    else:
        logger.info(f"Step 3+5: Computing two-level exclusion (prior approved={prior_approved_dep:.2f}L)...")
    workings = exclusion_engine.compute(
        claimed_depreciation=extraction.claimed_depreciation,
        audited_depreciation=extraction.audited_depreciation,
        funding_sources=funding_sources,
        gfa=extraction.gross_depreciation,
        prior_approved=prior_approved_dep,
        kserc_gross_dep=kserc_gross_dep,
        pre_cutoff_grant_dep=pre_cutoff_grant_dep,
    )
    logger.info(f"  Claimed: {workings['audited_total']:.2f}L")
    if workings.get("precedent_cap_applied"):
        logger.info(f"  Precedent cap: {workings['precedent_cap_value']:.2f}L → after cap: {workings['after_precedent_cap']:.2f}L")
    logger.info(f"  Level 1 adjustment: -{workings['level1_exclusion_adjustment']:.2f}L")
    logger.info(f"  Level 2 deductions: -{workings['level2_deductions']:.2f}L")
    logger.info(f"  Final approved: {workings['final_approved']:.2f}L")

    # Add table reading data to workings
    workings["table_reading_summary"] = [
        {
            "filename": t["filename"],
            "page": t["page"],
            "gross_depreciation": t["gross_depreciation"],
            "gfa_opening": t.get("gfa_opening", 0),
            "gfa_closing": t.get("gfa_closing", 0),
            "asset_groups_count": len(t.get("asset_groups", [])),
            "bottom_rows_count": len(t.get("bottom_section_rows", [])),
        }
        for t in extraction.table_reading_summary
    ]
    workings["bottom_section_rows"] = extraction.bottom_section_rows
    workings["is_provisional"] = extraction.is_provisional

    # Step 8: Cross-verification (standard)
    logger.info("Step 8: Running cross-verification suite...")
    flags = verifier.run_checks(
        extraction, funding_sources, workings, prior_year_data
    )
    for f in flags:
        logger.info(f"  FLAG: {f}")

    # Step 8A: Enhanced cross-verification (Checks A-F)
    logger.info("Step 8A: Running enhanced cross-verification (Checks A-F)...")
    enhanced_flags, enhanced_clarifications = enhanced_cross_verify(
        extraction, prior_year_data, rate_schedule
    )
    flags.extend(enhanced_flags)
    for f in enhanced_flags:
        logger.info(f"  ENHANCED FLAG: {f}")

    # Step 9: Clarification queue
    clarifications = clarification_builder.build(extraction, funding_sources, flags)
    clarifications.extend(enhanced_clarifications)

    # First-time licensee flag
    if extraction.is_provisional:
        clarifications.append(
            f"No prior KSERC order available for {licensee}. "
            f"Using petition-reported values for funding source exclusions. "
            f"These have NOT been verified by a previous order. "
            f"Human review required before finalising."
        )
        flags.append("PROVISIONAL: No prior year KSERC order data available")

    # Step 10: Generate output
    logger.info("Step 10: Generating structured output...")
    result = output_generator.generate(
        claimed=extraction.claimed_depreciation,
        workings=workings,
        flags=flags,
        clarifications=clarifications,
        funding_sources=funding_sources,
        licensee=licensee,
        fy=fy,
    )

    # Step 7: Persist to Firestore
    if firestore_store.available and result.firestore_payload:
        firestore_store.save(result.firestore_payload)

    logger.info(
        f"═══ Depreciation Result: Claimed {result.claimed:.2f}L → "
        f"Approved {result.approved:.2f}L ═══"
    )

    return result


# ═══════════════════════════════════════════════════════════════════
# Helper: Load prior year data from the local precedent DB
# ═══════════════════════════════════════════════════════════════════

def _load_from_precedent_db(licensee: str, fy: str) -> Optional[Dict[str, Any]]:
    """
    Load prior year depreciation data from the local precedent_db.json.
    This is the fallback when Firestore is not available.
    Now includes full depreciation_details with grant exclusions, GFA, etc.
    """
    try:
        from src.rag.precedent_lookup import PrecedentLookup
        lookup = PrecedentLookup()
        if not lookup.available:
            return None

        history = lookup.get_licensee_history(licensee)
        if not history:
            return None

        # Find the most recent prior year
        prior_fys = sorted([f for f in history.keys() if f < fy], reverse=True)
        if not prior_fys:
            return None

        prior_fy = prior_fys[0]
        prior_data = history[prior_fy]

        # Convert to our format
        approved_dep = prior_data.get("approved_expenses", {}).get("depreciation", 0.0)

        result = {
            "licensee": licensee,
            "financial_year": prior_fy,
            "approved_depreciation": approved_dep,
        }

        # Extract CC from capital structure if available
        cap_struct = prior_data.get("capital_structure", {})
        cc_val = cap_struct.get("consumer_contribution", 0.0)
        if cc_val > 0:
            result["consumer_contribution"] = {
                "value": cc_val,
                "asset_rate": DEFAULT_RATE,
                "deduction_amount": round(cc_val * DEFAULT_RATE / 100.0, 2),
            }
        result["consumer_contribution_value"] = cc_val

        # Extract government grants from capital structure
        govt_grants = cap_struct.get("government_grants", 0.0)
        if govt_grants > 0:
            result["government_grants"] = govt_grants

        # Extract KSERC NFA chain data for RoNFA calculation
        kserc_nfa = cap_struct.get("kserc_nfa_net_of_grants", 0.0)
        if kserc_nfa > 0:
            result["kserc_nfa_net_of_grants"] = kserc_nfa
            result["kserc_normative_loan"] = cap_struct.get("kserc_normative_loan", 0.0)
            result["kserc_net_nfa_for_ronfa"] = cap_struct.get("kserc_net_nfa_for_ronfa", 0.0)
            result["kserc_ronfa_rate"] = cap_struct.get("kserc_ronfa_rate", 5.5)
            logger.info(
                f"  KSERC NFA chain: nfa={kserc_nfa:.2f}L, "
                f"loan={result['kserc_normative_loan']:.2f}L, "
                f"rate={result['kserc_ronfa_rate']}%"
            )

        # Extract full depreciation_details if available
        dep_details = prior_data.get("depreciation_details", {})
        if dep_details:
            result["gross_depreciation"] = dep_details.get("gross_depreciation", 0.0)
            result["gfa_opening"] = dep_details.get("gfa_opening", 0.0)
            result["gfa_closing"] = dep_details.get("gfa_closing", 0.0)
            result["accumulated_dep_opening"] = dep_details.get("accumulated_dep_opening", 0.0)
            result["accumulated_dep_closing"] = dep_details.get("accumulated_dep_closing", 0.0)

            # KSERC table-based calculation data
            kserc_gross = dep_details.get("kserc_gross_dep", 0.0)
            pre_cutoff_dep = dep_details.get("pre_cutoff_grant_dep", 0.0)
            if kserc_gross > 0:
                result["kserc_gross_dep"] = kserc_gross
                result["kserc_dep_base"] = dep_details.get("kserc_dep_base", 0.0)
                result["excluded_post_cutoff_gfa"] = dep_details.get("excluded_post_cutoff_gfa", 0.0)
                logger.info(
                    f"  KSERC table data: gross_dep={kserc_gross:.2f}L, "
                    f"grant_dep={pre_cutoff_dep:.2f}L → expected approved={kserc_gross - pre_cutoff_dep:.2f}L"
                )
            # Always load pre_cutoff_grant_dep (Method C needs it even without kserc_gross_dep)
            if pre_cutoff_dep > 0:
                result["pre_cutoff_grant_dep"] = pre_cutoff_dep
                if kserc_gross == 0:
                    logger.info(
                        f"  Prior-year grant dep: {pre_cutoff_dep:.2f}L "
                        f"(no kserc_gross_dep — Method C will compute from petition)"
                    )

            # Pass through exclusion records from prior year
            exclusions = dep_details.get("exclusions", [])
            if exclusions:
                result["prior_exclusions"] = exclusions
                logger.info(f"  Prior year has {len(exclusions)} exclusion records")
                for exc in exclusions:
                    logger.info(
                        f"    {exc.get('type', '?')}: {exc.get('description', '')[:60]} "
                        f"val={exc.get('value', 0):.2f}L"
                    )

            # Pass through asset group data
            asset_groups = dep_details.get("asset_groups", [])
            if asset_groups:
                result["prior_asset_groups"] = asset_groups

        logger.info(f"Loaded prior year data from precedent DB: {prior_fy} (dep={approved_dep:.2f}L)")
        return result

    except Exception as e:
        logger.warning(f"Precedent DB fallback failed: {e}")
        return None

