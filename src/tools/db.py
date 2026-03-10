import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "kserc_truing_up.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        # ── Existing: Analysis results ────────────────────────────────
        conn.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                analysis_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result_json TEXT,
                progress_log TEXT
            )
        ''')
        # Add column if upgrading existing DB
        try:
            conn.execute('ALTER TABLE analysis_results ADD COLUMN progress_log TEXT')
        except Exception:
            pass  # Column already exists

        # ── New: Economic indicators per financial year ───────────────
        conn.execute('''
            CREATE TABLE IF NOT EXISTS economic_indicators (
                financial_year TEXT PRIMARY KEY,
                wpi_pct REAL,
                cpi_pct REAL,
                sbi_plr_pct REAL,
                hsd_price_rs REAL,
                power_purchase_rate_rs_per_kwh REAL,
                updated_at TEXT
            )
        ''')

        # ── New: Reference orders metadata (PDFs; MYT norms go to JSON) ─
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reference_orders (
                id TEXT PRIMARY KEY,
                order_type TEXT NOT NULL,
                licensee TEXT,
                financial_year TEXT,
                order_number TEXT,
                file_path TEXT,
                uploaded_at TEXT
            )
        ''')

        conn.commit()


# ── Analysis results ─────────────────────────────────────────────────────

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
            'SELECT status, result_json, progress_log FROM analysis_results WHERE analysis_id = ?',
            (analysis_id,)
        )
        row = cursor.fetchone()
        if row:
            status, result_json, progress_log = row
            return {
                "status": status,
                "result": json.loads(result_json) if result_json else None,
                "progress": json.loads(progress_log) if progress_log else [],
            }
    return None


def update_progress(analysis_id: str, stage: str, message: str):
    """Append a timestamped progress entry. Safe to call from any thread."""
    ts = datetime.utcnow().strftime("%H:%M:%S")
    entry = {"ts": ts, "stage": stage, "msg": message}
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        row = conn.execute(
            'SELECT progress_log FROM analysis_results WHERE analysis_id = ?',
            (analysis_id,)
        ).fetchone()
        log = json.loads(row[0]) if (row and row[0]) else []
        log.append(entry)
        conn.execute(
            'UPDATE analysis_results SET progress_log = ? WHERE analysis_id = ?',
            (json.dumps(log), analysis_id)
        )
        conn.commit()


# ── Economic Indicators ──────────────────────────────────────────────────

def get_all_economic_indicators() -> list:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            'SELECT financial_year, wpi_pct, cpi_pct, sbi_plr_pct, hsd_price_rs, '
            'power_purchase_rate_rs_per_kwh, updated_at '
            'FROM economic_indicators ORDER BY financial_year DESC'
        )
        rows = cursor.fetchall()
    return [
        {
            "financial_year": r[0],
            "wpi_pct": r[1],
            "cpi_pct": r[2],
            "sbi_plr_pct": r[3],
            "hsd_price_rs": r[4],
            "power_purchase_rate_rs_per_kwh": r[5],
            "updated_at": r[6],
        }
        for r in rows
    ]

def get_economic_indicators(financial_year: str) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            'SELECT wpi_pct, cpi_pct, sbi_plr_pct, hsd_price_rs, '
            'power_purchase_rate_rs_per_kwh FROM economic_indicators '
            'WHERE financial_year = ?', (financial_year,)
        )
        row = cursor.fetchone()
    if row:
        return {
            "wpi_pct": row[0], "cpi_pct": row[1],
            "sbi_plr_pct": row[2], "hsd_price_rs": row[3],
            "power_purchase_rate_rs_per_kwh": row[4],
        }
    return {}

def upsert_economic_indicators(financial_year: str, data: dict):
    now = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT OR REPLACE INTO economic_indicators
            (financial_year, wpi_pct, cpi_pct, sbi_plr_pct, hsd_price_rs,
             power_purchase_rate_rs_per_kwh, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            financial_year,
            data.get("wpi_pct"), data.get("cpi_pct"), data.get("sbi_plr_pct"),
            data.get("hsd_price_rs"), data.get("power_purchase_rate_rs_per_kwh"), now,
        ))
        conn.commit()


# ── Reference Orders ────────────────────────────────────────────────────

def save_reference_order(order_id: str, order_type: str, licensee: str,
                         financial_year: str, order_number: str, file_path: str):
    now = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT OR REPLACE INTO reference_orders
            (id, order_type, licensee, financial_year, order_number, file_path, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (order_id, order_type, licensee, financial_year, order_number, file_path, now))
        conn.commit()

def get_reference_orders(order_type: str = None) -> list:
    with sqlite3.connect(DB_PATH) as conn:
        if order_type:
            cursor = conn.execute(
                'SELECT id, order_type, licensee, financial_year, order_number, '
                'file_path, uploaded_at FROM reference_orders '
                'WHERE order_type = ? ORDER BY uploaded_at DESC', (order_type,)
            )
        else:
            cursor = conn.execute(
                'SELECT id, order_type, licensee, financial_year, order_number, '
                'file_path, uploaded_at FROM reference_orders ORDER BY uploaded_at DESC'
            )
        rows = cursor.fetchall()
    return [
        {"id": r[0], "order_type": r[1], "licensee": r[2],
         "financial_year": r[3], "order_number": r[4],
         "file_path": r[5], "uploaded_at": r[6]}
        for r in rows
    ]


# -- MYT Norms Override (set via Reference Data UI) --------------------------
def get_myt_norms_override(licensee_name: str, financial_year: str) -> dict:
    """Check DB for manual MYT norm overrides. Returns {} if not found."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                'SELECT norms_json FROM myt_norms_override WHERE licensee = ? AND financial_year = ?',
                (licensee_name, financial_year)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
    except Exception:
        pass  # Table does not exist yet -- fall back to JSON file
    return {}
