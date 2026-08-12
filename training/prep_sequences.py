"""MindPulse — Unified keystroke-sequence preparation for SSL pretraining.

Converts three unlabeled corpora into one unified sequence format:

    sequences.npz  (dict)
      hold:    float32 [N, MAX_LEN]  — per-keystroke hold times (ms, log-scaled)
      flight:  float32 [N, MAX_LEN]  — inter-keystroke intervals (ms, log-scaled)
      mask:    bool    [N, MAX_LEN]  — valid positions
      source:  str     [N]           — '136m' | 'ikdd' | 'kupa'
      session_id: str  [N]

Sources:
  136M  — TSV: PARTICIPANT_ID, TEST_SECTION_ID, PRESS_TIME, RELEASE_TIME (epoch ms)
  IKDD  — txt: header line (user, demo), then rows of keystroke latencies (ms)
  KUPA  — CSV: id, time, type ('down'/'up'), key (hold = up-down pair times)

Usage:
    python prep_sequences.py --out training/data/sequences.npz
"""

from __future__ import annotations

import argparse
import glob
import os

import numpy as np
import pandas as pd

MAX_LEN = 256
LOG_FLOOR = 1.0  # ms; hold/flight below this are set to 1 (log -> 0)


def log_scale(v: np.ndarray) -> np.ndarray:
    return np.log2(np.maximum(v, LOG_FLOOR))


def to_fixed(seq: np.ndarray, max_len: int = MAX_LEN) -> tuple:
    if len(seq) == 0:
        return np.zeros(max_len, dtype=np.float32), np.zeros(max_len, dtype=bool)
    seq = seq[:max_len]
    pad = max_len - len(seq)
    return np.pad(seq, (0, pad)).astype(np.float32), \
        np.concatenate([np.ones(len(seq), dtype=bool), np.zeros(pad, dtype=bool)])


def seq_from_136m(folder: str, limit: int = None) -> dict:
    """Per TEST_SECTION_ID: hold = release-press; flight = press[i+1]-press[i]."""
    holds, flights, ids, sources = [], [], [], []
    files = sorted(glob.glob(os.path.join(folder, "*.txt")))
    if limit:
        files = files[:limit]
    for f in files:
        df = pd.read_csv(f, sep="\t", usecols=["PARTICIPANT_ID", "TEST_SECTION_ID",
                                               "PRESS_TIME", "RELEASE_TIME"],
                         encoding="latin-1", on_bad_lines="skip", quoting=3, dtype=str)
        for col in ["PRESS_TIME", "RELEASE_TIME"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["PRESS_TIME", "RELEASE_TIME"])
        df = df[df["RELEASE_TIME"] >= df["PRESS_TIME"]]
        for sec, g in df.groupby("TEST_SECTION_ID"):
            press = g["PRESS_TIME"].to_numpy(dtype=np.float64)
            release = g["RELEASE_TIME"].to_numpy(dtype=np.float64)
            hold = release - press
            flight = np.diff(press)
            if len(hold) < 10:
                continue
            holds.append(log_scale(hold))
            flights.append(log_scale(flight))
            ids.append(f"{os.path.basename(f)}::{sec}")
            sources.append("136m")
    return dict(hold=holds, flight=flights, id=ids, source=sources)


def seq_from_ikdd(folder: str, limit: int = None) -> dict:
    """Each file = one user; each row = one keystroke sequence (latencies, ms).
    Hold times unknown -> hold=0-mask, flight = row values."""
    holds, flights, ids, sources = [], [], [], []
    files = sorted(glob.glob(os.path.join(folder, "*.txt")))
    if limit:
        files = files[:limit]
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        if len(lines) < 2:
            continue
        for line in lines[1:]:
            vals = []
            for x in line.strip().split(","):
                x = x.strip()
                if not x:
                    continue
                try:
                    vals.append(float(x))
                except ValueError:
                    continue  # key-id token like '8-0'
            if len(vals) < 10:
                continue
            v = np.asarray(vals, dtype=np.float64)
            holds.append(np.zeros(len(v), dtype=np.float32))
            flights.append(log_scale(v))
            ids.append(os.path.basename(f))
            sources.append("ikdd")
    return dict(hold=holds, flight=flights, id=ids, source=sources)


