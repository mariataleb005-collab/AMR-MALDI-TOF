"""Analysis history (SQLite, Python standard library).

Stores the sample ID, file name, the spectrum (6,000 intensities, compressed) and the calls of each
analysis. No patient data is stored.
"""
import json
import os
import sqlite3
import zlib
from array import array
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("ATHAR_DB_PATH", Path(__file__).resolve().parent / "history.sqlite3"))


def connect():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            sample_id TEXT NOT NULL DEFAULT '',
            species TEXT NOT NULL,
            filename TEXT NOT NULL,
            feature_count INTEGER NOT NULL,
            results_json TEXT NOT NULL,
            spectrum BLOB
        )""")


def pack(spectrum):
    return zlib.compress(array("f", spectrum).tobytes())


def unpack(blob):
    values = array("f")
    values.frombytes(zlib.decompress(blob))
    return values.tolist()


def save_analysis(sample_id, species, filename, spectrum, results):
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO analyses (created_at, sample_id, species, filename, feature_count, results_json, spectrum) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (created_at, sample_id, species, filename, len(spectrum), json.dumps(results), pack(spectrum)),
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


def get_analysis(analysis_id, with_spectrum=False):
    with connect() as db:
        row = db.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    if row is None:
        return None
    record = _record(row)
    if with_spectrum:
        record["spectrum"] = unpack(row["spectrum"]) if row["spectrum"] else None
    return record
