import json
import os
from pathlib import Path
from typing import Dict, Optional, Any

class MYTLoader:
    def __init__(self, data_path: Optional[str] = None):
        if data_path:
            self.data_path = Path(data_path)
        else:
            # Default to data/myt_baselines/myt_baselines.json relative to project root
            self.data_path = Path(__file__).resolve().parents[2] / "data" / "myt_baselines" / "myt_baselines.json"
        
        self.baselines: Dict[str, Any] = {}
        self._load_data()

    def _load_data(self) -> None:
        if self.data_path.exists():
            with open(self.data_path, "r", encoding="utf-8") as f:
                self.baselines = json.load(f)
        else:
            print(f"Warning: MYT baselines file not found at {self.data_path}")

    def load_myt_baselines(self, licensee_name: str, financial_year: str) -> Dict[str, float]:
        """
        Loads the MYT baseline norms for a specific licensee and financial year.
        If not found, returns an empty dictionary.
        """
        licensee_data = self.baselines.get(licensee_name, {})
        baselines = licensee_data.get("baselines", {})
        
        return baselines.get(financial_year, {})

    def load_myt_base_year_norms(self, licensee_name: str, base_year: str = "base_year_2021-22") -> Dict[str, float]:
         """Loads the base year norms for a licensee, primarily used for O&M escalation."""
         licensee_data = self.baselines.get(licensee_name, {})
         baselines = licensee_data.get("baselines", {})
         return baselines.get(base_year, {})
