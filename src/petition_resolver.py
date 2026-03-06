"""
Petition Input Resolver
========================

Handles both input modes:
1. Single PDF file  — employee uploads one petition PDF
2. Folder           — employee uploads a folder with petition + annexures

The resolver identifies the main petition PDF and any supporting annexures,
returning a structured dict with paths categorized by role.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("kserc.petition_resolver")


def resolve_petition_input(input_path: str) -> Dict:
    """
    Resolve a petition input that can be either a single PDF or a folder.
    
    Args:
        input_path: Path to a PDF file or a folder containing PDFs.
    
    Returns:
        Dict with keys:
            - 'main_petition': str — path to the main petition PDF
            - 'annexures': List[str] — paths to supporting annexure PDFs
            - 'all_pdfs': List[str] — all PDF paths in order
            - 'input_type': 'file' | 'folder'
    """
    path = Path(input_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")
    
    # ── Single PDF ──────────────────────────────────────────────────
    if path.is_file() and path.suffix.lower() == ".pdf":
        logger.info(f"Single PDF input: {path.name}")
        return {
            "main_petition": str(path),
            "annexures": [],
            "all_pdfs": [str(path)],
            "input_type": "file",
        }
    
    # ── Folder ──────────────────────────────────────────────────────
    if path.is_dir():
        pdf_files = sorted(path.glob("*.pdf"), key=lambda p: p.name.lower())
        
        if not pdf_files:
            raise ValueError(f"No PDF files found in folder: {input_path}")
        
        logger.info(f"Folder input: {path.name} ({len(pdf_files)} PDFs)")
        
        # Identify the main petition vs annexures
        main_petition = None
        annexures = []
        
        for pdf in pdf_files:
            name_lower = pdf.name.lower()
            
            # Main petition detection — keywords that indicate the main filing
            if _is_main_petition(name_lower):
                main_petition = str(pdf)
                logger.info(f"  → Main petition: {pdf.name}")
            else:
                annexures.append(str(pdf))
                logger.info(f"  → Annexure: {pdf.name}")
        
        # If no main petition identified, use the largest PDF
        if not main_petition:
            largest = max(pdf_files, key=lambda p: p.stat().st_size)
            main_petition = str(largest)
            annexures = [str(p) for p in pdf_files if str(p) != main_petition]
            logger.info(f"  → Main petition (by size): {largest.name}")
        
        return {
            "main_petition": main_petition,
            "annexures": annexures,
            "all_pdfs": [main_petition] + annexures,
            "input_type": "folder",
        }
    
    raise ValueError(
        f"Input must be a PDF file or a folder containing PDFs: {input_path}"
    )


def _is_main_petition(filename_lower: str) -> bool:
    """Detect if a filename is likely the main petition document."""
    # Common petition filename patterns
    petition_patterns = [
        r"petition",          # "1_Petition.pdf", "Petition Filing.pdf"
        r"^1[_\-\s]",         # "1_Petition.pdf", "1-Main.pdf"
        r"truing.?up",        # "Truing Up Petition.pdf"
        r"true.?up",          # "True Up Filing.pdf"
        r"main",              # "Main Petition.pdf"
        r"application",       # "Application.pdf"
        r"op\s*\d+",          # "OP 84 2023.pdf"
    ]
    
    # Annexure patterns — if it matches these, it's NOT the main petition
    annexure_patterns = [
        r"annex",             # "Annex A.pdf", "Annexure B.pdf"
        r"appendix",          # "Appendix 1.pdf"
        r"schedule",          # "Schedule of Rates.pdf"
        r"audit",             # "Audit Report.pdf"
        r"accounts",          # "Electricity Accounts.pdf"
        r"certificate",       # "CA Certificate.pdf"
        r"supporting",        # "Supporting Documents.pdf"
    ]
    
    # If it matches an annexure pattern, it's not the main petition
    for pattern in annexure_patterns:
        if re.search(pattern, filename_lower):
            return False
    
    # If it matches a petition pattern, it's the main petition
    for pattern in petition_patterns:
        if re.search(pattern, filename_lower):
            return True
    
    return False


def merge_extracted_data(
    main_data: Dict,
    annexure_data: List[Dict],
) -> Dict:
    """
    Merge extracted data from the main petition with annexure data.
    
    Annexures typically contain detailed financial tables that might
    have more accurate numbers than the main petition narrative.
    
    Strategy:
    - If annexure has non-zero values for a component where main has 0, use annexure
    - If both have non-zero values, prefer the main petition (it's the official claim)
    - Merge any additional components found only in annexures
    """
    if not annexure_data:
        return main_data
    
    merged = dict(main_data)
    
    for annex in annexure_data:
        # Merge expenses
        if "expenses" in annex:
            main_expenses = merged.get("expenses", {})
            for key, value in annex["expenses"].items():
                if key not in main_expenses or main_expenses.get(key, 0) == 0:
                    main_expenses[key] = value
                    logger.info(f"  Merged from annexure: {key} = {value}")
            merged["expenses"] = main_expenses
        
        # Merge revenues
        if "revenues" in annex:
            main_revenues = merged.get("revenues", {})
            for key, value in annex["revenues"].items():
                if key not in main_revenues or main_revenues.get(key, 0) == 0:
                    main_revenues[key] = value
            merged["revenues"] = main_revenues
        
        # Merge text (concatenate)
        if "petition_text" in annex and annex["petition_text"]:
            existing_text = merged.get("petition_text", "")
            merged["petition_text"] = existing_text + "\n\n--- ANNEXURE ---\n\n" + annex["petition_text"]
    
    return merged
