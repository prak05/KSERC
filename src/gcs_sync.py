"""
GCS Document Sync — downloads reference documents from Google Cloud Storage
at startup so Cloud Run has local access to all regulatory PDFs.

This runs once when the app starts on Cloud Run. On local dev, the Documents
folder is already available, so this is a no-op.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger("kserc.gcs_sync")

# Where to store downloaded documents on Cloud Run
BASE_DIR = Path(__file__).resolve().parents[1]
LOCAL_DOCS_DIR = Path(os.getenv("DOCUMENTS_DIR", str(BASE_DIR / ".." / "Documents"))).resolve()

# GCS bucket name
GCS_BUCKET = os.getenv("GCS_BUCKET", "kserc-regulatory-docs-v2")


def sync_documents_from_gcs(force: bool = False) -> bool:
    """
    Download all documents from GCS bucket to local DOCUMENTS_DIR.
    
    Skips download if:
    - DOCUMENTS_DIR already exists and has files (local dev)
    - GCS_BUCKET is not set
    
    Args:
        force: If True, download even if local docs exist.
    
    Returns:
        True if sync was performed, False if skipped.
    """
    # Skip if local docs already exist (local dev environment)
    if not force and LOCAL_DOCS_DIR.exists() and any(LOCAL_DOCS_DIR.glob("*.pdf")):
        pdf_count = len(list(LOCAL_DOCS_DIR.glob("*.pdf")))
        logger.info(f"Local documents found ({pdf_count} PDFs in {LOCAL_DOCS_DIR}) — skipping GCS sync")
        return False
    
    if not GCS_BUCKET:
        logger.warning("GCS_BUCKET not set — cannot sync documents")
        return False
    
    try:
        from google.cloud import storage
    except ImportError:
        logger.warning("google-cloud-storage not installed — cannot sync documents")
        return False
    
    try:
        logger.info(f"Syncing documents from gs://{GCS_BUCKET}/ → {LOCAL_DOCS_DIR}")
        LOCAL_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        blobs = list(bucket.list_blobs())
        
        downloaded = 0
        skipped = 0
        
        for blob in blobs:
            if blob.name.endswith("/"):
                continue  # skip directory markers
            
            local_path = LOCAL_DOCS_DIR / blob.name
            
            # Create subdirectories if needed (e.g., petitions/)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Skip if already downloaded and same size
            if not force and local_path.exists() and local_path.stat().st_size == blob.size:
                skipped += 1
                continue
            
            blob.download_to_filename(str(local_path))
            downloaded += 1
            size_kb = blob.size / 1024 if blob.size else 0
            logger.info(f"  ⬇ {blob.name} ({size_kb:.0f} KB)")
        
        logger.info(f"GCS sync complete: {downloaded} downloaded, {skipped} skipped (already up to date)")
        return True
        
    except Exception as e:
        logger.error(f"GCS document sync failed: {e}", exc_info=True)
        return False
