"""
Seed a test analysis into the DB for development and CI testing.

Usage:
    python scripts/seed_test_analysis.py [--file results_infopark_2024_25.json]

This bypasses the full PDF extraction pipeline and directly inserts
a completed analysis result into the SQLite DB.
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.tools.db import init_db, save_analysis


def seed(results_file: str = None):
    """Seed a test analysis from a results JSON file."""
    init_db()

    if results_file is None:
        # Default to Infopark 2024-25
        results_file = str(project_root / "results_infopark_2024_25.json")

    results_path = Path(results_file)
    if not results_path.exists():
        print(f"ERROR: File not found: {results_path}")
        sys.exit(1)

    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    aid = data.get("analysis_id", "test-seed-001")

    # Ensure required fields
    data.setdefault("pdf_available", False)
    data.setdefault("output_pdf_path", "")

    save_analysis(aid, "COMPLETED", data)
    print(f"✅ Seeded analysis: {aid}")
    print(f"   Licensee: {data.get('licensee_name', '?')}")
    print(f"   FY: {data.get('financial_year', '?')}")
    print(f"   Source: {results_path.name}")
    print(f"\n   Use this analysis_id to test: {aid}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed test analysis into DB")
    parser.add_argument("--file", type=str, default=None, help="Path to results JSON file")
    args = parser.parse_args()
    seed(args.file)
