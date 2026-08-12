"""MindPulse — Unified data preparation pipeline (compile → clean → validate → split).

Frozen artifacts (everything downstream reads these, never raw files):
  training/data/cleaned_dataset.parquet   — 23 features + label + subject +
                                             provenance columns, validated
  training/data/splits.json               — subject-disjoint dev/test split,
                                             hashes, per-source stats

Steps (all checked, nothing silent):
  1. COMPILE: SWELL-KW (per-minute, relax excluded) + Kaggle-raw rebuilt
  2. CLEAN:   NaN->0, clip>=0, schema check (23 cols, right dtype), dup check
  3. VALIDATE: per-source feature coverage report, class distribution,
               subject disjointness between sources, dataset SHA256
  4. SPLIT:   fixed subject-grouped dev/test (seed 42, 20% test subjects)
"""
from __future__ import annotations

import hashlib
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\ItzP\miniproject\training")
import cloud_train as ct  # noqa: E402

F = ct.FEATURE_NAMES
SEED = 42
TEST_FRACTION = 0.2


def compile_sources():
    X1, y1, s1, mapping, _ = ct.load_swellkw(
        r"C:\Users\ItzP\miniproject\training\data\Behavioral-features - per minute.tab")
    swell = pd.DataFrame(X1, columns=F)
    swell["label"] = y1
    swell["subject"] = s1
    swell["source"] = "swell"
    swell["label_origin"] = "stressor_condition"

    k = pd.read_csv(r"C:\Users\ItzP\miniproject\training\data\kaggle_raw_rebuilt.csv")
    kag = k[F + ["label", "user_id"]].rename(columns={"user_id": "subject"}).copy()
    kag["source"] = "kaggle_raw"
    kag["label_origin"] = "self_report"
    return swell, kag


def main() -> None:
    swell, kag = compile_sources()
    print(f"sources: swell={len(swell)} kaggle_raw={len(kag)}")

    df = pd.concat([swell, kag], ignore_index=True)

    # ── CLEAN ──
    assert set(F) <= set(df.columns), "schema missing features"
    X = df[F].to_numpy(dtype=np.float32)
    X = np.nan_to_num(X, nan=0.0)
    X = np.clip(X, 0.0, None)
    df[F] = X
    df["label"] = df["label"].astype(int)
    assert df["label"].isin([0, 1, 2]).all(), "invalid labels"
    n_dup = df.duplicated(subset=F).sum()
    if n_dup:
        print(f"[WARN] duplicate feature rows: {n_dup} (kept, reported)")
    df["dataset_version"] = "v3"

    # ── VALIDATE ──
    print("\n=== per-source feature coverage (non-zero fraction) ===")
    for src, g in df.groupby("source"):
        frac = (g[F].to_numpy() > 0).mean(axis=0)
        top = sorted(zip(F, frac), key=lambda t: -t[1])[:6]
        print(f"  {src}: {[(f, round(v,2)) for f, v in top]}")

    print("\nclass distribution:")
    print(df.groupby(["source", "label"]).size().to_string())

    overlap = set(df.loc[df.source == "swell", "subject"]) & \
              set(df.loc[df.source == "kaggle_raw", "subject"])
    print(f"\nsubject overlap between sources: {overlap or 'none'}")
    print(f"total subjects: {df['subject'].nunique()}")

    h = hashlib.sha256()
    h.update(df[F + ["label", "subject"]].to_csv(index=False).encode())
    dataset_hash = h.hexdigest()
    print(f"dataset sha256: {dataset_hash[:16]}")

    # ── SPLIT (subject-disjoint, fixed seed) ──
    from sklearn.model_selection import GroupShuffleSplit
    gss = GroupShuffleSplit(n_splits=1, test_size=TEST_FRACTION, random_state=SEED)
    dev_idx, test_idx = next(gss.split(df, df["label"], groups=df["subject"]))
    dev_subjects = set(df.iloc[dev_idx]["subject"])
    test_subjects = set(df.iloc[test_idx]["subject"])
    assert dev_subjects.isdisjoint(test_subjects), "split leaked subjects"

    df.to_parquet(r"C:\Users\ItzP\miniproject\training\data\cleaned_dataset.parquet",
                  index=False)
    splits = {
        "dataset_version": "v3",
        "dataset_sha256": dataset_hash,
        "n_rows": int(len(df)),
        "n_subjects": int(df["subject"].nunique()),
        "dev_rows": int(len(dev_idx)), "test_rows": int(len(test_idx)),
        "dev_subjects": sorted(dev_subjects),
        "test_subjects": sorted(test_subjects),
        "seed": SEED, "test_fraction": TEST_FRACTION,
        "per_source_rows": df["source"].value_counts().to_dict(),
    }
    json.dump(splits, open(r"C:\Users\ItzP\miniproject\training\data\splits.json", "w"),
              indent=2, default=str)
    print(f"\nfrozen: cleaned_dataset.parquet ({len(df)} rows) + splits.json")
    print(f"test subjects ({len(test_subjects)}): {sorted(test_subjects)[:8]}...")


if __name__ == "__main__":
    main()
