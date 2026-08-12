"""MindPulse — Drop-in storage for extended features (chat, wellness, focus).

Interface-compatible with the supabase-py client subset used by the
services (table().insert/select/update/upsert().eq().execute()).

Backends:
  - Supabase, when SUPABASE_URL + SUPABASE_ANON_KEY are set (real project)
  - Local SQLite otherwise (fully functional, single-user scale, no accounts)

Tables (auto-created): chat_sessions, chat_messages, wellness_checkins,
wellness_insights, focus_snapshots, user_shield_settings.

Rows are stored as JSON documents with a stable id; eq() filters are
applied client-side (tables are tiny — the honest trade at this scale).
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

_LOCAL_DB = "extended.db"

REQUIRED_TABLES = [
    "chat_sessions", "chat_messages", "wellness_checkins",
    "wellness_insights", "focus_snapshots", "user_shield_settings",
]


def _local_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_LOCAL_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables() -> None:
    conn = _local_conn()
    try:
        for table in REQUIRED_TABLES:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS sb_{table} "
                "(id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )
        conn.commit()
    finally:
        conn.close()


def _insert_row(table: str, payload: dict) -> dict:
    _ensure_tables()
    row = dict(payload)
    if "id" not in row:
        row["id"] = str(uuid.uuid4())
    conn = _local_conn()
    try:
        conn.execute(
            f"INSERT OR REPLACE INTO sb_{table} (id, data) VALUES (?, ?)",
            (str(row["id"]), json.dumps(row)),
        )
        conn.commit()
    finally:
        conn.close()
    return row


def _fetch_rows(table: str) -> List[dict]:
    _ensure_tables()
    conn = _local_conn()
    try:
        rows = conn.execute(f"SELECT data FROM sb_{table}").fetchall()
    finally:
        conn.close()
    return [json.loads(r["data"]) for r in rows]


class _Query:
    """Chainable query: select/update/upsert ... eq(...) ... execute()."""

    def __init__(self, table: str, op: str, payload: Optional[dict] = None):
        self.table = table
        self.op = op  # insert | select | update | upsert
        self.payload = payload or {}
        self.filters: List[tuple] = []
        self._limit: Optional[int] = None

    def eq(self, column: str, value: Any) -> "_Query":
        self.filters.append((column, value, "eq"))
        return self

    def gte(self, column: str, value: Any) -> "_Query":
        self.filters.append((column, value, "gte"))
        return self

    def lte(self, column: str, value: Any) -> "_Query":
        self.filters.append((column, value, "lte"))
        return self

    def neq(self, column: str, value: Any) -> "_Query":
        self.filters.append((column, value, "neq"))
        return self

    def order(self, column: str, desc: bool = False) -> "_Query":
        self.order_by = (column, desc)
        return self

    def limit(self, n: int) -> "_Query":
        self._limit = n
        return self

    def maybe_single(self) -> "_Query":
        self._maybe_single = True
        return self

    def _matches(self, row: dict) -> bool:
        for c, v, op in self.filters:
            rv = row.get(c)
            if op == "eq" and not (str(rv) == str(v)):
                return False
            if op == "neq" and not (str(rv) != str(v)):
                return False
            if op == "gte":
                try:
                    if not (float(rv) >= float(v)):
                        return False
                except (TypeError, ValueError):
                    if not (str(rv) >= str(v)):
                        return False
            if op == "lte":
                try:
                    if not (float(rv) <= float(v)):
                        return False
                except (TypeError, ValueError):
                    if not (str(rv) <= str(v)):
                        return False
        return True

    def execute(self) -> "Any":
        rows = _fetch_rows(self.table)
        if self.op == "insert":
            return _Result([_insert_row(self.table, self.payload)])
        if self.op == "upsert":
            hit = next((r for r in rows if self._matches(r)), None)
            if hit:
                merged = {**hit, **self.payload, "id": hit["id"]}
                _insert_row(self.table, merged)
                return _Result([merged])
            return _Result([_insert_row(self.table, self.payload)])
        if self.op == "update":
            updated = []
            for r in rows:
                if self._matches(r):
                    merged = {**r, **self.payload}
                    _insert_row(self.table, merged)
                    updated.append(merged)
            return _Result(updated)
        # select
        out = [r for r in rows if self._matches(r)]
        ob = getattr(self, "order_by", None)
        if ob:
            col, desc = ob
            out.sort(key=lambda r: str(r.get(col, "")), reverse=desc)
        if self._limit is not None:
            out = out[: self._limit]
        if getattr(self, "_maybe_single", False):
            return _Result(out[0] if out else None)
        return _Result(out)


class _Result:
    def __init__(self, data: List[dict]):
        self.data = data


class _Table:
    def __init__(self, name: str):
        self.name = name

    def insert(self, payload: dict) -> _Query:
        return _Query(self.name, "insert", payload)

    def select(self, *cols) -> _Query:
        return _Query(self.name, "select")

    def update(self, payload: dict) -> _Query:
        return _Query(self.name, "update", payload)

    def upsert(self, payload: dict, on_conflict: Any = None) -> _Query:
        return _Query(self.name, "upsert", payload)


class _StorageClient:
    """Local SQLite client exposing the supabase-py subset."""

    def table(self, name: str) -> _Table:
        return _Table(name)


_supabase_client: Any = None
_supabase_admin_client: Any = None


def get_supabase_client() -> Any:
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    if SUPABASE_URL and SUPABASE_ANON_KEY:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    else:
        _supabase_client = _StorageClient()
    return _supabase_client


def get_supabase_admin() -> Any:
    global _supabase_admin_client
    if _supabase_admin_client is not None:
        return _supabase_admin_client
    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        from supabase import create_client
        _supabase_admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        return _supabase_admin_client
    return get_supabase_client()


def check_supabase_connection() -> bool:
    try:
        client = get_supabase_client()
        if isinstance(client, _StorageClient):
            _ensure_tables()
            return True
        result = client.table("chat_sessions").select("count").limit(1).execute()
        return bool(result.data is not None)
    except Exception:
        return False
