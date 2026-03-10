import json
from pathlib import Path
from typing import Dict, Optional, Any


class MYTLoader:
    """
    Load MYT baseline norms for a licensee and financial year.

    Priority order:
      1. DB override table (myt_norms_override) — set by staff via Reference Data UI
      2. JSON file fallback (data/myt_baselines/myt_baselines.json)

    This means staff can update norms in the UI without touching any files.
    """

    def __init__(self, data_path: Optional[str] = None):
        if data_path:
            self.data_path = Path(data_path)
        else:
            self.data_path = (
                Path(__file__).resolve().parents[2]
                / "data" / "myt_baselines" / "myt_baselines.json"
            )

        self.baselines: Dict[str, Any] = {}
        self._load_json_data()

    def _load_json_data(self) -> None:
        if self.data_path.exists():
            with open(self.data_path, "r", encoding="utf-8") as f:
                self.baselines = json.load(f)
        else:
            print(f"Warning: MYT baselines file not found at {self.data_path}")

    def load_myt_baselines(self, licensee_name: str, financial_year: str) -> Dict[str, float]:
        """
        Load MYT baseline norms.
        DB override wins over JSON. Returns {} if nothing found.
        """
        # ── 1. Check DB override first ─────────────────────────────────
        try:
            from src.tools.db import get_myt_norms_override
            db_norms = get_myt_norms_override(licensee_name, financial_year)
            if db_norms:
                return db_norms
        except Exception as e:
            print(f"MYTLoader: DB lookup failed, falling back to JSON — {e}")

        # ── 2. Fall back to JSON ───────────────────────────────────────
        licensee_data = self.baselines.get(licensee_name, {})
        baselines = licensee_data.get("baselines", {})
        return baselines.get(financial_year, {})

    def load_myt_base_year_norms(
        self, licensee_name: str, base_year: str = "base_year_2021-22"
    ) -> Dict[str, float]:
        """Load base year norms — used for O&M escalation. JSON only."""
        licensee_data = self.baselines.get(licensee_name, {})
        baselines = licensee_data.get("baselines", {})
        return baselines.get(base_year, {})

    def load_full_licensee_data(self, licensee_name: str) -> Dict[str, Any]:
        """Return all years' norms for a licensee from the JSON file."""
        return self.baselines.get(licensee_name, {})