def seq_from_kupa(task_csv: str, limit: int = None) -> dict:
    """Events: type 'down'/'up' with ms timestamps. Hold = consecutive
    down->up pair of the same key (vectorized); flight = down[i+1]-down[i]."""
    holds, flights, ids, sources = [], [], [], []
    n = 0
    for ci, df in enumerate(pd.read_csv(task_csv, usecols=["id", "time", "type", "key"],
                                        chunksize=5_000_000)):
        df = df[df["type"].isin(["down", "up"])].sort_values(["id", "time"])
        g = df.reset_index(drop=True)
        # session = contiguous run of the same id (chunk boundaries may split a
        # session; acceptable for distributional pretraining, documented)
        run = (g["id"] != g["id"].shift(1)).cumsum()
        same_id = g["id"] == g["id"].shift(-1)
        nxt_key = g["key"].shift(-1)
        nxt_type = g["type"].shift(-1)
        nxt_time = g["time"].shift(-1)
        is_down = g["type"] == "down"
        pair = is_down & (nxt_type == "up") & (nxt_key == g["key"]) & same_id
        hold_df = pd.DataFrame({
            "run": run[pair].to_numpy(),
            "hold": (nxt_time[pair] - g["time"][pair]).to_numpy(dtype=np.float64),
        })
        down_df = pd.DataFrame({"run": run[is_down].to_numpy(),
                                "t": g.loc[is_down, "time"].to_numpy(dtype=np.float64)})
        down_df["flight"] = down_df.groupby("run")["t"].diff()
        down_df = down_df.dropna(subset=["flight"])

        for r, hg in hold_df.groupby("run"):
            hv = hg["hold"].to_numpy(dtype=np.float64)
            fv = down_df.loc[down_df["run"] == r, "flight"].to_numpy(dtype=np.float64)
            if len(hv) < 10 or len(fv) < 10:
                continue
            holds.append(log_scale(hv))
            flights.append(log_scale(fv))
            ids.append(f"kupa_chunk{ci}_run{r}")
            sources.append("kupa")
            n += 1
            if limit and n >= limit:
                return dict(hold=holds, flight=flights, id=ids, source=sources)
    return dict(hold=holds, flight=flights, id=ids, source=sources)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=r"C:\Users\ItzP\miniproject\training\data\sequences.npz")
    ap.add_argument("--limit", type=int, default=0, help="limit files per corpus (testing)")
    ap.add_argument("--skip-136m-raw", action="store_true",
                    help="skip the 4.7GB raw 136M txt parse (slow); sequences come from IKDD+KUPA")
    args = ap.parse_args()

    corpora = {}
    if not args.skip_136m_raw:
        c = seq_from_136m(r"C:\Users\ItzP\AppData\Local\Temp\typing136\extracted\Keystrokes\files",
                          args.limit or None)
        corpora["136m"] = c
        print(f"136m: {len(c['hold'])} sessions")
    else:
        print("136m raw: skipped (use --no-skip-136m-raw on a fast machine)")
    c = seq_from_ikdd(r"C:\Users\ItzP\miniproject\training\data\ikdd", args.limit or None)
    corpora["ikdd"] = c
    print(f"ikdd: {len(c['hold'])} sessions")
    c = seq_from_kupa(r"C:\Users\ItzP\miniproject\training\data\kupa_keys\KUPA-KEYS-TASK-1.csv",
                      args.limit or None)
    corpora["kupa"] = c
    print(f"kupa: {len(c['hold'])} sessions")

    hold = np.zeros((0, MAX_LEN), dtype=np.float32)
    flight = np.zeros((0, MAX_LEN), dtype=np.float32)
    mask = np.zeros((0, MAX_LEN), dtype=bool)
    ids, sources = [], []
    for name, c in corpora.items():
        for j, (h, fl) in enumerate(zip(c["hold"], c["flight"])):
            if len(h) < 10 or len(fl) < 10:
                continue
            h_f, h_m = to_fixed(h)
            f_f, f_m = to_fixed(fl)
            hold = np.vstack([hold, h_f])
            flight = np.vstack([flight, f_f])
            mask = np.vstack([mask, (h_m | f_m)])
            ids.append(c["id"][j])
            sources.append(name)

    np.savez_compressed(args.out, hold=hold, flight=flight, mask=mask,
                        session_id=np.asarray(ids), source=np.asarray(sources))
    print(f"\nTOTAL: {len(hold)} sessions -> {args.out}")
    from collections import Counter
    print(Counter(sources))


if __name__ == "__main__":
    main()
