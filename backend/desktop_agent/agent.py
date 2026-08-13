"""MindPulse — Desktop agent: full-OS behavioral tracking → Supabase.

Global keyboard/mouse/app-switch capture (pynput, privacy-safe: timings and
categories only, never content). Feature windows are computed with the SAME
math and units as the browser collector (frontend/src/lib/features.ts), sent
to the `infer` edge function, and persisted to stress_history +
focus_snapshots + telemetry_events — all scoped by RLS to the paired user.

Usage:
    pip install -r requirements.txt
    python pair.py --refresh-token <token>   # token from web app /privacy page
    python agent.py                          # runs until Ctrl+C
"""

from __future__ import annotations

import logging
import math
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.ml.data_collector import BehavioralCollector  # noqa: E402
from supabase_api import SupabaseAPI, load_config  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("mindpulse-agent")

WINDOW_MS = 30_000
MAX_HOLD_MS = 3000
MAX_FLIGHT_MS = 5000
IDLE_GAP_MS = 5000
RAGE_CLICK_MS = 400
MAX_MOUSE_SPEED = 5000
MAX_SCROLL_SPEED = 20000


# ────────────────────────────────────────────────────────────────
# Feature computation — parity port of frontend/src/lib/features.ts
# (units: hold/flight/pause ms, speeds px/s, rates per s/min).
# ────────────────────────────────────────────────────────────────

def _round(v: float, d: int) -> float:
    return round(v, d)


def _shannon_entropy(values: List[float], bins: int = 10) -> float:
    if len(values) < 3:
        return 0.0
    lo, hi = min(values), max(values)
    if hi == lo:
        return 0.0
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        idx = min(int((v - lo) / width), bins - 1)
        counts[idx] += 1
    n = len(values)
    entropy = 0.0
    for c in counts:
        if c > 0:
            p = c / n
            entropy -= p * math.log2(p)
    return entropy


def _direction_changes(moves: List[Dict[str, Any]]) -> int:
    if len(moves) < 3:
        return 0
    changes = 0
    for i in range(2, len(moves)):
        dx1 = moves[i - 1]["x"] - moves[i - 2]["x"]
        dy1 = moves[i - 1]["y"] - moves[i - 2]["y"]
        dx2 = moves[i]["x"] - moves[i - 1]["x"]
        dy2 = moves[i]["y"] - moves[i - 1]["y"]
        if (dx1 > 0 > dx2) or (dx1 < 0 < dx2) or (dy1 > 0 > dy2) or (dy1 < 0 < dy2):
            changes += 1
    return changes


