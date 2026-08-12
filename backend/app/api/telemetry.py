"""MindPulse — Telemetry ingestion (the desktop/client data channel).

Closes the biggest broken connection in the architecture: clients (Tauri
desktop, browser) previously collected events but had NO way to ship them.
This module receives raw event batches and stores them for the nightly
window-aggregation job (aggregation lives in the collector job, see
collect_telemetry.py).

Endpoint: POST /api/v1/telemetry/batch  (auth required)
Body:
  {"client": "desktop"|"browser",
   "events": [
     {"type": "key",  "t": 123.45, "key": "a", "down_ms": 123456, "up_ms": 123490},
     {"type": "mouse","t": 123.50, "x": 100, "y": 200, "kind": "move"|"left"|"right"|"scroll"},
     {"type": "window","t": 123.60, "title_hash": "abc123"}
   ]}
No key CONTENT is stored: "key" is hashed server-side (privacy by design,
same as the ETH field study).
"""
from __future__ import annotations

import hashlib
import sqlite3
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.ratelimit import SlidingWindowLimiter, rate_limit

router = APIRouter()

TELEMETRY_DB = "telemetry.db"
_limiter = SlidingWindowLimiter(max_requests=600, window_seconds=60)

SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    client TEXT NOT NULL,
    event_type TEXT NOT NULL,
    ts_epoch REAL NOT NULL,
    key_hash TEXT,
    x REAL, y REAL,
    kind TEXT,
    down_ms REAL, up_ms REAL,
    title_hash TEXT,
    received_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_telemetry_user_ts
    ON telemetry_events(user_id, ts_epoch);
"""


class TelemetryEvent(BaseModel):
    type: str  # key | mouse | window
    t: float
    key: str | None = None
    down_ms: float | None = None
    up_ms: float | None = None
    x: float | None = None
    y: float | None = None
    kind: str | None = None
    title_hash: str | None = None


class TelemetryBatch(BaseModel):
    client: str
    events: list[TelemetryEvent]


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(TELEMETRY_DB)
    conn.executescript(SCHEMA)
    return conn


@router.post("/telemetry/batch")
async def ingest_telemetry(
    batch: TelemetryBatch,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(rate_limit(_limiter)),
):
    user_id = current_user["id"]
    now = time.time()
    conn = _get_conn()
    try:
        rows = []
        for e in batch.events:
            key_hash = None
            if e.key is not None:
                # privacy: never store key content, only a per-user salted hash
                key_hash = hashlib.sha256(
                    f"{user_id}:{e.key}".encode()
                ).hexdigest()[:16]
            rows.append((user_id, batch.client, e.type, e.t, key_hash,
                         e.x, e.y, e.kind, e.down_ms, e.up_ms, e.title_hash, now))
        conn.executemany(
            "INSERT INTO telemetry_events "
            "(user_id, client, event_type, ts_epoch, key_hash, x, y, kind, "
            " down_ms, up_ms, title_hash, received_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "ok", "stored": len(rows)}


@router.get("/telemetry/stats")
async def telemetry_stats(
    current_user: dict = Depends(get_current_user),
    hours: int = Query(default=24, ge=1, le=168),
):
    conn = _get_conn()
    try:
        cur = conn.execute(
            "SELECT event_type, COUNT(*) FROM telemetry_events "
            "WHERE user_id = ? AND received_at > ? "
            "GROUP BY event_type",
            (current_user["id"], time.time() - hours * 3600),
        )
        return {"user_id": current_user["id"], "hours": hours,
                "counts": dict(cur.fetchall())}
    finally:
        conn.close()
