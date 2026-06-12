from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterable

from app.config import get_settings


def get_db_path() -> Path:
    path = get_settings().database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class _Row(dict):
    """Dict that also supports positional [0] access, matching sqlite3.Row behaviour."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class _PgCursor:
    def __init__(self, cur):
        self._cur = cur

    def _cols(self) -> list[str]:
        return [d[0] for d in self._cur.description] if self._cur.description else []

    def fetchall(self) -> list[_Row]:
        cols = self._cols()
        return [_Row(zip(cols, row)) for row in self._cur.fetchall()]

    def fetchone(self) -> _Row | None:
        cols = self._cols()
        row = self._cur.fetchone()
        return _Row(zip(cols, row)) if row else None

    def __iter__(self):
        cols = self._cols()
        for row in self._cur:
            yield _Row(zip(cols, row))


class _NullCursor:
    """No-op result for PRAGMA statements skipped on PostgreSQL."""
    def fetchall(self) -> list: return []
    def fetchone(self): return None
    def __iter__(self): return iter([])


class _PgConnection:
    def __init__(self, raw_conn):
        self._conn = raw_conn

    @staticmethod
    def _fix(sql: str) -> str:
        sql = sql.replace("?", "%s")
        sql = sql.replace("datetime('now')", "NOW()")
        sql = sql.replace("GLOB '[0-9]*'", "~ '^[0-9]'")
        return sql

    def execute(self, sql: str, params=()):
        if sql.strip().upper().startswith("PRAGMA"):
            return _NullCursor()
        sql = self._fix(sql)
        cur = self._conn.cursor()
        cur.execute(sql, params or None)
        return _PgCursor(cur)

    def executemany(self, sql: str, params_list):
        sql = self._fix(sql)
        cur = self._conn.cursor()
        cur.executemany(sql, list(params_list))

    def executescript(self, sql: str) -> None:
        cur = self._conn.cursor()
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                cur.execute(stmt)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        self._conn.close()


class _SqliteConnection:
    def __init__(self, raw_conn: sqlite3.Connection):
        self._conn = raw_conn

    def execute(self, sql: str, params=()):
        return self._conn.execute(sql, params)

    def executemany(self, sql: str, params_list):
        self._conn.executemany(sql, params_list)

    def executescript(self, sql: str) -> None:
        self._conn.executescript(sql)

    @property
    def total_changes(self) -> int:
        return self._conn.total_changes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        self._conn.close()


def connect() -> _PgConnection | _SqliteConnection:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        import psycopg2  # type: ignore
        raw = psycopg2.connect(database_url)
        return _PgConnection(raw)
    raw = sqlite3.connect(get_db_path())
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA journal_mode = WAL")
    raw.execute("PRAGMA foreign_keys = ON")
    return _SqliteConnection(raw)


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
