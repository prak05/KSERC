import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

class RegulationIndex:
    def __init__(self, data_path: Optional[str] = None):
        if data_path:
            self.data_path = Path(data_path)
        else:
            # Default to data/regulations/regulation_clauses.json relative to project root
            self.data_path = Path(__file__).resolve().parents[3] / "data" / "regulations" / "regulation_clauses.json"
        
        self.clauses: Dict[str, Any] = {}
        self._load_data()

    def _load_data(self) -> None:
        if self.data_path.exists():
            with open(self.data_path, "r", encoding="utf-8") as f:
                self.clauses = json.load(f)
        else:
            print(f"Warning: Regulations file not found at {self.data_path}")

    def get_clause(self, clause_number: str) -> Optional[Dict[str, str]]:
        """
        Retrieve a specific clause by its assigned number, e.g., '24' or '73(3)'.
        """
        return self.clauses.get(clause_number)

    def search_clauses(self, topic: str) -> List[Dict[str, str]]:
        """
        Simple text search based on the topic string.
        """
        topic_lower = topic.lower()
        results = []
        for clause in self.clauses.values():
            if topic_lower in clause.get("topic", "").lower():
                results.append(clause)
        return results
