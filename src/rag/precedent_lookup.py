"""
Precedent Lookup Service — queries the precedent database
to find past KSERC decisions for a given licensee + component.
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger("precedent_lookup")

DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "precedent_db", "precedent_db.json"
)


class PrecedentLookup:
    """Provides structured lookups into the KSERC precedent database."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = os.path.abspath(db_path)
        self.db: Dict[str, Dict[str, dict]] = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.db_path):
            logger.warning(f"Precedent DB not found at {self.db_path}")
            return
        with open(self.db_path, "r", encoding="utf-8") as f:
            self.db = json.load(f)
        logger.info(
            f"Loaded precedent DB: {len(self.db)} licensees, "
            f"{sum(len(v) for v in self.db.values())} total orders"
        )

    @property
    def available(self) -> bool:
        return bool(self.db)

    def get_licensee_history(self, licensee: str) -> Dict[str, dict]:
        """Get all past orders for a licensee."""
        # Try exact match first, then case-insensitive
        if licensee in self.db:
            return self.db[licensee]
        for key in self.db:
            if key.lower() == licensee.lower():
                return self.db[key]
        return {}

    def get_component_history(
        self, licensee: str, component: str
    ) -> List[Dict[str, Any]]:
        """
        Get the historical claimed vs approved amounts for a specific component
        across all past years.

        Returns a list of dicts sorted by FY:
        [
            {
                "fy": "2020-21",
                "order_ref": "CSEZA TU 2020-21",
                "claimed": 25.42,
                "approved": 23.67,
                "cut_pct": 6.89,
                "kserc_reasoning": "..."
            }
        ]
        """
        history = self.get_licensee_history(licensee)
        if not history:
            return []

        records = []
        for fy, order_data in sorted(history.items()):
            claimed_exp = order_data.get("claimed_expenses", {})
            approved_exp = order_data.get("approved_expenses", {})
            meta = order_data.get("_meta", {})

            claimed = claimed_exp.get(component, 0.0)
            approved = approved_exp.get(component, 0.0)
            cut_pct = round((1 - approved / claimed) * 100, 2) if claimed > 0 else 0.0

            # Find KSERC reasoning for this component
            kserc_reasoning = ""
            for d in order_data.get("key_disallowances", []):
                if d.get("component") == component:
                    kserc_reasoning = d.get("kserc_reasoning", "")
                    break

            records.append({
                "fy": fy,
                "order_ref": meta.get("order_ref", ""),
                "claimed": claimed,
                "approved": approved,
                "cut_pct": cut_pct,
                "kserc_reasoning": kserc_reasoning,
            })

        return records

    def get_capital_structure(self, licensee: str, fy: str) -> Dict[str, float]:
        """Get the capital structure (GFA, NFA, grants, etc.) for a specific year."""
        history = self.get_licensee_history(licensee)
        if fy in history:
            return history[fy].get("capital_structure", {})
        return {}

    def get_energy_data(self, licensee: str, fy: str) -> Dict[str, float]:
        """Get energy purchase/sales/loss data for a specific year."""
        history = self.get_licensee_history(licensee)
        if fy in history:
            return history[fy].get("energy_data", {})
        return {}

    def get_interim_relief(self, licensee: str, fy: str) -> Dict[str, Any]:
        """Get interim relief details for a specific year."""
        history = self.get_licensee_history(licensee)
        if fy in history:
            return history[fy].get("interim_relief", {})
        return {}

    def get_order_structure(self, licensee: str = None) -> Dict[str, Any]:
        """
        Get the order section structure from any past order.
        Used to match our output format to real KSERC order format.
        """
        # Return structure from any available order
        for lic, years in self.db.items():
            if licensee and lic.lower() != licensee.lower():
                continue
            for fy, data in years.items():
                structure = data.get("order_structure", {})
                if structure.get("sections"):
                    return structure
        return {}

    def build_precedent_justification(
        self, licensee: str, component: str, claimed: float, fy: str
    ) -> str:
        """
        Build a precedent-based justification string for the auditor.

        Example output:
        "Precedent: In Technopark FY 2022-23 (OP 84/2023), the Commission
        approved Employee Cost of Rs. 27.82L against a claim of Rs. 54.54L
        (49% reduction). KSERC reasoning: 'As per the Tariff Regulations, 2021,
        the licensee shall be allowed to recover the O&M expenses as per the
        norms specified in Annexure-7...'"
        """
        history = self.get_component_history(licensee, component)
        if not history:
            return ""

        # Get the most recent prior year's data
        prior_records = [r for r in history if r["fy"] < fy]
        if not prior_records:
            # Use any available record
            prior_records = history

        latest = prior_records[-1]

        parts = []
        parts.append(
            f"Precedent: In {licensee} FY {latest['fy']} ({latest['order_ref']}), "
            f"the Commission approved Rs. {latest['approved']:.2f} Lakhs "
            f"against a claim of Rs. {latest['claimed']:.2f} Lakhs"
        )

        if latest["cut_pct"] > 0:
            parts.append(f" ({latest['cut_pct']:.1f}% reduction)")
        parts.append(".")

        return "".join(parts)

    def get_cumulative_surplus(self, licensee: str) -> float:
        """Get the latest cumulative revenue surplus from past orders."""
        history = self.get_licensee_history(licensee)
        if not history:
            return 0.0

        latest_fy = max(history.keys())
        final = history[latest_fy].get("final_result", {})
        return final.get("cumulative_gap_surplus", 0.0)

    def get_imputed_interest_rate(self, licensee: str) -> float:
        """Get the interest rate used for imputed interest on surplus."""
        history = self.get_licensee_history(licensee)
        if not history:
            return 0.0

        latest_fy = max(history.keys())
        final = history[latest_fy].get("final_result", {})
        surplus = final.get("cumulative_gap_surplus", 0.0)
        imputed = final.get("imputed_interest_on_surplus", 0.0)
        if surplus > 0 and imputed > 0:
            return round(imputed / surplus * 100, 2)
        return 0.0


# Singleton
try:
    precedent_lookup = PrecedentLookup()
except Exception as e:
    logger.error(f"Failed to initialize PrecedentLookup: {e}")
    precedent_lookup = None
