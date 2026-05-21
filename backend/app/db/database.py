import sqlite3
from pathlib import Path
from typing import Iterable

from app.config import get_settings


def get_db_path() -> Path:
    path = get_settings().database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def execute_script(sql: str) -> None:
    with connect() as conn:
        conn.executescript(sql)


def fetch_all(query: str, params: Iterable[object] = ()) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def fetch_one(query: str, params: Iterable[object] = ()) -> dict | None:
    with connect() as conn:
        row = conn.execute(query, tuple(params)).fetchone()
    return dict(row) if row else None
