# [Purpose] Generate verdict PDF for KSERC Saarthi
# [Source] User defined
# [Why] Provide official-style output to client

# [Library] uuid - Unique IDs for verdict files
# [Why] Avoid collisions
import uuid

# [Library] pathlib - Path handling
# [Why] Safe filesystem operations
from pathlib import Path

# [Library] typing - Type hints
# [Why] Clarity
from typing import Dict, Any

# [Library] fpdf - Lightweight PDF generation
# [Why] Simple PDF creation without heavy deps
from fpdf import FPDF

# [Library] google-cloud-storage - Upload to GCS
# [Why] Persist verdict PDFs across container restarts
from google.cloud import storage

# [User Defined] Import settings
# [Source] src/config.py
# [Why] Access bucket config
from src.config import settings

# [User Defined] Import logger
# [Source] src/utils/logger.py
# [Why] Trace PDF generation
from src.utils.logger import get_logger

logger = get_logger(__name__)


def build_verdict_pdf(output_dir: Path, payload: Dict[str, Any]) -> Path:
    """
    [Purpose] Build a verdict PDF file
    [Why] Client receives final KSERC-style verdict
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    verdict_id = str(uuid.uuid4())
    file_path = output_dir / f"{verdict_id}.pdf"

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "KSERC Saarthi - Regulatory Verdict", ln=True)

    pdf.set_font("Helvetica", "", 11)
    pdf.ln(2)
    pdf.multi_cell(0, 6, payload.get("summary", "No summary available."))

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Approved Items", ln=True)
    pdf.set_font("Helvetica", "", 11)
    approved = payload.get("approved_items", [])
    if not approved:
        pdf.multi_cell(0, 6, "- None listed")
    else:
        for item in approved:
            pdf.multi_cell(0, 6, f"- {item}")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Disallowed Items", ln=True)
    pdf.set_font("Helvetica", "", 11)
    disallowed = payload.get("disallowed_items", [])
    if not disallowed:
        pdf.multi_cell(0, 6, "- None listed")
    else:
        for item in disallowed:
            pdf.multi_cell(0, 6, f"- {item}")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Conditions / Notes", ln=True)
    pdf.set_font("Helvetica", "", 11)
    conditions = payload.get("conditions", [])
    if not conditions:
        pdf.multi_cell(0, 6, "- None")
    else:
        for item in conditions:
            pdf.multi_cell(0, 6, f"- {item}")

    pdf.output(str(file_path))
    logger.info(f"Verdict PDF saved to {file_path}")
    return file_path


def upload_verdict_to_gcs(file_path: Path) -> str:
    """
    [Purpose] Upload verdict PDF to Google Cloud Storage
    [Why] Provide persistent public access
    """
    if not settings.GCS_BUCKET_NAME:
        raise RuntimeError("GCS_BUCKET_NAME is not set")

    client = storage.Client()
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(file_path.name)
    blob.upload_from_filename(str(file_path), content_type="application/pdf")

    # Try to make object public (works when bucket allows public access)
    try:
        blob.make_public()
    except Exception as e:
        logger.warning(f"Failed to make blob public: {e}")

    if settings.GCS_PUBLIC_BASE_URL:
        return f"{settings.GCS_PUBLIC_BASE_URL.rstrip('/')}/{file_path.name}"

    return f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/{file_path.name}"
