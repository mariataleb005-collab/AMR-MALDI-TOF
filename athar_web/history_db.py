"""Local demonstration prediction history (SQLite, Python standard library)."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'history.sqlite3'


def connect():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize():
    with connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            filename TEXT NOT NULL,
            feature_count INTEGER NOT NULL,
            mode TEXT NOT NULL,
            predictions_json TEXT NOT NULL
        )''')


def save_analysis(filename, feature_count, predictions):
    created_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with connect() as db:
        cursor = db.execute(
            'INSERT INTO analyses (created_at, filename, feature_count, mode, predictions_json) VALUES (?, ?, ?, ?, ?)',
            (created_at, filename, feature_count, 'simulation', json.dumps(predictions))
        )
        return cursor.lastrowid


def get_analyses():
    with connect() as db:
        rows = db.execute('SELECT * FROM analyses ORDER BY id DESC').fetchall()
    return [dict(id=row['id'], created_at=row['created_at'], filename=row['filename'],
                 feature_count=row['feature_count'], mode=row['mode'],
                 predictions=json.loads(row['predictions_json'])) for row in rows]
