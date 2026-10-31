"""Ustawienia (JSON) i baza widzianych ogłoszeń (SQLite)."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "RadarOkazji"
SETTINGS = APP_DIR / "settings.json"
DB = APP_DIR / "seen.db"


def _ensure() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(data: dict) -> None:
    _ensure()
    SETTINGS.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8")


def _conn() -> sqlite3.Connection:
    _ensure()
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS seen (uid TEXT PRIMARY KEY)")
    return con


def is_new(uid: str) -> bool:
    with _conn() as con:
        return con.execute("SELECT 1 FROM seen WHERE uid=?",
                           (uid,)).fetchone() is None


def mark_seen(uid: str) -> None:
    with _conn() as con:
        con.execute("INSERT OR IGNORE INTO seen VALUES (?)", (uid,))
