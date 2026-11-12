"""Analysis history (SQLite, Python standard library).

Stores the sample ID, file name and the calls of each analysis. The spectrum itself is never stored.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "history.sqlite3"


def connect():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize():
    with connect() as db:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(analyses)")}
        if columns and "results_json" not in columns:
            # Records from the earlier simulated version are kept aside, not shown.
            db.execute("ALTER TABLE analyses RENAME TO analyses_simulated_legacy")
        db.execute("""CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            sample_id TEXT NOT NULL DEFAULT '',
            species TEXT NOT NULL,
            filename TEXT NOT NULL,
            feature_count INTEGER NOT NULL,
            results_json TEXT NOT NULL
        )""")


def save_analysis(sample_id, species, filename, feature_count, results):
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO analyses (created_at, sample_id, species, filename, feature_count, results_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (created_at, sample_id, species, filename, feature_count, json.dumps(results)),
        )
        return cursor.lastrowid


def _record(row):
    return dict(id=row["id"], created_at=row["created_at"], sample_id=row["sample_id"],
                species=row["species"], filename=row["filename"], feature_count=row["feature_count"],
                results=json.loads(row["results_json"]))


def get_analyses():
    with connect() as db:
        rows = db.execute("SELECT * FROM analyses ORDER BY id DESC").fetchall()
    return [_record(row) for row in rows]


def get_analysis(analysis_id):
    with connect() as db:
        row = db.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    return _record(row) if row else None
