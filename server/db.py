"""Database helper for aggregate metrics storage.

SQLite is used for local development, recording only aggregate counts.
Raw cycle or symptom logs are never accepted or stored.
"""
from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "aggregate.db"


def get_connection(db_file: Path | str | None = None) -> sqlite3.Connection:
    target = str(db_file or DB_PATH)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_file: Path | str | None = None) -> None:
    """Initializes the aggregate_metrics table."""
    conn = get_connection(db_file)
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS aggregate_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    bucket_date TEXT NOT NULL
                );
                """
            )
    finally:
        conn.close()


def record_aggregate_metric(metric_name: str, value: float, db_file: Path | str | None = None) -> int:
    """Records an allowed aggregate metric with today's date bucket."""
    init_db(db_file)
    conn = get_connection(db_file)
    today = datetime.date.today().isoformat()
    try:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO aggregate_metrics (metric_name, value, bucket_date)
                VALUES (?, ?, ?)
                """,
                (metric_name, float(value), today),
            )
            return int(cur.lastrowid)
    finally:
        conn.close()
