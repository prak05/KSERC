"""
Seed Firestore with existing JSON data files.

Run this ONCE to populate Firestore from:
  - data/myt_baselines/myt_baselines.json → myt_norms collection
  - data/precedent_db/precedent_db.json → precedent_db collection
  - data/annexure1_rates.json → economic_indicators collection (if applicable)
"""

import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from src.tools.db import save_myt_norms, save_precedent, upsert_economic_indicators, init_db
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("seed_firestore")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def seed_myt_norms():
    """Seed MYT baselines from JSON to Firestore."""
    path = DATA_DIR / "myt_baselines" / "myt_baselines.json"
    if not path.exists():
        logger.warning(f"MYT baselines file not found: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for licensee, licensee_data in data.items():
        baselines = licensee_data.get("baselines", {})
        for fy, norms in baselines.items():
            if isinstance(norms, dict) and norms:
                save_myt_norms(licensee, fy, norms, source="json_seed")
                count += 1
                logger.info(f"  ✓ {licensee} / {fy}: {len(norms)} fields")

    logger.info(f"Seeded {count} MYT norm entries to Firestore")


def seed_precedent_db():
    """Seed precedent DB from JSON to Firestore."""
    path = DATA_DIR / "precedent_db" / "precedent_db.json"
    if not path.exists():
        logger.warning(f"Precedent DB file not found: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for licensee, fy_data in data.items():
        if isinstance(fy_data, dict):
            for fy, precedent in fy_data.items():
                if isinstance(precedent, dict):
                    save_precedent(licensee, fy, precedent)
                    count += 1
                    logger.info(f"  ✓ {licensee} / {fy}")

    logger.info(f"Seeded {count} precedent entries to Firestore")


def seed_economic_indicators():
    """Seed economic indicators if the data exists in a JSON file."""
    # Check for a separate JSON file, or extract from myt_baselines
    eco_path = DATA_DIR / "economic_indicators.json"
    if eco_path.exists():
        with open(eco_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for fy, indicators in data.items():
            upsert_economic_indicators(fy, indicators)
            logger.info(f"  ✓ Economic indicators: {fy}")
    else:
        logger.info("No economic_indicators.json found — skipping")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Seeding Firestore from JSON files")
    logger.info("=" * 60)

    init_db()

    logger.info("\n1. Seeding MYT Norms...")
    seed_myt_norms()

    logger.info("\n2. Seeding Precedent DB...")
    seed_precedent_db()

    logger.info("\n3. Seeding Economic Indicators...")
    seed_economic_indicators()

    logger.info("\n" + "=" * 60)
    logger.info("Seeding complete!")
    logger.info("=" * 60)
