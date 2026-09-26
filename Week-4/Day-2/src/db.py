"""SQLite loaders for structured RealEstate Hub data."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .config import PROCESSED, SQLITE_PATH, STRUCTURED


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or SQLITE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def build_sqlite(db_path: Path | None = None) -> Path:
    path = db_path or SQLITE_PATH
    conn = connect(path)
    try:
        for name in ("properties", "developers", "agents", "payment_plans"):
            csv_path = STRUCTURED / f"{name}.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"Missing {csv_path} — run scripts/seed_kb.py")
            df = pd.read_csv(csv_path)
            df.to_sql(name, conn, if_exists="replace", index=False)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_prop_city ON properties(city)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_prop_purpose ON properties(purpose)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_prop_status ON properties(status)"
        )
        conn.commit()
    finally:
        conn.close()
    return path


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    conn = connect()
    try:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None
