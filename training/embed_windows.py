"""MindPulse — Align per-window keystroke sequences with labeled windows.

Builds encoder inputs for every labeled window:
  - SWELL-KW: per-minute windows from the raw uLog XMLs (flight-only; uLog
    has no key-up events -> hold channel zero-masked, like IKDD)
  - Kaggle raw rebuilt: 30-min windows from raw press/release events
    (full hold + flight)

Output: embed_inputs.npz aligned with the labeled feature matrices:
  hold/flight/mask [N, MAX_LEN], window_ids, source
"""

from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\ItzP\miniproject\training")
from prep_sequences import MAX_LEN, log_scale, to_fixed  # noqa: E402


def swell_window_sequences(ulog_dir: str, perminute_tab: str):
    """Per-minute hold/flight sequences for SWELL blocks (flight only)."""
    import xml.etree.ElementTree as ET

    pm = pd.read_csv(perminute_tab, sep="\t")
    pm["ts"] = pd.to_datetime(pm["timestamp"], format="%Y%m%dT%H%M%S%f",
                              errors="coerce")

    seqs, wids = [], []
    for fname in sorted(glob.glob(os.path.join(ulog_dir, "*.xml"))):
        m = re.match(r"a_pp(\d+)_c(\d)_uLog_(\d{8})_(\d{6})", os.path.basename(fname), re.I)
        if not m:
            continue
        pp = f"PP{int(m.group(1))}"
        t0 = pd.to_datetime(f"{m.group(3)} {m.group(4)}", format="%Y%m%d %H%M%S")

        times = []
        for ev in ET.iterparse(fname, events=("end",)):
            if ev[1].tag != "Event":
                continue
            ts_el = ev[1].find("TimeStamp")
            typ_el = ev[1].find("EventType")
            if ts_el is not None and typ_el is not None and typ_el.text == "Keyboard":
                times.append(pd.Timestamp(ts_el.text).timestamp())
            ev[1].clear()
        times.sort()
        if len(times) < 10:
            continue
        t_arr = np.asarray(times, dtype=np.float64)
        t0_utc = t_arr[0]
        # relative seconds: uLog timestamps are UTC, per-minute rows are local;
        # both anchored at the block start (filename t0 = local) -> offset-free
        t0_local = t0.timestamp()

        row_mask = (pm["PP"] == pp) & (pm["ts"] >= t0) & (pm["ts"] < t0 + pd.Timedelta(hours=3))
        for _, row in pm[row_mask].iterrows():
            w0_rel = (row["ts"].timestamp() - t0_local)
            if w0_rel < -60:
                continue
            sel = (t_arr - t0_utc >= w0_rel) & (t_arr - t0_utc < w0_rel + 60)
            if sel.sum() < 10:
                continue
            t_sel = t_arr[sel]
            flight = np.diff(t_sel) * 1000.0  # ms
            if len(flight) < 10:
                continue
            seqs.append({
                "hold": np.zeros(len(t_sel), dtype=np.float64),
                "flight": flight,
                "window_id": f"swell_{pp}_{row.name}",
                "row_idx": row.name,
                "source": "swell",
            })
    return seqs


def kaggle_window_sequences(src_dir: str):
    """30-min windows from raw events, aligned by window_start."""
    rebuilt = pd.read_csv(r"C:\Users\ItzP\miniproject\training\data\kaggle_raw_rebuilt.csv")
    seqs = []
    for _, row in rebuilt.iterrows():
        n = row["user_id"].replace("kaggle_user", "")
        user = f"user {n}"
        kp = pd.read_csv(os.path.join(src_dir, "Data", user, "keystrokes.tsv"), sep="\t",
                         encoding="latin-1", on_bad_lines="skip", quoting=3)
        kp["Press_Time"] = pd.to_datetime(kp["Press_Time"], format="mixed")
        kp["Relase_Time"] = pd.to_datetime(kp["Relase_Time"], format="mixed")
        w0 = pd.Timestamp(row["window_start"])
        w1 = w0 + pd.Timedelta(minutes=30)
        k = kp[(kp["Press_Time"] >= w0) & (kp["Press_Time"] < w1)]
        if len(k) < 10:
            continue
        press = k["Press_Time"].to_numpy(dtype="datetime64[us]").astype(np.float64) / 1e6
        release = k["Relase_Time"].to_numpy(dtype="datetime64[us]").astype(np.float64) / 1e6
        hold = (release - press) * 1000.0
        flight = np.diff(press) * 1000.0
        if len(hold) < 10 or len(flight) < 10:
            continue
        seqs.append({
            "hold": hold,
            "flight": flight,
            "window_id": f"kaggle_{row.name}",
            "row_idx": row.name,
            "source": "kaggle",
        })
    return seqs


def main() -> None:
    seqs = []
    seqs += swell_window_sequences(
        r"C:\Users\ItzP\miniproject\training\data\swell_ulog",
        r"C:\Users\ItzP\miniproject\training\data\Behavioral-features - per minute.tab")
    seqs += kaggle_window_sequences(r"C:\Users\ItzP\AppData\Local\Temp\kaggle_src")
    print(f"windows with sequences: {len(seqs)} "
          f"({sum(1 for s in seqs if s['source']=='swell')} swell, "
          f"{sum(1 for s in seqs if s['source']=='kaggle')} kaggle)")

    H = np.zeros((len(seqs), MAX_LEN), dtype=np.float32)
    F = np.zeros((len(seqs), MAX_LEN), dtype=np.float32)
    M = np.zeros((len(seqs), MAX_LEN), dtype=bool)
    ids, sources, row_idx = [], [], []
    for i, s in enumerate(seqs):
        h_f, h_m = to_fixed(log_scale(np.asarray(s["hold"], dtype=np.float64)))
        f_f, f_m = to_fixed(log_scale(np.asarray(s["flight"], dtype=np.float64)))
        H[i] = h_f
        F[i] = f_f
        M[i] = h_m | f_m
        ids.append(s["window_id"])
        sources.append(s["source"])
        row_idx.append(s["row_idx"])

    out = r"C:\Users\ItzP\miniproject\training\data\embed_inputs.npz"
    np.savez_compressed(out, hold=H, flight=F, mask=M,
                        window_id=np.asarray(ids), source=np.asarray(sources),
                        row_idx=np.asarray(row_idx))
    print("saved:", out)


if __name__ == "__main__":
    main()
