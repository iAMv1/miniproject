"""Privacy controls for locally stored MindPulse data.

The account record is deliberately retained so a signed-in user can continue to
use the app after a data reset. This router covers the behavioral data stores
owned by this service: history, interventions, telemetry, EMA labels, and the
per-user baseline database.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from app.api import ema, telemetry
from app.core.auth import get_current_user
from app.ml.model import BASELINE_DB
from app.services import history
from app.services.inference import engine

router = APIRouter()


def _rows_as_dicts(conn: sqlite3.Connection, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def _baseline_path(user_id: str) -> Path:
    return Path(BASELINE_DB.replace(".db", f"_{user_id}.db"))


@router.get("/privacy/export")
async def export_my_data(current_user: dict = Depends(get_current_user)):
    """Return all local behavioral data for the authenticated user as JSON."""
    user_id = str(current_user["id"])
    with history._connect() as conn:
        history_rows = _rows_as_dicts(
            conn,
            "SELECT timestamp, score, level, confidence, insights_json, model_score, equation_score, final_score, "
            "typing_speed_wpm, rage_click_count, error_rate, click_count, mouse_speed_mean "
            "FROM history WHERE user_id=? ORDER BY timestamp ASC",
            (user_id,),
        )
        intervention_rows = _rows_as_dicts(
            conn,
            "SELECT timestamp, action, intervention_type, alert_state, score_before, score_after, recovery_score, notes "
            "FROM intervention_events WHERE user_id=? ORDER BY timestamp ASC",
            (user_id,),
        )
    with telemetry._get_conn() as conn:
        telemetry_rows = _rows_as_dicts(
            conn,
            "SELECT client, event_type, ts_epoch, kind, down_ms, up_ms, received_at "
            "FROM telemetry_events WHERE user_id=? ORDER BY ts_epoch ASC",
            (user_id,),
        )
    with ema._get_conn() as conn:
        ema_rows = _rows_as_dicts(
            conn,
            "SELECT stress, fatigue, ts_epoch, source FROM ema_checkins WHERE user_id=? ORDER BY ts_epoch ASC",
            (user_id,),
        )
    return {
        "export_version": 1,
        "user_id": user_id,
        "scope": "local behavioral data stored by this service; account credentials are excluded",
        "history": history_rows,
        "interventions": intervention_rows,
        "telemetry": telemetry_rows,
        "ema_checkins": ema_rows,
    }


@router.delete("/privacy/data")
async def delete_my_behavioral_data(current_user: dict = Depends(get_current_user)):
    """Delete locally stored behavioral data while preserving the user account."""
    user_id = str(current_user["id"])
    history.reset(user_id)
    with telemetry._get_conn() as conn:
        telemetry_deleted = conn.execute(
            "DELETE FROM telemetry_events WHERE user_id=?", (user_id,)
        ).rowcount
        conn.commit()
    with ema._get_conn() as conn:
        ema_deleted = conn.execute(
            "DELETE FROM ema_checkins WHERE user_id=?", (user_id,)
        ).rowcount
        conn.commit()

    baseline_path = _baseline_path(user_id)
    baseline_deleted = baseline_path.exists()
    if baseline_deleted:
        baseline_path.unlink()
    engine._baselines.pop(user_id, None)

    return {
        "status": "ok",
        "account_retained": True,
        "deleted": {
            "history_and_interventions": True,
            "telemetry_events": telemetry_deleted,
            "ema_checkins": ema_deleted,
            "personal_baseline": baseline_deleted,
        },
    }