class WindowFeatures:
    """Collect one 30s window's worth of events into a feature vector."""

    def __init__(self, start_ms: float):
        self.start_ms = start_ms
        self.hold_times: List[float] = []
        self.flight_times: List[float] = []
        self.total_chars = 0
        self.error_count = 0
        self.mouse_moves: List[Dict[str, Any]] = []
        self.mouse_speeds: List[float] = []
        self.click_ts: List[float] = []
        self.scroll_velocities: List[float] = []
        self.app_switches: List[float] = []
        self.last_press_ms: Optional[float] = None
        self.event_times: List[float] = []
        self.telemetry: List[Dict[str, Any]] = []
        self._last_scroll: Optional[tuple] = None  # (ts_ms, y_delta)

    def add_key(self, press_ms: float, release_ms: float, category: str) -> None:
        hold = release_ms - press_ms
        if 1 <= hold <= MAX_HOLD_MS:
            self.hold_times.append(hold)
        if category == "backspace":
            self.error_count += 1
        elif category in ("alpha", "digit", "special"):
            self.total_chars += 1
        if self.last_press_ms is not None:
            flight = press_ms - self.last_press_ms
            if flight < MAX_FLIGHT_MS:
                self.flight_times.append(flight)
        self.last_press_ms = press_ms
        self.event_times.append(press_ms)
        self.telemetry.append({
            "event_type": "key", "ts_epoch": press_ms / 1000,
            "kind": category, "down_ms": press_ms, "up_ms": release_ms,
        })

    def add_mouse_move(self, ts_ms: float, x: int, y: int) -> None:
        self.mouse_moves.append({"x": x, "y": y, "t": ts_ms})
        if len(self.mouse_moves) > 1:
            prev = self.mouse_moves[-2]
            dt = (ts_ms - prev["t"]) / 1000
            if dt > 0:
                dist = math.hypot(x - prev["x"], y - prev["y"])
                speed = dist / dt
                if speed < MAX_MOUSE_SPEED:
                    self.mouse_speeds.append(speed)
        self.event_times.append(ts_ms)

    def add_click(self, ts_ms: float, x: int, y: int, click_type: str) -> None:
        self.click_ts.append(ts_ms)
        self.event_times.append(ts_ms)
        self.telemetry.append({
            "event_type": "mouse_click", "ts_epoch": ts_ms / 1000,
            "kind": click_type, "x": float(x), "y": float(y),
        })

    def add_scroll(self, ts_ms: float, dy: int) -> None:
        self.event_times.append(ts_ms)
        if self._last_scroll is not None:
            prev_ts, _prev_dy = self._last_scroll
            dt = (ts_ms - prev_ts) / 1000
            if dt > 0:
                velocity = abs(dy) / dt
                if velocity < MAX_SCROLL_SPEED:
                    self.scroll_velocities.append(velocity)
        self._last_scroll = (ts_ms, dy)
        self.telemetry.append({
            "event_type": "mouse_scroll", "ts_epoch": ts_ms / 1000, "kind": str(dy),
        })

    def add_app_switch(self, ts_ms: float, category_hash: str) -> None:
        self.app_switches.append(ts_ms)
        self.event_times.append(ts_ms)
        self.telemetry.append({
            "event_type": "app_switch", "ts_epoch": ts_ms / 1000, "key_hash": category_hash,
        })

    def compute(self, window_start_ms: float, end_ms: float) -> Dict[str, float]:
        window_ms = max(1000, end_ms - window_start_ms)
        window_min = window_ms / 60000

        hold_mean = sum(self.hold_times) / len(self.hold_times) if self.hold_times else 0.0
        hold_std = (
            math.sqrt(sum((v - hold_mean) ** 2 for v in self.hold_times) / (len(self.hold_times) - 1))
            if len(self.hold_times) > 1 else 0.0
        )
        hold_median = sorted(self.hold_times)[len(self.hold_times) // 2] if self.hold_times else 0.0

        flight_mean = sum(self.flight_times) / len(self.flight_times) if self.flight_times else 0.0
        flight_std = (
            math.sqrt(sum((v - flight_mean) ** 2 for v in self.flight_times) / (len(self.flight_times) - 1))
            if len(self.flight_times) > 1 else 0.0
        )

        wpm = (self.total_chars / 5) / window_min if self.total_chars > 0 else 0.0
        error_rate = self.error_count / self.total_chars if self.total_chars > 0 else 0.0

        pauses = [t for t in self.flight_times if t > 1500]
        pause_freq = len(pauses) / max(1.0, window_min)
        pause_mean = sum(pauses) / len(pauses) if pauses else 0.0

        bursts: List[int] = []
        current = 0
        for ft in self.flight_times:
            if ft < 500:
                current += 1
            else:
                if current > 1:
                    bursts.append(current)
                current = 0
        if current > 1:
            bursts.append(current)
        burst_mean = sum(bursts) / len(bursts) if bursts else 0.0

        rhythm_entropy = _shannon_entropy(self.flight_times)

        mouse_mean = sum(self.mouse_speeds) / len(self.mouse_speeds) if self.mouse_speeds else 0.0
        mouse_std = (
            math.sqrt(sum((v - mouse_mean) ** 2 for v in self.mouse_speeds) / (len(self.mouse_speeds) - 1))
            if len(self.mouse_speeds) > 1 else 0.0
        )

        direction_changes = _direction_changes(self.mouse_moves)

        rage = sum(
            1 for i in range(1, len(self.click_ts))
            if self.click_ts[i] - self.click_ts[i - 1] < RAGE_CLICK_MS
        )

        scroll_std = (
            math.sqrt(sum((v - (sum(self.scroll_velocities) / len(self.scroll_velocities))) ** 2 for v in self.scroll_velocities) / (len(self.scroll_velocities) - 1))
            if len(self.scroll_velocities) > 1 else 0.0
        )

        # Session fragmentation = share of window with no events (away/idle).
        idle_ms = 0.0
        times = sorted(self.event_times)
        for i in range(1, len(times)):
            gap = times[i] - times[i - 1]
            if gap > IDLE_GAP_MS:
                idle_ms += gap
        fragmentation = min(1.0, idle_ms / window_ms)

        # Tab-switch analogue: app switches + gap entropy (privacy-safe hashes).
        switch_gaps = [
            self.app_switches[i] - self.app_switches[i - 1]
            for i in range(1, len(self.app_switches))
        ]

        now = time.localtime()
        return {
            "hold_time_mean": _round(hold_mean, 4),
            "hold_time_std": _round(hold_std, 4),
            "hold_time_median": _round(hold_median, 4),
            "flight_time_mean": _round(flight_mean, 4),
            "flight_time_std": _round(flight_std, 4),
            "typing_speed_wpm": _round(min(wpm, 200), 2),
            "error_rate": _round(min(error_rate, 1), 4),
            "pause_frequency": _round(pause_freq, 2),
            "pause_duration_mean": _round(pause_mean, 4),
            "burst_length_mean": _round(burst_mean, 2),
            "rhythm_entropy": _round(rhythm_entropy, 4),
            "mouse_speed_mean": _round(mouse_mean, 2),
            "mouse_speed_std": _round(mouse_std, 2),
            "direction_change_rate": _round(direction_changes / max(1.0, window_ms / 1000), 2),
            "click_count": len(self.click_ts),
            "rage_click_count": rage,
            "scroll_velocity_std": _round(scroll_std, 2),
            "tab_switch_freq": _round(len(self.app_switches) / max(1.0, window_min), 2),
            "switch_entropy": _round(_shannon_entropy(switch_gaps), 4),
            "session_fragmentation": _round(fragmentation, 4),
            "hour_of_day": _round(now.tm_hour + now.tm_min / 60, 2),
            "day_of_week": now.tm_wday,
            "session_duration_min": _round(window_ms / 60000, 2),
        }


# ────────────────────────────────────────────────────────────────
# Main loop
# ────────────────────────────────────────────────────────────────

def main() -> int:
    cfg = load_config()
    api = SupabaseAPI(cfg)
    collector = BehavioralCollector()

    log.info("starting collectors (global keyboard/mouse/app-switch hooks)")
    collector.start()
    if not collector.is_running:
        log.error("pynput unavailable — cannot capture global input on this platform")
        return 1

    window_start = time.time() * 1000.0
    window = WindowFeatures(window_start)
    pruned = False

    def shutdown(_sig=None, _frame=None) -> None:
        log.info("stopping")
        collector.stop()
        api.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        time.sleep(2)
        now_ms = time.time() * 1000.0
        if now_ms - window_start < WINDOW_MS:
            continue

        keys, mice, contexts = collector.get_events()
        for k in keys:
            window.add_key(k.timestamp_press, k.timestamp_release, k.key_category)
        for m in mice:
            if m.event_type == "move":
                window.add_mouse_move(m.timestamp, int(m.x), int(m.y))
            elif m.event_type == "click":
                window.add_click(m.timestamp, int(m.x), int(m.y), m.click_type or "unknown")
            elif m.event_type == "scroll":
                window.add_scroll(m.timestamp, int(m.scroll_delta or 0))
        for c in contexts:
            window.add_app_switch(c.timestamp, c.category_hash)

        active = (
            window.total_chars > 0
            or bool(window.click_ts)
            or bool(window.mouse_speeds)
            or bool(window.app_switches)
        )
        if active:
            features = window.compute(window_start, now_ms)
            try:
                result = api.infer(features)
                score = float(result.get("score") or 0)
                level = str(result.get("level") or "UNKNOWN")
                deviation = str(result.get("deviation_level") or "OK")
                prob = float(result.get("stress_probability") or 0)
                uid = api.user_id()
                row = {
                    "user_id": uid,
                    "score": round(score, 1),
                    "level": level,
                    "deviation_level": deviation,
                    "stress_probability": round(prob, 4),
                    "typing_speed_wpm": float(features["typing_speed_wpm"]),
                    "error_rate": float(features["error_rate"]),
                    "click_count": int(features["click_count"]),
                }
                api.insert_stress_history(row)
                api.insert_focus_snapshot({
                    "user_id": uid,
                    "focus_score": max(0.0, min(100.0, 100.0 - score)),
                    "context_switches": len(window.app_switches),
                    "tab_hopping": len(window.app_switches),
                    "deep_work_minutes": round(features["session_duration_min"], 2)
                    if score < 35 else 0.0,
                })
                api.insert_telemetry(window.telemetry[-200:])
                if not pruned:
                    api.prune_stress_history(uid)
                    pruned = True
                log.info(
                    "window ok: score=%s level=%s switches=%s chars=%s",
                    row["score"], row["level"], len(window.app_switches), window.total_chars,
                )
            except Exception as e:  # noqa: BLE001 — keep the agent alive
                log.warning("window failed: %s", e)

        window = WindowFeatures(now_ms)
        window_start = now_ms


if __name__ == "__main__":
    raise SystemExit(main())
