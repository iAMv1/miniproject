"""MindPulse — Rebuild labeled windows from the raw Kaggle 2-user source.

The repo's real_dataset.csv (all label=1) was a MIS-PROCESSED derivation.
The raw source (chaminduweerasinghe/stress-detection-by-keystrokeapp-mouse-
changes) contains timestamped SELF-REPORTED stress labels every ~30 min:

    Stress_Val: Neutral | S_Stressed | V_Stressed | F_Good | F_Great

This script re-extracts 23 MindPulse features over labeled windows and
emits a properly labeled 3-class dataset:
    0 = Neutral, 1 = S_Stressed, 2 = V_Stressed
F_* (feeling good/great) windows are excluded and counted (not mapped).

Usage:
    python rebuild_kaggle_labels.py <kaggle_src_dir> <output.csv>
"""

from __future__ import annotations

import glob
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

FEATURE_NAMES = [
    "hold_time_mean", "hold_time_std", "hold_time_median",
    "flight_time_mean", "flight_time_std", "typing_speed_wpm",
    "error_rate", "pause_frequency", "pause_duration_mean",
    "burst_length_mean", "rhythm_entropy", "mouse_speed_mean",
    "mouse_speed_std", "direction_change_rate", "click_count",
    "rage_click_count", "scroll_velocity_std", "tab_switch_freq",
    "switch_entropy", "session_fragmentation", "hour_of_day",
    "day_of_week", "session_duration_min",
]

LABEL_MAP = {"Neutral": 0, "S_Stressed": 1, "V_Stressed": 2}
WINDOW_MIN = 30
PAUSE_S = 1.0


