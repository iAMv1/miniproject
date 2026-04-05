"""MindPulse Backend — In-memory history store."""

from __future__ import annotations
from typing import Dict, List
from app.schemas.stress import HistoryPoint

_store: Dict[str, List[dict]] = {}
MAX_POINTS = 500


def reset(user_id: str):
    """Clear all in-memory history for a user (session reset)."""
    _store.pop(user_id, None)


def append(user_id: str, point: dict):
    if user_id not in _store:
        _store[user_id] = []
    _store[user_id].append(point)
    if len(_store[user_id]) > MAX_POINTS:
        _store[user_id] = _store[user_id][-MAX_POINTS:]


def get_history(user_id: str, hours: int = 24) -> List[HistoryPoint]:
    import time

    cutoff = time.time() - (hours * 3600)
    points = _store.get(user_id, [])
    return [HistoryPoint(**p) for p in points if p["timestamp"] > cutoff]


def get_stats(user_id: str) -> dict:
    points = _store.get(user_id, [])
    if not points:
        return {
            "total_samples": 0,
            "avg_score": 0,
            "stressed_pct": 0,
            "current_level": "UNKNOWN",
            "typing_speed_wpm": 0,
            "rage_click_count": 0,
            "error_rate": 0,
            "click_count": 0,
        }
    scores = [p["score"] for p in points]
    stressed = sum(1 for p in points if p["level"] == "STRESSED")

    # Average raw features from stored history
    avg_wpm = sum(p.get("typing_speed_wpm", 0) for p in points) / len(points)
    total_rage = sum(p.get("rage_click_count", 0) for p in points)
    avg_error = sum(p.get("error_rate", 0) for p in points) / len(points)
    total_clicks = sum(p.get("click_count", 0) for p in points)

    return {
        "total_samples": len(points),
        "avg_score": round(sum(scores) / len(scores), 1),
        "stressed_pct": round(stressed / len(points) * 100, 1),
        "current_level": points[-1]["level"] if points else "UNKNOWN",
        "typing_speed_wpm": round(avg_wpm, 1),
        "rage_click_count": int(total_rage),
        "error_rate": round(avg_error, 3),
        "click_count": int(total_clicks),
    }

