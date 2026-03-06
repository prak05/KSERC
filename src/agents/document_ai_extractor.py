"""
Document AI Form Parser — precise table extraction from petition PDFs.

Uses Google Cloud Document AI Form Parser processor to extract
structured tables from KSERC petition PDFs. This provides much higher
accuracy than PyMuPDF for complex table layouts.

Authentication: Uses gcloud ADC (application-default credentials).
Run `gcloud auth application-default login --project=kserc-489315` first.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
from dotenv import load_dotenv

logger = logging.getLogger("kserc.document_ai")
load_dotenv()

# ═══════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "kserc-489315")
PROCESSOR_ID = os.getenv("DOCUMENT_AI_PROCESSOR_ID", "5eecf35a1ed2be8e")
PROCESSOR_LOCATION = os.getenv("DOCUMENT_AI_LOCATION", "us")


def _get_processor_name() -> str:
    """Build the full processor resource name."""
    return f"projects/{GCP_PROJECT_ID}/locations/{PROCESSOR_LOCATION}/processors/{PROCESSOR_ID}"


# ═══════════════════════════════════════════════════════════════════════
# Document AI Processing
# ═══════════════════════════════════════════════════════════════════════

def process_document(pdf_path: str, max_pages: int = 15) -> dict:
    """
    Process a PDF with Document AI Form Parser.
    
    Args:
        pdf_path: Path to the PDF file.
        max_pages: Max pages to process (Document AI has limits).
    
    Returns:
        Dict with 'text', 'tables', 'pages' from Document AI.
    """
    from google.cloud import documentai_v1 as documentai
    from google.api_core.client_options import ClientOptions
    
    # Read PDF
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    file_content = pdf_path.read_bytes()
    file_size_mb = len(file_content) / (1024 * 1024)
    logger.info(f"Processing PDF: {pdf_path.name} ({file_size_mb:.1f} MB)")
    
    # Document AI has a 20MB limit for online processing
    if file_size_mb > 20:
        logger.warning(f"PDF is {file_size_mb:.1f} MB — exceeds 20MB online limit. "
                        "Using first pages only.")
        # For large files, we'll process only a subset via PyMuPDF extraction
        return _process_large_document(str(pdf_path), max_pages)
    
    # Configure client
    opts = ClientOptions(
        api_endpoint=f"{PROCESSOR_LOCATION}-documentai.googleapis.com"
    )
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    
    # Build request
    raw_document = documentai.RawDocument(
        content=file_content,
        mime_type="application/pdf",
    )
    
    request = documentai.ProcessRequest(
        name=_get_processor_name(),
        raw_document=raw_document,
    )
    
    # Process
    logger.info(f"Sending to Document AI Form Parser (processor: {PROCESSOR_ID})...")
    result = client.process_document(request=request)
    document = result.document
    
    logger.info(f"Document AI returned: {len(document.text)} chars text, "
                f"{len(document.pages)} pages")
    
    # Extract tables
    tables = _extract_tables_from_document(document)
    logger.info(f"Extracted {len(tables)} tables from Document AI")
    
    return {
        "text": document.text,
        "tables": tables,
        "pages": len(document.pages),
        "document": document,  # Raw document object for advanced use
    }


def _process_large_document(pdf_path: str, max_pages: int) -> dict:
    """
    Handle PDFs larger than 20MB by splitting into chunks.
    Uses PyMuPDF to extract individual pages, then processes each.
    """
    import fitz
    from google.cloud import documentai_v1 as documentai
    from google.api_core.client_options import ClientOptions
    
    doc = fitz.open(pdf_path)
    total_pages = min(len(doc), max_pages)
    all_tables = []
    all_text = []
    
    logger.info(f"Large PDF mode: processing {total_pages} pages individually")
    
    opts = ClientOptions(
        api_endpoint=f"{PROCESSOR_LOCATION}-documentai.googleapis.com"
    )
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    
    # Process in batches of 5 pages
    batch_size = 5
    for start in range(0, total_pages, batch_size):
        end = min(start + batch_size, total_pages)
        
        # Create a sub-PDF with just these pages
        sub_doc = fitz.open()
        for i in range(start, end):
            sub_doc.insert_pdf(doc, from_page=i, to_page=i)
        
        sub_bytes = sub_doc.tobytes()
        sub_doc.close()
        
        if len(sub_bytes) > 20 * 1024 * 1024:
            logger.warning(f"Batch pages {start+1}-{end} still > 20MB, skipping")
            continue
        
        try:
            raw_document = documentai.RawDocument(
                content=sub_bytes,
                mime_type="application/pdf",
            )
            request = documentai.ProcessRequest(
                name=_get_processor_name(),
                raw_document=raw_document,
            )
            result = client.process_document(request=request)
            
            all_text.append(result.document.text)
            tables = _extract_tables_from_document(result.document)
            all_tables.extend(tables)
            
            logger.info(f"  Pages {start+1}-{end}: {len(tables)} tables, "
                        f"{len(result.document.text)} chars")
        except Exception as e:
            logger.error(f"  Pages {start+1}-{end} failed: {e}")
    
    doc.close()
    
    return {
        "text": "\n\n".join(all_text),
        "tables": all_tables,
        "pages": total_pages,
        "document": None,
    }


# ═══════════════════════════════════════════════════════════════════════
# Table Extraction from Document AI Response
# ═══════════════════════════════════════════════════════════════════════

def _get_text_from_layout(layout, document_text: str) -> str:
    """Extract text from a Document AI layout element using text anchors."""
    if not layout.text_anchor or not layout.text_anchor.text_segments:
        return ""
    
    text_parts = []
    for segment in layout.text_anchor.text_segments:
        start = int(segment.start_index) if segment.start_index else 0
        end = int(segment.end_index) if segment.end_index else 0
        text_parts.append(document_text[start:end])
    
    return "".join(text_parts).strip()


def _extract_tables_from_document(document) -> List[pd.DataFrame]:
    """
    Extract all tables from a Document AI document object as DataFrames.
    """
    tables = []
    
    for page in document.pages:
        for table in page.tables:
            # Extract header rows
            header_cells = []
            for header_row in table.header_rows:
                row_cells = []
                for cell in header_row.cells:
                    cell_text = _get_text_from_layout(cell.layout, document.text)
                    row_cells.append(cell_text)
                header_cells.append(row_cells)
            
            # Extract body rows
            body_rows = []
            for body_row in table.body_rows:
                row_cells = []
                for cell in body_row.cells:
                    cell_text = _get_text_from_layout(cell.layout, document.text)
                    row_cells.append(cell_text)
                body_rows.append(row_cells)
            
            if not body_rows:
                continue
            
            # Build DataFrame
            try:
                if header_cells:
                    # Use last header row as column names (handles multi-row headers)
                    columns = header_cells[-1]
                    # Pad columns if needed
                    max_cols = max(len(columns), max(len(r) for r in body_rows))
                    columns = columns + [f"Col_{i}" for i in range(len(columns), max_cols)]
                    
                    # Pad rows if needed
                    padded_rows = []
                    for row in body_rows:
                        padded = row + [""] * (max_cols - len(row))
                        padded_rows.append(padded[:max_cols])
                    
                    df = pd.DataFrame(padded_rows, columns=columns[:max_cols])
                else:
                    df = pd.DataFrame(body_rows)
                
                if len(df) >= 2 and len(df.columns) >= 2:
                    tables.append(df)
                    logger.info(f"  [DocAI] Table: {df.shape[0]} rows × {df.shape[1]} cols")
                    
            except Exception as e:
                logger.warning(f"  [DocAI] Failed to build DataFrame: {e}")
    
    return tables


# ═══════════════════════════════════════════════════════════════════════
# High-Level Extraction for KSERC Petitions
# ═══════════════════════════════════════════════════════════════════════

def extract_petition_tables(
    pdf_path: str,
    licensee_name: str = "",
    financial_year: str = "",
) -> Tuple[str, List[pd.DataFrame]]:
    """
    Extract tables and text from a KSERC petition PDF using Document AI.
    
    This is the primary entry point for the extractor module.
    Falls back to PyMuPDF if Document AI fails.
    
    Returns:
        (full_text, list_of_dataframes)
    """
    try:
        result = process_document(pdf_path)
        
        full_text = result.get("text", "")
        tables = result.get("tables", [])
        
        if tables:
            logger.info(f"Document AI extracted {len(tables)} tables from {Path(pdf_path).name}")
            return full_text, tables
        else:
            logger.warning("Document AI returned no tables, falling back to PyMuPDF")
            
    except Exception as e:
        logger.error(f"Document AI extraction failed: {e}")
        logger.info("Falling back to PyMuPDF extraction")
    
    # Fallback to PyMuPDF
    return _fallback_pymupdf(pdf_path)


def _fallback_pymupdf(pdf_path: str) -> Tuple[str, List[pd.DataFrame]]:
    """PyMuPDF fallback for when Document AI is unavailable."""
    import fitz
    
    doc = fitz.open(pdf_path)
    pages_text = []
    tables = []
    
    for page in doc:
        pages_text.append(page.get_text("text"))
        try:
            page_tabs = page.find_tables()
            for tab in page_tabs.tables:
                if tab.row_count < 2 or tab.col_count < 2:
                    continue
                rows = tab.extract()
                if len(rows) >= 2:
                    header = [str(h) if h else "" for h in rows[0]]
                    data = [[str(c) if c else "" for c in row] for row in rows[1:]]
                    try:
                        df = pd.DataFrame(data, columns=header[:len(data[0])])
                        tables.append(df)
                    except Exception:
                        tables.append(pd.DataFrame(data))
        except AttributeError:
            pass
    
    doc.close()
    full_text = "\n".join(pages_text)
    logger.info(f"PyMuPDF fallback: {len(full_text)} chars, {len(tables)} tables")
    return full_text, tables