def load_conditions(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    df["Time"] = pd.to_datetime(df["Time"], format="mixed")
    df = df[df["Stress_Val"].isin(LABEL_MAP)].copy()
    df["label"] = df["Stress_Val"].map(LABEL_MAP)
    return df


def load_keystrokes(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    df["Press_Time"] = pd.to_datetime(df["Press_Time"], format="mixed")
    df["Relase_Time"] = pd.to_datetime(df["Relase_Time"], format="mixed")
    df = df.sort_values("Press_Time").reset_index(drop=True)
    return df


def load_mouse(path: str, chunk: int = 2_000_000) -> pd.DataFrame:
    frames = []
    for i, df in enumerate(pd.read_csv(path, sep="\t", chunksize=chunk)):
        df["Time"] = pd.to_datetime(df["Time"], format="mixed")
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_activewindows(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, sep="\t")
        df["Time"] = pd.to_datetime(df["Time"], format="mixed")
        return df
    except Exception:
        return pd.DataFrame()


def window_features(keys: pd.DataFrame, mouse: pd.DataFrame,
                    windows: pd.DataFrame, t0: pd.Timestamp, t1: pd.Timestamp) -> dict:
    k = keys[(keys["Press_Time"] >= t0) & (keys["Press_Time"] < t1)]
    m = mouse[(mouse["Time"] >= t0) & (mouse["Time"] < t1)]
    w = windows[(windows["Time"] >= t0) & (windows["Time"] < t1)]

    f = {name: 0.0 for name in FEATURE_NAMES}
    f["session_duration_min"] = WINDOW_MIN

    if len(k) >= 2:
        press = k["Press_Time"].to_numpy(dtype="datetime64[us]").astype(np.float64) / 1e6
        release = k["Relase_Time"].to_numpy(dtype="datetime64[us]").astype(np.float64) / 1e6
        hold = (release - press) * 1000.0  # ms
        flight = np.diff(press) * 1000.0  # ms between presses

        f["hold_time_mean"] = float(hold.mean())
        f["hold_time_std"] = float(hold.std())
        f["hold_time_median"] = float(np.median(hold))
        f["flight_time_mean"] = float(flight.mean())
        f["flight_time_std"] = float(flight.std())

        n_chars = int((k["Key"].astype(str).str.len() > 0).sum())
        f["typing_speed_wpm"] = float(n_chars / 5.0 / (WINDOW_MIN / 60.0))
        f["error_rate"] = float(
            (k["Key"].astype(str).str.lower().isin(
                ["backspace", "delete"]).sum()) / max(n_chars, 1)
        )
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

        # SWELL definition: direction keys = keyboard arrow keys
        f["direction_change_rate"] = float(
            (k["Key"].astype(str).str.lower().isin(
                ["arrow_key", "left", "right", "up", "down", "arrowleft",
                 "arrowright", "arrowup", "arrowdown"]).sum())
        )

    if len(m) >= 2:
        mt = m["Time"].to_numpy(dtype="datetime64[us]").astype(np.float64) / 1e6
        xy = m[["X", "Y"]].to_numpy(dtype=np.float64)
        # SWELL definition: total distance per 60s bin -> per-minute speeds
        t_rel = (mt - mt[0]) / 60.0
        bins = np.floor(t_rel).astype(np.int64)
        dist_per_bin = np.zeros(bins.max() + 1)
        for b in range(bins.max() + 1):
            mask = bins == b
            if mask.sum() > 1:
                dist_per_bin[b] = np.hypot(
                    np.diff(xy[mask, 0]), np.diff(xy[mask, 1])).sum()
        speeds = dist_per_bin / 60.0  # px/s
        speeds = speeds[speeds > 0]
        if len(speeds):
            f["mouse_speed_mean"] = float(speeds.mean())
            f["mouse_speed_std"] = float(speeds.std())

        is_press = m["Event_Type"].astype(str).str.contains("Left_Pressed")
        f["click_count"] = float(is_press.sum())
        # rage clicks: 3+ left presses within 2s
        if f["click_count"] >= 3:
            pt = mt[is_press.to_numpy()]
            px = xy[is_press.to_numpy(), 0]
            py = xy[is_press.to_numpy(), 1]
            rage = 0
            for i in range(len(pt) - 2):
                if (pt[i + 2] - pt[i]) <= 2.0:
                    if (abs(px[i + 2] - px[i]) <= 50 and abs(py[i + 2] - py[i]) <= 50):
                        rage += 1
            f["rage_click_count"] = float(rage)
        f["scroll_velocity_std"] = float(
            (m["Event_Type"].astype(str).str.contains("Scroll")).sum())

    # tab/window switches from activewindows (SWELL: TabfocusChange)
    if len(w) > 1:
        f["tab_switch_freq"] = float(len(w) - 1)
        # switch entropy over window titles (approx)
        if "Activewindow" in w.columns:
            counts = w["Activewindow"].astype(str).value_counts().values
            p = counts / counts.sum()
            f["switch_entropy"] = float(-(p * np.log2(p)).sum())

    f["hour_of_day"] = float(t0.hour)
    f["day_of_week"] = float(t0.dayofweek)
    return f


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    src, out = sys.argv[1], sys.argv[2]

    all_rows = []
    for user_dir in sorted(glob.glob(os.path.join(src, "Data", "user*"))):
        user = os.path.basename(user_dir)
        cond_path = os.path.join(user_dir, "usercondition.tsv")
        keys_path = os.path.join(user_dir, "keystrokes.tsv")
        mouse_path = os.path.join(user_dir, "mousedata.tsv")
        if not all(os.path.exists(p) for p in (cond_path, keys_path, mouse_path)):
            print(f"[SKIP] {user}: missing files")
            continue

        print(f"[LOAD] {user}: conditions/keys/mouse")
        cond = load_conditions(cond_path)
        keys = load_keystrokes(keys_path)
        mouse = load_mouse(mouse_path)
        windows = load_activewindows(os.path.join(user_dir, "activewindows.tsv"))

        n_excluded = 0
        for _, row in cond.iterrows():
            t0 = row["Time"] - pd.Timedelta(minutes=WINDOW_MIN // 2)
            t1 = row["Time"] + pd.Timedelta(minutes=WINDOW_MIN // 2)
            feats = window_features(keys, mouse, windows, t0, t1)
            feats["label"] = int(row["label"])
            feats["user_id"] = f"kaggle_{user.replace(' ', '')}"
            feats["window_start"] = t0.isoformat()
            feats["source_type"] = "real"
            feats["label_origin"] = "self_report"
            all_rows.append(feats)

        print(f"[OK] {user}: {len(cond)} labeled windows built")

    df = pd.DataFrame(all_rows)
    cols = FEATURE_NAMES + ["label", "user_id", "window_start",
                            "source_type", "label_origin"]
    df = df[cols]
    df.to_csv(out, index=False)
    print("\n=== OUTPUT ===")
    print(f"rows: {len(df)}")
    print("label distribution:")
    print(df["label"].value_counts().sort_index().to_string())
    print("users:", df["user_id"].unique().tolist())
    print("written:", out)


if __name__ == "__main__":
    main()

