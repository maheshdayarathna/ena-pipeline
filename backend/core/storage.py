"""
Result storage — SQLite (built into Python, no setup).

Stores each analysis result (biomarker A/B/C + metadata) so there is a record
of past analyses. No image or per-cell data is stored — just the results, to
keep the database small. The DB is a single file in backend/ (git-ignored).
"""

from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

DB_PATH = Path(__file__).resolve().parent / "results.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the results table if it doesn't exist. Safe to call on every startup."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at    TEXT NOT NULL,
                filename      TEXT,
                use_diffusion INTEGER NOT NULL,
                -- biomarker A (primary)
                a_total       INTEGER, a_abnormal INTEGER, a_per_1000 REAL,
                -- biomarker B (combined)
                b_total       INTEGER, b_abnormal INTEGER, b_per_1000 REAL,
                -- biomarker C (reconstruction)
                c_total       INTEGER, c_abnormal INTEGER, c_per_1000 REAL,
                -- full stage counts as JSON, for reference
                stage_counts  TEXT
            )
        """)
        conn.commit()


def save_analysis(filename: str, use_diffusion: bool,
                  biomarker: Dict[str, Any], stage_counts: Dict[str, Any]) -> int:
    """Persist one analysis result. Returns the new row id."""
    a = biomarker["A_real_only"]
    b = biomarker["B_combined"]
    c = biomarker["C_reconstruction_only"]
    with _connect() as conn:
        cur = conn.execute("""
            INSERT INTO analyses (
                created_at, filename, use_diffusion,
                a_total, a_abnormal, a_per_1000,
                b_total, b_abnormal, b_per_1000,
                c_total, c_abnormal, c_per_1000,
                stage_counts
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            filename, int(use_diffusion),
            a["total_cells"], a["abnormal_cells"], a["abnormal_per_1000"],
            b["total_cells"], b["abnormal_cells"], b["abnormal_per_1000"],
            c["total_cells"], c["abnormal_cells"], c["abnormal_per_1000"],
            json.dumps(stage_counts),
        ))
        conn.commit()
        return cur.lastrowid


def list_analyses(limit: int = 50) -> List[Dict[str, Any]]:
    """Return recent analyses, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["use_diffusion"] = bool(d["use_diffusion"])
        try:
            d["stage_counts"] = json.loads(d["stage_counts"]) if d["stage_counts"] else {}
        except Exception:
            d["stage_counts"] = {}
        out.append(d)
    return out


def get_analysis(analysis_id: int):
    """Return a single analysis by id, or None."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["use_diffusion"] = bool(d["use_diffusion"])
    try:
        d["stage_counts"] = json.loads(d["stage_counts"]) if d["stage_counts"] else {}
    except Exception:
        d["stage_counts"] = {}
    return d