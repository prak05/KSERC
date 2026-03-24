import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any


logger = logging.getLogger("kserc.myt_loader")


class MYTLoader:
    """
    Load MYT baseline norms for a licensee and financial year.

    Priority order:
      1. Firestore myt_norms/{licensee}/years/{fy} — set by staff or auto-extracted
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
            logger.warning(f"MYT baselines file not found at {self.data_path}")

    def load_myt_baselines(self, licensee_name: str, financial_year: str) -> Dict[str, float]:
        """
        Load MYT baseline norms.
        Firestore wins over JSON. Returns {} if nothing found.
        """
        # ── 1. Check Firestore first ───────────────────────────────────
        try:
            from src.tools.db import get_myt_norms_override
            db_norms = get_myt_norms_override(licensee_name, financial_year)
            if db_norms:
                logger.info(f"MYT norms loaded from Firestore for {licensee_name} FY {financial_year}")
                return db_norms
        except Exception as e:
            logger.warning(f"MYTLoader: Firestore lookup failed, falling back to JSON — {e}")

        # ── 2. Fall back to JSON ───────────────────────────────────────
        licensee_data = self.baselines.get(licensee_name, {})
        baselines = licensee_data.get("baselines", {})
        norms = baselines.get(financial_year, {})
        if norms:
            logger.info(f"MYT norms loaded from JSON for {licensee_name} FY {financial_year}")
        return norms

    def load_myt_base_year_norms(
        self, licensee_name: str, base_year: str = "base_year_2021-22"
    ) -> Dict[str, float]:
        """Load base year norms — used for O&M escalation."""
        # Try Firestore first
        try:
            from src.tools.db import get_myt_norms_override
            db_norms = get_myt_norms_override(licensee_name, base_year)
            if db_norms:
                return db_norms
        except Exception:
            pass

        # JSON fallback
        licensee_data = self.baselines.get(licensee_name, {})
        baselines = licensee_data.get("baselines", {})
        return baselines.get(base_year, {})

    def load_full_licensee_data(self, licensee_name: str) -> Dict[str, Any]:
        """Return all years' norms for a licensee. Merges Firestore + JSON."""
        # Start with JSON data
        result = dict(self.baselines.get(licensee_name, {}))

        # Overlay Firestore data (higher priority)
        try:
            from src.tools.db import get_all_myt_norms
            fs_norms = get_all_myt_norms(licensee_name)
            if fs_norms:
                if "baselines" not in result:
                    result["baselines"] = {}
                result["baselines"].update(fs_norms)
        except Exception as e:
            logger.warning(f"MYTLoader: Firestore full load failed — {e}")

        return result
