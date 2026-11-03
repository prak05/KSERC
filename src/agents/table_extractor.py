"""
Petition table extraction.

aws    Amazon Textract document analysis (TABLES). Multi-page PDFs go through the
       asynchronous job API, which reads the file from the documents bucket.
local  PyMuPDF's table finder.

Both paths return ``(full_text, list_of_dataframes)``.
"""

import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from src.cloud import settings

logger = logging.getLogger("kserc.tables")

_POLL_SECONDS = 3
_TIMEOUT_SECONDS = 600


def extract_petition_tables(pdf_path: str, licensee_name: str = "", financial_year: str = "") -> Tuple[str, List[pd.DataFrame]]:
    if settings.IS_AWS and settings.DOCS_BUCKET:
        try:
            text, tables = _textract(pdf_path)
            if tables:
                logger.info(f"Textract extracted {len(tables)} tables from {Path(pdf_path).name}")
                return text, tables
            logger.warning("Textract returned no tables, falling back to PyMuPDF")
        except Exception as e:
            logger.error(f"Textract extraction failed: {e}; falling back to PyMuPDF")
    return _pymupdf(pdf_path)


# ═══════════════════════════════════════════════════════════════════════
# Textract
# ═══════════════════════════════════════════════════════════════════════

def _textract(pdf_path: str) -> Tuple[str, List[pd.DataFrame]]:
    import boto3

    from src.cloud.blobstore import upload_file

    key = upload_file(Path(pdf_path), f"textract-input/{uuid.uuid4()}.pdf")
    tx = boto3.client("textract", region_name=settings.AWS_REGION)
    job = tx.start_document_analysis(
        DocumentLocation={"S3Object": {"Bucket": settings.DOCS_BUCKET, "Name": key}},
        FeatureTypes=["TABLES"],
    )["JobId"]

    deadline = time.time() + _TIMEOUT_SECONDS
    while True:
        resp = tx.get_document_analysis(JobId=job)
        status = resp["JobStatus"]
        if status == "SUCCEEDED":
            break
        if status == "FAILED" or time.time() > deadline:
            raise RuntimeError(f"Textract job {job} ended with status {status}")
        time.sleep(_POLL_SECONDS)

    blocks = list(resp["Blocks"])
    while resp.get("NextToken"):
        resp = tx.get_document_analysis(JobId=job, NextToken=resp["NextToken"])
        blocks.extend(resp["Blocks"])
    return _blocks_to_text(blocks), _blocks_to_tables(blocks)


def _children(block: Dict, by_id: Dict[str, Dict]) -> List[Dict]:
    ids = [i for rel in block.get("Relationships", []) if rel["Type"] == "CHILD" for i in rel["Ids"]]
    return [by_id[i] for i in ids if i in by_id]


def _blocks_to_text(blocks: List[Dict]) -> str:
    pages: Dict[int, List[str]] = {}
    for b in blocks:
        if b["BlockType"] == "LINE":
            pages.setdefault(b.get("Page", 1), []).append(b.get("Text", ""))
    return "\n".join(f"\n--- Page {p} ---\n" + "\n".join(lines) for p, lines in sorted(pages.items()))


def _blocks_to_tables(blocks: List[Dict]) -> List[pd.DataFrame]:
    by_id = {b["Id"]: b for b in blocks}
    tables = []
    for table in (b for b in blocks if b["BlockType"] == "TABLE"):
        cells = [c for c in _children(table, by_id) if c["BlockType"] == "CELL"]
        if not cells:
            continue
        n_rows = max(c["RowIndex"] for c in cells)
        n_cols = max(c["ColumnIndex"] for c in cells)
        grid = [[""] * n_cols for _ in range(n_rows)]
        header_rows = set()
        for c in cells:
            words = [w.get("Text", "") for w in _children(c, by_id) if w["BlockType"] in ("WORD", "SELECTION_ELEMENT")]
            grid[c["RowIndex"] - 1][c["ColumnIndex"] - 1] = " ".join(words).strip()
            if "COLUMN_HEADER" in c.get("EntityTypes", []):
                header_rows.add(c["RowIndex"] - 1)
        if header_rows:
            last = max(header_rows)
            columns = [h or f"Col_{i}" for i, h in enumerate(grid[last])]
            body = grid[last + 1:]
        else:
            columns, body = None, grid
        if len(body) >= 2 and n_cols >= 2:
            tables.append(pd.DataFrame(body, columns=columns))
    return tables


# ═══════════════════════════════════════════════════════════════════════
# PyMuPDF (local)
# ═══════════════════════════════════════════════════════════════════════

def _pymupdf(pdf_path: str) -> Tuple[str, List[pd.DataFrame]]:
    import fitz

    pages_text, tables = [], []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            pages_text.append(page.get_text("text"))
            for tab in page.find_tables().tables:
                if tab.row_count < 2 or tab.col_count < 2:
                    continue
                rows = tab.extract()
                header = [str(h) if h else "" for h in rows[0]]
                data = [[str(c) if c else "" for c in row] for row in rows[1:]]
                try:
                    tables.append(pd.DataFrame(data, columns=header[: len(data[0])]))
                except Exception:
                    tables.append(pd.DataFrame(data))
    full_text = "\n".join(pages_text)
    logger.info(f"PyMuPDF: {len(full_text)} chars, {len(tables)} tables")
    return full_text, tables
