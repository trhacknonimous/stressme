from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from config import DATABASE_PATH


def connect():
    path = Path(DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            mode TEXT NOT NULL,
            target TEXT NOT NULL,
            success INTEGER NOT NULL DEFAULT 0,
            errors INTEGER NOT NULL DEFAULT 0,
            avg_latency REAL NOT NULL DEFAULT 0,
            details TEXT NOT NULL
        )
    """)
    db.commit()
    return db


def save_campaign(mode, target, success, errors, avg_latency, details):
    with connect() as db:
        db.execute("""
            INSERT INTO campaigns
            (mode, target, success, errors, avg_latency, details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            mode, target, int(success), int(errors),
            float(avg_latency), json.dumps(details),
        ))


def get_campaigns(limit=50):
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM campaigns ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]
