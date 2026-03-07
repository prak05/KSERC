import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "kserc_truing_up.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                analysis_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result_json TEXT
            )
        ''')
        conn.commit()

def save_analysis(analysis_id: str, status: str, result: dict = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT OR REPLACE INTO analysis_results (analysis_id, status, result_json)
            VALUES (?, ?, ?)
        ''', (analysis_id, status, json.dumps(result) if result else None))
        conn.commit()

def get_analysis(analysis_id: str) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            'SELECT status, result_json FROM analysis_results WHERE analysis_id = ?',
            (analysis_id,)
        )
        row = cursor.fetchone()
        if row:
            status, result_json = row
            return {
                "status": status,
                "result": json.loads(result_json) if result_json else None
            }
    return None
