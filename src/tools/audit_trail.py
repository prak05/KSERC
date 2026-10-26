import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

AUDIT_DIR = Path(__file__).resolve().parents[2] / "data" / "audit_trail"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

def log_decision(
    analysis_id: str,
    decision_type: str,
    details: str,
    clause_ref: str = "",
    user_id: str = "system"
) -> None:
    """
    Log an audit decision to an append-only JSONL file.
    
    Parameters
    ----------
    analysis_id : str
        Unique identifier for the analysis session.
    decision_type : str
        Category of the decision (e.g., 'override', 'disallowance', 'approval').
    details : str
        Detailed description of the decision/change.
    clause_ref : str, optional
        Relevant KSERC regulation clause, by default "".
    user_id : str, optional
        User making the decision, by default "system".
    """
    log_file = AUDIT_DIR / f"{analysis_id}.jsonl"
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "analysis_id": analysis_id,
        "user_id": user_id,
        "type": decision_type,
        "details": details,
        "clause_ref": clause_ref
    }
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to write audit log for {analysis_id}: {e}")

def get_audit_trail(analysis_id: str) -> list[dict]:
    """
    Retrieve the full audit trail for a given analysis session.
    """
    log_file = AUDIT_DIR / f"{analysis_id}.jsonl"
    if not log_file.exists():
        return []
        
    trail = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    trail.append(json.loads(line))
    except Exception as e:
        logger.error(f"Failed to read audit log for {analysis_id}: {e}")
        
    return trail
