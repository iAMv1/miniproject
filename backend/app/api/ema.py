"""MindPulse — EMA self-report loop (the label channel of the rebuild).

Self-reported stress labels are the ONLY ground truth for subjective
stress (first-principles axiom A3). The product collects them naturally:
  POST /api/v1/ema/checkin  {stress: 0-10, fatigue: 0-10}  (auth)
  GET  /api/v1/ema/status   {due: bool, last_checkin_at}
Labels pair with the telemetry windows around the checkin time to grow
per-user labeled datasets (per-user model training = the product's core).
"""
from __future__ import annotations

import sqlite3
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.ratelimit import SlidingWindowLimiter, rate_limit

router = APIRouter()

EMA_DB = "ema.db"
CHECKIN_INTERVAL_S = 30 * 60  # every 30 minutes max; never sooner

SCHEMA = """
CREATE TABLE IF NOT EXISTS ema_checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    stress REAL NOT NULL,
    fatigue REAL,
    ts_epoch REAL NOT NULL,
    source TEXT NOT NULL DEFAULT 'prompt'
);
CREATE INDEX IF NOT EXISTS idx_ema_user_ts ON ema_checkins(user_id, ts_epoch);
"""

_limiter = SlidingWindowLimiter(max_requests=60, window_seconds=60)


class EmaCheckin(BaseModel):
    stress: float = Field(ge=0, le=10, description="current stress 0-10")
    fatigue: float | None = Field(default=None, ge=0, le=10)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(EMA_DB)
    conn.executescript(SCHEMA)
    return conn


@router.post("/ema/checkin")
async def ema_checkin(
    req: EmaCheckin,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(rate_limit(_limiter)),
):
    user_id = current_user["id"]
    conn = _get_conn()
    try:
        last = conn.execute(
            "SELECT MAX(ts_epoch) FROM ema_checkins WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
        now = time.time()
        if last and (now - last) < CHECKIN_INTERVAL_S:
            raise HTTPException(
                status_code=429,
                detail=f"Check in again in {int(CHECKIN_INTERVAL_S - (now - last))}s",
            )
        conn.execute(
            "INSERT INTO ema_checkins (user_id, stress, fatigue, ts_epoch) VALUES (?,?,?,?)",
            (user_id, float(req.stress), req.fatigue, now),
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "ok", "stored": True, "stress": req.stress}


@router.get("/ema/status")
async def ema_status(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT MAX(ts_epoch) FROM ema_checkins WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
    finally:
        conn.close()
    now = time.time()
    return {"due": row is None or (now - row) >= CHECKIN_INTERVAL_S,
            "last_checkin_at": row, "next_in_s": max(0, int(CHECKIN_INTERVAL_S - (now - row))) if row else 0}
