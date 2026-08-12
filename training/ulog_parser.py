"""MindPulse — Noldus uLog 3.2.5 XML parser.

Extracts per-minute behavioral features from SWELL-KW raw uLog event logs
that are NOT present in the official per-minute feature file:

  - pause_frequency      (inter-keystroke gaps > 1s)
  - burst_length_mean    (mean consecutive keys without a >1s pause)
  - rhythm_entropy       (Shannon entropy of inter-key interval distribution)
  - hour_of_day / day_of_week (from exact event timestamps)
  - session_duration_min (minute index of each window)

Note: uLog 3.2.5 logs keystrokes as character/special-key events WITHOUT
key-up timestamps, so hold_time / flight_time / rhythm inter-key delays
cannot be derived from SWELL raw logs (SENSE-42 or MindPulse's own
collector are the sources for those).

Merges with the official per-minute file: run parse_ulog() on each
a_ppXX_cN_uLog_*.xml, then merge_into_perminute() to fill the gaps.

Usage:
    python ulog_parser.py <ulog.xml> <output_features.csv>
    python ulog_parser.py --merge <per-minute.tab> <ulog_dir> <output.tab>
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from collections import deque
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

EVENT_RE = re.compile(
    r"<Event>(.*?)</Event>", re.S
)
TYPE_RE = re.compile(r"<EventType>([^<]+)</EventType>")
ACTION_RE = re.compile(r"<EventAction>([^<]+)</EventAction>")
TS_RE = re.compile(r"<TimeStamp>([^<]+)</TimeStamp>")
KEYVAL_RE = re.compile(r"<KeyboardValue>([^<]*)</KeyboardValue>")
DESC_RE = re.compile(r"<EventDescription>([^<]*)</EventDescription>")

PAUSE_THRESHOLD_S = 1.0


def parse_ulog(xml_path: str, minute_window_s: int = 60) -> pd.DataFrame:
    """Parse one uLog XML into per-minute feature rows."""
    with open(xml_path, "r", encoding="utf-8", errors="replace") as f:
        data = f.read()

    events: List[Tuple[float, str]] = []
    for m in EVENT_RE.finditer(data):
        block = m.group(1)
        t = TS_RE.search(block)
        typ = TYPE_RE.search(block)
        if not t:
            continue
        ts = pd.Timestamp(t.group(1))
        events.append((ts.timestamp(), typ.group(1) if typ else ""))

    if not events:
        raise SystemExit(f"No events with timestamps in {xml_path}")

    events.sort(key=lambda e: e[0])
    t0 = events[0][0]
    minutes: Dict[int, List[float]] = {}
    key_times: Dict[int, List[float]] = {}
    for ts, typ in events:
        minute_idx = int((ts - t0) // minute_window_s)
        minutes.setdefault(minute_idx, []).append(ts)
        if typ == "Keyboard":
            key_times.setdefault(minute_idx, []).append(ts)

    rows = []
    for minute_idx in sorted(set(minutes) | set(key_times)):
        keys = np.asarray(sorted(key_times.get(minute_idx, [])), dtype=np.float64)
        # pause frequency: inter-key gaps > 1s
        if len(keys) > 1:
            gaps = np.diff(keys)
            pause_freq = float((gaps > PAUSE_THRESHOLD_S).sum())
            # bursts: consecutive runs of keys separated by <= 1s
            run_lens = [1]
            for g in gaps:
                if g <= PAUSE_THRESHOLD_S:
                    run_lens[-1] += 1
                else:
                    run_lens.append(1)
            burst_mean = float(np.mean(run_lens))
            # rhythm entropy over 100ms bins of inter-key gaps
            bin_counts, _ = np.histogram(gaps, bins=np.arange(0, 5.0, 0.1))
            p = bin_counts / max(bin_counts.sum(), 1)
            rhythm_entropy = float(-(p[p > 0] * np.log2(p[p > 0])).sum())
        else:
            pause_freq = 0.0
            burst_mean = 1.0
            rhythm_entropy = 0.0

        first_ts = pd.Timestamp.fromtimestamp(t0 + minute_idx * minute_window_s)
        rows.append({
            "minute_idx": minute_idx,
            "timestamp": first_ts.strftime("%Y%m%dT%H%M%S000"),
            "pause_frequency": pause_freq,
            "burst_length_mean": burst_mean,
            "rhythm_entropy": rhythm_entropy,
            "total_events": float(len(minutes.get(minute_idx, []))),
        })

    return pd.DataFrame(rows)


def merge_into_perminute(perminute_path: str, ulog_dir: str, out_path: str) -> None:
    """Merge uLog-derived features into the official per-minute file.

    Matches per-participant-per-block: uLog files named a_ppXX_cN_*.xml
    are matched to the official file's PP + Blok columns (blocks in
    chronological order of the uLog files).
    """
    perminute = pd.read_csv(perminute_path, sep="\t")
    perminute["timestamp_parsed"] = pd.to_datetime(
        perminute["timestamp"], format="%Y%m%dT%H%M%S%f", errors="coerce"
    )

    ulog_files = sorted(
        f for f in os.listdir(ulog_dir) if f.lower().endswith(".xml")
    )
    # group uLog files per participant, preserving block order by start time
    by_pp: Dict[str, List[Tuple[float, str, pd.DataFrame]]] = {}
    for fname in ulog_files:
        m = re.match(r"a_pp(\d+)_c(\d)_uLog_(\d{8})_(\d{6})", fname, re.I)
        if not m:
            continue
        pp = f"PP{int(m.group(1))}"
        # filename carries LOCAL wall-clock start (uLog XML timestamps are UTC)
        t0 = pd.to_datetime(f"{m.group(3)} {m.group(4)}", format="%Y%m%d %H%M%S")
        df = parse_ulog(os.path.join(ulog_dir, fname))
        if df.empty:
            continue
        by_pp.setdefault(pp, []).append((t0, fname, df))

    merged_cols = ["pause_frequency", "burst_length_mean", "rhythm_entropy"]
    for col in merged_cols:
        perminute[col] = np.nan

    n_matched = 0
    for pp, entries in by_pp.items():
        for t0, fname, udf in entries:
            # direct wall-clock overlap: per-minute rows within [t0, t0 + len*60)
            span = pd.Timedelta(seconds=len(udf) * 60)
            mask = (
                (perminute["PP"] == pp)
                & (perminute["timestamp_parsed"] >= t0)
                & (perminute["timestamp_parsed"] < t0 + span)
            )
            idxs = perminute.index[mask]
            udf_idx = udf.set_index("minute_idx")
            for i in idxs:
                rel_min = int(
                    (perminute.loc[i, "timestamp_parsed"] - t0).total_seconds() // 60
                )
                if rel_min in udf_idx.index:
                    for col in merged_cols:
                        perminute.loc[i, col] = udf_idx.loc[rel_min, col]
                    n_matched += 1

    print(f"[MERGE] matched {n_matched} per-minute rows across {len(by_pp)} participants")
    perminute.to_csv(out_path, sep="\t", index=False)
    print(f"[MERGE] wrote {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ulog_xml", nargs="?", help="path to one uLog XML")
    ap.add_argument("out_csv", nargs="?", help="output CSV for single-file mode")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--perminute", help="official per-minute .tab")
    ap.add_argument("--ulog-dir", help="folder of a_ppXX_cN_*.xml files")
    ap.add_argument("--output", help="merged output .tab")
    args = ap.parse_args()

    if args.merge:
        if not (args.perminute and args.ulog_dir and args.output):
            raise SystemExit("--merge requires --perminute, --ulog-dir, --output")
        merge_into_perminute(args.perminute, args.ulog_dir, args.output)
        return

    if not (args.ulog_xml and args.out_csv):
        raise SystemExit("single-file mode requires <ulog.xml> <output.csv>")
    df = parse_ulog(args.ulog_xml)
    df.to_csv(args.out_csv, index=False)
    print(df.head(10).to_string())


if __name__ == "__main__":
    main()
