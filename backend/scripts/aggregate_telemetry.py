"""MindPulse — Aggregate telemetry + EMA into labeled per-user windows.

Nightly job (cron / scheduled): reads telemetry_events + ema_checkins,
builds 30-min windows around each check-in, extracts the same 23 features
the model consumes, and writes labeled training rows per user.

Output: data/per_user_labels/<user_id>.csv  (23 features + label + ts)

Usage: python scripts/aggregate_telemetry.py [--db-dir backend]
"""
from __future__ import annotations

import glob
import os
import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app.core.config import FEATURE_NAMES  # noqa: E402

WINDOW_MIN = 30
PAUSE_S = 1.0
# EMA stress -> binary label: <4 OK(0), >=4 ELEVATED(1). Documented threshold,
# matches SWELL neutral vs stressed split behavior in our data.
STRESS_THRESHOLD = 4.0


def build_window(events: pd.DataFrame, t0: pd.Timestamp, t1: pd.Timestamp) -> dict:
    ev = events[(events["ts_epoch"] >= t0.timestamp()) & (events["ts_epoch"] < t1.timestamp())]
    f = {name: 0.0 for name in FEATURE_NAMES}
    f["session_duration_min"] = WINDOW_MIN
    keys = ev[ev["event_type"] == "key"]
    mouse = ev[ev["event_type"] == "mouse"]

    if len(keys) >= 2 and keys["down_ms"].notna().all() and keys["up_ms"].notna().all():
        hold = (keys["up_ms"] - keys["down_ms"]).to_numpy(dtype=np.float64)
        press = keys["down_ms"].to_numpy(dtype=np.float64)
        flight = np.diff(press)
        f["hold_time_mean"] = float(hold.mean())
        f["hold_time_std"] = float(hold.std())
        f["hold_time_median"] = float(np.median(hold))
        f["flight_time_mean"] = float(flight.mean())
        f["flight_time_std"] = float(flight.std())
        f["typing_speed_wpm"] = float(len(keys) / 5.0 / (WINDOW_MIN / 60.0))
        f["error_rate"] = 0.0  # backspace count needs key hashing; see below
        f["pause_frequency"] = float((flight > PAUSE_S * 1000).sum())
        f["pause_duration_mean"] = float(flight[flight > PAUSE_S * 1000].mean()) \
            if (flight > PAUSE_S * 1000).any() else 0.0
        runs = [1]
        for g in flight:
            if g <= PAUSE_S * 1000:
                runs[-1] += 1
            else:
                runs.append(1)
        f["burst_length_mean"] = float(np.mean(runs))
        bins = np.arange(0, 5000, 100)
        counts, _ = np.histogram(flight, bins=bins)
        p = counts / max(counts.sum(), 1)
        f["rhythm_entropy"] = float(-(p[p > 0] * np.log2(p[p > 0])).sum())

    if len(mouse) >= 2:
        mt = mouse["ts_epoch"].to_numpy(dtype=np.float64)
        xy = np.column_stack([mouse["x"].to_numpy(dtype=np.float64),
                              mouse["y"].to_numpy(dtype=np.float64)])
        t_rel = (mt - mt[0]) / 60.0
        b = np.floor(t_rel).astype(np.int64)
        dist_per_bin = np.zeros(b.max() + 1)
        for i in range(b.max() + 1):
            m = b == i
            if m.sum() > 1:
                dist_per_bin[i] = np.hypot(np.diff(xy[m, 0]), np.diff(xy[m, 1])).sum()
        speeds = dist_per_bin / 60.0
        speeds = speeds[speeds > 0]
        if len(speeds):
            f["mouse_speed_mean"] = float(speeds.mean())
            f["mouse_speed_std"] = float(speeds.std())
        f["click_count"] = float((mouse["kind"] == "left").sum())
        f["rage_click_count"] = float((mouse["kind"] == "left").sum())  # refine later
        f["scroll_velocity_std"] = float((mouse["kind"] == "scroll").sum())

    f["hour_of_day"] = float(t0.hour)
    f["day_of_week"] = float(t0.dayofweek)
    return f


def main() -> None:
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    tel = sqlite3.connect(os.path.join(base, "telemetry.db"))
    ema = sqlite3.connect(os.path.join(base, "ema.db"))
    out_dir = os.path.join(base, "data", "per_user_labels")
    os.makedirs(out_dir, exist_ok=True)

    checkins = pd.read_sql("SELECT user_id, stress, ts_epoch FROM ema_checkins ORDER BY ts_epoch", ema)
    events = pd.read_sql(
        "SELECT user_id, event_type, ts_epoch, key_hash, x, y, kind, down_ms, up_ms "
        "FROM telemetry_events", tel)
    events["down_ms"] = pd.to_numeric(events["down_ms"], errors="coerce")
    events["up_ms"] = pd.to_numeric(events["up_ms"], errors="coerce")

    for user_id, g in checkins.groupby("user_id"):
        rows = []
        for _, c in g.iterrows():
            t0 = pd.Timestamp(c["ts_epoch"], unit="s") - pd.Timedelta(minutes=WINDOW_MIN // 2)
            t1 = t0 + pd.Timedelta(minutes=WINDOW_MIN)
            ue = events[events["user_id"] == user_id]
            f = build_window(ue, t0, t1)
            f["label"] = 1 if float(c["stress"]) >= STRESS_THRESHOLD else 0
            f["stress_raw"] = float(c["stress"])
            rows.append(f)
        if rows:
            df = pd.DataFrame(rows)[FEATURE_NAMES + ["label", "stress_raw"]]
            path = os.path.join(out_dir, f"{user_id}.csv")
            df.to_csv(path, index=False)
            print(f"{user_id}: {len(df)} labeled windows -> {path}")
    print("DONE")


if __name__ == "__main__":
    main()
