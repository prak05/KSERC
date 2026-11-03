"""
Object storage for reference documents and uploads.

local  files live in ``DOCUMENTS_DIR``; nothing to sync.
aws    the regulatory corpus lives in S3 (``DOCS_BUCKET``/``DOCS_PREFIX``) and is mirrored
       into ``DOCUMENTS_DIR`` on start-up so the PDF tools can read it from disk.
"""

import logging
from pathlib import Path

from src.cloud import settings

logger = logging.getLogger("kserc.blobstore")


def _s3():
    import boto3

    return boto3.client("s3", region_name=settings.AWS_REGION)


def sync_documents(force: bool = False) -> bool:
    """Mirror the S3 document corpus to ``DOCUMENTS_DIR``. Returns True if a sync ran."""
    if not settings.IS_AWS or not settings.DOCS_BUCKET:
        return False

    dest = settings.DOCUMENTS_DIR
    dest.mkdir(parents=True, exist_ok=True)
    downloaded = skipped = 0
    paginator = _s3().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.DOCS_BUCKET, Prefix=settings.DOCS_PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            local = dest / key[len(settings.DOCS_PREFIX):]
            local.parent.mkdir(parents=True, exist_ok=True)
            if not force and local.exists() and local.stat().st_size == obj["Size"]:
                skipped += 1
                continue
            _s3().download_file(settings.DOCS_BUCKET, key, str(local))
            downloaded += 1
    logger.info(f"S3 sync: {downloaded} downloaded, {skipped} already current → {dest}")
    return True


def upload_file(path: Path, key: str) -> str:
    """Upload a local file to the documents bucket and return its key."""
    _s3().upload_file(str(path), settings.DOCS_BUCKET, key)
    return key
