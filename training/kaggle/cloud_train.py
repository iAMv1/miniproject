"""MindPulse — Cloud training entrypoint (Kaggle / Google Colab).

Trains the production XGBoost model on REAL behavioral data (SWELL-KW
preferred) with subject-independent validation, and emits the exact
artifacts the backend expects:

    model_xgb.joblib          XGBClassifier (3 classes, 23 raw features)
    global_stats.joblib       {"mean": [23], "std": [23]} for DualNormalizer
    artifacts_manifest.json   provenance: dataset hash, split method, metrics
    xgb_model.onnx            (optional) browser model exported from the
                              same trained weights

Standalone: it does NOT import anything from the MindPulse backend.

Usage:
    python cloud_train.py --data "Behavioral-features - per minute.tab" \
        --out artifacts --export-onnx

Dataset adapters
----------------
1) SWELL-KW (recommended, real 25-subject study)
   --data = the official per-minute feature file
   ("Behavioral-features - per minute.tab/.ods/.csv") OR a folder of
   per-condition files named <subject>_<condition>.csv.
   Conditions map: neutral -> 0, interruption -> 1, time_pressure -> 2
   (stressor-condition labels, documented proxy — not clinical stress).
   If your file uses block codes (e.g. "Block 1"), pass --condition-map.

2) MindPulse CSV (existing 23-feature format)
   --data path/to/real_dataset.csv with columns = 23 MindPulse features +
   label (0/1/2) + user_id. Useful for fine-tuning on top of SWELL-KW.

3) Kaggle 2-user dataset (raw rows)
   --data path/to/kaggle_rows.csv + --raw-kaggle: rows have many raw
   keystroke/mouse columns; windows are aggregated here. EXPERIMENTAL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ────────────────────────────────────────────────────────────────
# Must match backend/app/core/config.py FEATURE_NAMES exactly.
# ────────────────────────────────────────────────────────────────
FEATURE_NAMES: List[str] = [
    "hold_time_mean", "hold_time_std", "hold_time_median",
    "flight_time_mean", "flight_time_std", "typing_speed_wpm",
    "error_rate", "pause_frequency", "pause_duration_mean",
    "burst_length_mean", "rhythm_entropy", "mouse_speed_mean",
    "mouse_speed_std", "direction_change_rate", "click_count",
    "rage_click_count", "scroll_velocity_std", "tab_switch_freq",
    "switch_entropy", "session_fragmentation", "hour_of_day",
    "day_of_week", "session_duration_min",
]
NUM_FEATURES = len(FEATURE_NAMES)

LABEL_MAP = {0: "NEUTRAL", 1: "MILD", 2: "STRESSED"}

# ────────────────────────────────────────────────────────────────
# SWELL-KW adapter
# ────────────────────────────────────────────────────────────────

# Official SWELL-KW per-minute feature columns (ICMI 2014 paper, Table 2)
# -> MindPulse feature. Key: substrings matched against lowercased column
# names. Also accepts common mirror names (typing_speed, wpm, ...).
SWELL_COLUMN_MAP: Dict[str, Tuple[List[str], str]] = {
    "click_count": (["leftclick", "left_click", "click"], "click_count"),
    "mouse_speed_mean": (["mousedistance", "cursor_speed", "mouse_speed", "movement_speed"], "mouse_speed_mean"),
    "scroll_velocity_std": (["wheel", "mouse_wheel", "scroll"], "scroll_velocity_std"),
    "error_rate": (["errorkeyratio", "error_key_ratio", "backspace_rate", "error"], "error_rate"),
    "tab_switch_freq": (["tabfocuschange", "tab_focus", "tab_switch"], "tab_switch_freq"),
    "switch_entropy": (["appchange", "app_changes", "switch"], "switch_entropy"),
    "flight_time_mean": (["inter_key_delay", "interkey", "key_latency", "flight"], "flight_time_mean"),
    "flight_time_std": (["delay_sd", "inter_key_delay_sd", "interkey_sd"], "flight_time_std"),
    "pause_frequency": (["pause", "idle_proportion"], "pause_frequency"),
    "direction_change_rate": (["directionkeys", "direction"], "direction_change_rate"),
    "mouse_activity": (["mouseact", "mouseactivity", "mouse_activity"], "mouse_activity"),
    "keystrokes": (["keystrokes", "key_strokes", "keyevents"], "keystrokes"),
    "characters": (["chars", "characters"], "characters"),
    "typing_speed_wpm": (["typing_speed", "words_per_minute", "wpm"], "typing_speed_wpm"),
    "timestamp": (["timestamp", "time", "date"], "timestamp"),
}

CONDITION_LABEL = {
    "neutral": 0,
    "interruption": 1,
    "time_pressure": 2,
}
CONDITION_ALIASES = {
    "n": "neutral", "neutral": "neutral",
    "i": "interruption", "interruption": "interruption", "email": "interruption",
    "t": "time_pressure", "time_pressure": "time_pressure", "tp": "time_pressure",
    "pressure": "time_pressure",
    "r": "relax", "relax": "relax",
}


def _norm_col(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", str(name).lower().strip())


def _find_column(df: pd.DataFrame, needles: List[str]) -> Optional[str]:
    norm = {_norm_col(c): c for c in df.columns}
    for needle in needles:
        n = _norm_col(needle)
        if n in norm:
            return norm[n]
        for norm_name, orig in norm.items():
            if n in norm_name:
                return orig
    return None


def _identify_column(df: pd.DataFrame, *needle_groups: List[str]) -> Optional[str]:
    """Find the first column matching any needle in any group (loose)."""
    for group in needle_groups:
        col = _find_column(df, group)
        if col is not None:
            return col
    return None


def _infer_condition(value) -> Optional[int]:
    """Map a condition cell value (string or int) to a label 0/1/2.
    Returns -1 for the relax phase (excluded from training), None for
    unmappable values."""
    s = str(value).strip().lower()
    if not s or s in ("nan", "none", "-"):
        return None
    if s.isdigit():
        # SWELL blocks are counterbalanced; code 1/2/3 is NOT fixed to a
        # condition. Only map when explicitly confirmed via --condition-map.
        return None
    for alias, canon in sorted(CONDITION_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if alias in s:
            if canon == "relax":
                return -1
            return CONDITION_LABEL[canon]
    return None


def load_swellkw(path: str, condition_map: Optional[dict] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray, dict, Optional[np.ndarray]]:
    """Load SWELL-KW per-minute features.

    Accepts either:
      A) a single file (CSV/TSV/ODS/XLSX) — the official
         "Behavioral-features - per minute.tab": all participants, with a
         participant column and a condition column;
      B) a folder of per-condition files named <subject>_<condition>.csv.
    Returns (X, y, subjects, mapping_report, stress_values_or_None).
    """
    if os.path.isdir(path):
        return _load_swellkw_folder(path, condition_map)
    return _load_swellkw_file(path, condition_map)


def _load_swellkw_file(path: str, condition_map: Optional[dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    if path.lower().endswith((".xlsx", ".ods")):
        df = pd.read_excel(path)
    elif path.lower().endswith(".tab"):
        df = pd.read_csv(path, sep="\t")
    else:
        df = pd.read_csv(path)

    subject_col = _identify_column(
        df,
        ["participant", "subject", "pp", "user", "id", "person"],
        ["participant_id", "subject_id"],
    )
    cond_col = _identify_column(
        df,
        ["condition", "block", "stressor", "c", "type"],
        ["condition_type"],
    )
    if cond_col is None:
        raise SystemExit(
            f"Could not find a condition column in {path}. "
            f"Available columns: {list(df.columns)}"
        )

    condition_values = df[cond_col].astype(str).unique()
    labels = []
    unknown = set()
    n_relax = 0
    keep = []
    for i, v in enumerate(df[cond_col]):
        mapped = _infer_condition(v)
        if mapped == -1:
            n_relax += 1
            labels.append(-1)
            continue
        if mapped is None:
            if condition_map and str(v).strip() in condition_map:
                mapped = condition_map[str(v).strip()]
            else:
                unknown.add(str(v))
                mapped = 0  # placeholder, filtered out below
        labels.append(mapped)
        keep.append(i)
    if unknown:
        raise SystemExit(
            f"Cannot map condition values {sorted(unknown)} to labels. "
            f"Expected values containing neutral/interruption/time_pressure "
            f"(or block codes). Pass --condition-map 'value:label,...' to map them, "
            f"e.g. --condition-map 'Block 1:0,Block 2:1,Block 3:2'. "
            f"All distinct values seen: {sorted(condition_values)}"
        )
    if n_relax:
        print(f"[INFO] Excluding {n_relax} relax-phase rows (not part of the 3-class protocol).")

    df = df.iloc[keep].reset_index(drop=True)
    labels = [labels[i] for i in keep]

    X, y, subjects, mapping = _build_matrix(df, labels, subject_col)
    if subject_col is None:
        raise SystemExit(
            "No participant/subject column found — subject-independent "
            "validation is impossible. Refusing to proceed with random splits."
        )
    stress = None
    if "Stress" in df.columns:
        stress = pd.to_numeric(df["Stress"], errors="coerce").to_numpy(dtype=np.float64)
    return X, y, subjects, mapping, stress


def _load_swellkw_folder(folder: str, condition_map: Optional[dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    rows: List[pd.DataFrame] = []
    subjects: List[str] = []
    labels: List[int] = []

    files = sorted(
        f for f in os.listdir(folder)
        if f.lower().endswith((".csv", ".xlsx", ".ods", ".tab")) and not f.startswith("~")
    )
    if not files:
        raise SystemExit(f"No CSV/XLSX/ODS found in {folder}")

    for fname in files:
        stem = os.path.splitext(fname)[0].lower()
        cond = None
        for alias, canon in CONDITION_ALIASES.items():
            if re.search(rf"(^|_){alias}(_|$)", stem):
                cond = canon
                break
        if cond is None:
            print(f"[SKIP] {fname}: cannot infer condition "
                  f"(expected neutral/interruption/time_pressure in filename)")
            continue
        path = os.path.join(folder, fname)
        if fname.lower().endswith((".xlsx", ".ods")):
            df = pd.read_excel(path)
        elif fname.lower().endswith(".tab"):
            df = pd.read_csv(path, sep="\t")
        else:
            df = pd.read_csv(path)
        if df.empty:
            continue

        subject = re.sub(rf"(_|^){cond}($|_)", "_", stem).strip("_") or stem
        rows.append(df)
        subjects.extend([subject] * len(df))
        labels.extend([CONDITION_LABEL[cond]] * len(df))
        print(f"[LOAD] {fname}: {len(df)} minutes, subject={subject}, "
              f"condition={cond} -> label={CONDITION_LABEL[cond]}")

    if not rows:
        raise SystemExit("No files with recognizable conditions. "
                         "Rename files to <subject>_<neutral|interruption|time_pressure>.csv")

    raw = pd.concat(rows, ignore_index=True)
    minute_counter = np.concatenate([
        np.arange(len(r), dtype=np.int64) for r in rows
    ])
    X, y, _, mapping = _build_matrix(raw, labels, None, minute_counter=minute_counter)
    return X, y, np.asarray(subjects), mapping, None


def _build_matrix(df: pd.DataFrame, labels: List[int], subject_col: Optional[str],
                  minute_counter: Optional[np.ndarray] = None,
                  ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Build the 23-feature matrix from SWELL-KW columns. Returns X, y, subjects, mapping."""
    mapping_report: Dict[str, Optional[str]] = {}
    for mp_feat, (needles, _) in SWELL_COLUMN_MAP.items():
        mapping_report[mp_feat] = _find_column(df, needles)

    X = np.zeros((len(df), NUM_FEATURES), dtype=np.float32)

    def put(mp_feat: str, values) -> None:
        X[:, FEATURE_NAMES.index(mp_feat)] = np.asarray(values, dtype=np.float32)

    col = mapping_report["typing_speed_wpm"]
    if col and col in df.columns:
        put("typing_speed_wpm", df[col])
    # Official file has no WPM column: derive from Characters per minute
    # (English ~5 chars/word).
    elif mapping_report["characters"]:
        put("typing_speed_wpm", df[mapping_report["characters"]] / 5.0)
        mapping_report["typing_speed_wpm"] = "derived: characters/5"

    for mp_feat in ["click_count", "scroll_velocity_std",
                    "error_rate", "tab_switch_freq", "switch_entropy",
                    "flight_time_mean", "flight_time_std", "pause_frequency",
                    "direction_change_rate"]:
        col = mapping_report[mp_feat]
        if col and col in df.columns:
            put(mp_feat, df[col])

    # Mouse distance (SWELL: pixels per minute) -> pixels per second
    if mapping_report["mouse_speed_mean"]:
        col = mapping_report["mouse_speed_mean"]
        values = df[col]
        if "mousedistance" in _norm_col(col):
            values = values / 60.0
            mapping_report["mouse_speed_mean"] += " (px/min -> px/s)"
        put("mouse_speed_mean", values)

    # rage clicks: official file only counts left clicks vs all mouse activity
    if mapping_report["mouse_activity"] and mapping_report["click_count"]:
        wheel = (df[mapping_report["scroll_velocity_std"]]
                 if mapping_report["scroll_velocity_std"] else 0)
        put("rage_click_count",
            (df[mapping_report["mouse_activity"]]
             - df[mapping_report["click_count"]] - wheel).clip(lower=0.0))
        mapping_report["rage_click_count"] = "derived: mouse_activity-leftclicks-wheel"

    # session_duration_min: minute index within each participant's block
    if minute_counter is not None:
        put("session_duration_min", minute_counter)
    elif subject_col:
        put("session_duration_min", df.groupby(subject_col).cumcount())

    # hour_of_day / day_of_week from timestamp column (SWELL format: 20120918T131600000)
    ts_col = mapping_report.get("timestamp")
    if ts_col and ts_col in df.columns:
        try:
            ts = pd.to_datetime(
                df[ts_col], format="%Y%m%dT%H%M%S%f", errors="coerce"
            )
            if ts.isna().all():
                ts = pd.to_datetime(df[ts_col], errors="coerce")
            if ts.notna().any():
                put("hour_of_day", ts.dt.hour.fillna(0))
                put("day_of_week", ts.dt.dayofweek.fillna(0))
                mapping_report["hour_of_day"] = ts_col
                mapping_report["day_of_week"] = ts_col
        except Exception as e:
            print(f"[WARN] timestamp parse failed ({e}); hour/day left zero")

    X = np.clip(np.nan_to_num(X, nan=0.0), 0.0, None)
    y = np.asarray(labels, dtype=np.int32)
    subjects_arr = df[subject_col].astype(str).to_numpy() if subject_col else None
    return X, y, subjects_arr, mapping_report


def load_mindpulse_csv(path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    df = pd.read_csv(path)
    missing = [c for c in FEATURE_NAMES if c not in df.columns]
    if missing:
        raise SystemExit(f"MindPulse CSV missing features: {missing}")
    X = df[FEATURE_NAMES].to_numpy(dtype=np.float32)
    y = df["label"].to_numpy(dtype=np.int32)
    subjects = df["user_id"].astype(str).to_numpy() if "user_id" in df.columns else None
    return X, y, subjects


# ────────────────────────────────────────────────────────────────
# Stats + training
# ────────────────────────────────────────────────────────────────

def compute_global_stats(X: np.ndarray) -> dict:
    """Compute global mean/std for z-score normalization, plus
    distribution-aware inference guards:
      - zero_variance_mask: features that were constant (0) during training;
        client values on them are out-of-distribution -> forced to 0 at inference
      - clip_min / clip_max: per-feature 1st/99th percentiles of training data;
        inference inputs are clipped to this range."""
    return {
        "mean": np.mean(X, axis=0).astype(np.float32),
        "std": np.std(X, axis=0).astype(np.float32),
        "zero_variance_mask": (np.std(X, axis=0) == 0).astype(np.float32),
        "clip_min": np.percentile(X, 1, axis=0).astype(np.float32),
        "clip_max": np.percentile(X, 99, axis=0).astype(np.float32),
    }


def tune_hyperparameters(X, y, subjects, n_iter: int = 15, inner_folds: int = 5,
                         random_seed: int = 42) -> dict:
    """Hyperparameter tuning with inner GroupKFold CV (subject-aware).

    NOTE: tuning uses all subjects (inner CV); the final LOOCV with the
    tuned parameters is the honest estimate. Mild optimism possible — the
    manifest records the tuning procedure.
    """
    from sklearn.model_selection import GroupKFold, RandomizedSearchCV
    import xgboost as xgb

    base = xgb.XGBClassifier(
        objective="multi:softprob", num_class=3, max_depth=5,
        learning_rate=0.05, n_estimators=250, subsample=0.85,
        colsample_bytree=0.85, min_child_weight=5, gamma=0.1,
        reg_alpha=0.05, reg_lambda=1.5, eval_metric="mlogloss",
        random_state=random_seed, tree_method="hist",
    )
    space = {
        "max_depth": [3, 5, 7, 9],
        "learning_rate": [0.01, 0.03, 0.05, 0.1],
        "n_estimators": [150, 250, 400],
        "subsample": [0.7, 0.85, 1.0],
        "colsample_bytree": [0.6, 0.8, 1.0],
        "min_child_weight": [1, 5, 10],
        "gamma": [0.0, 0.1, 0.3],
        "reg_alpha": [0.0, 0.05, 0.5],
        "reg_lambda": [0.5, 1.5, 4.0],
    }
    gkf = GroupKFold(n_splits=inner_folds)
    search = RandomizedSearchCV(
        base, space, n_iter=n_iter, cv=gkf, scoring="f1_macro",
        random_state=random_seed, n_jobs=-1, verbose=0,
    )
    search.fit(X, y, groups=subjects)
    best = {k: v for k, v in search.best_params_.items()}
    print(f"[TUNE] best params: {best}")
    print(f"[TUNE] inner CV f1_macro: {search.best_score_:.4f}")
    return best


def build_classifier(params: Optional[dict] = None, n_estimators: int = 500,
                     random_seed: int = 42) -> "xgb.XGBClassifier":
    import xgboost as xgb
    defaults = dict(
        objective="multi:softprob", num_class=3, max_depth=5,
        learning_rate=0.05, n_estimators=n_estimators, subsample=0.85,
        colsample_bytree=0.85, min_child_weight=5, gamma=0.1,
        reg_alpha=0.05, reg_lambda=1.5, eval_metric="mlogloss",
        random_state=random_seed, tree_method="hist",
    )
    if params:
        defaults.update(params)
    return xgb.XGBClassifier(**defaults)


def loocv_evaluate(X, y, subjects, repeats: int = 1, random_seed: int = 42,
                   chronological: bool = False,
                   model_params: Optional[dict] = None) -> dict:
    """Leave-one-subject-out cross-validation with honest metrics.

    repeats > 1: repeated LOOCV with different model seeds -> mean/std over
    repeats (confidence intervals). chronological: within each held-out
    subject, train on that subject's earlier minutes and test on later ones
    (personalized evaluation), pooled with the cross-subject results.
    """
    from sklearn.metrics import (
        accuracy_score, classification_report, confusion_matrix, f1_score,
        precision_score, recall_score,
    )
    import xgboost as xgb

    unique = np.unique(subjects)
    all_fold_scores: Dict[str, list] = {
        "accuracy": [], "f1_macro": [], "precision_macro": [], "recall_macro": [],
    }
    y_true_all, y_pred_all, fold_rows = [], [], []

    for rep in range(repeats):
        seed = random_seed + rep
        for held in unique:
            tr_mask = subjects != held
            va_mask = subjects == held
            model = build_classifier(model_params, n_estimators=400, random_seed=seed)
            X_tr, y_tr = X[tr_mask], y[tr_mask]
            X_va, y_va = X[va_mask], y[va_mask]

            if chronological:
                # per-subject chronological split: earlier 70% -> train, later 30% -> test
                for s in np.unique(subjects[va_mask]):
                    s_idx = np.where(subjects == s)[0]
                    cut = int(len(s_idx) * 0.7)
                    X_tr = np.concatenate([X_tr, X[s_idx[:cut]]])
                    y_tr = np.concatenate([y_tr, y[s_idx[:cut]]])
                    X_va = X[s_idx[cut:]]
                    y_va = y[s_idx[cut:]]
                    if len(y_va) == 0:
                        continue
                    model.fit(X_tr, y_tr)
                    y_true_all.extend(y_va.tolist())
                    y_pred_all.extend(model.predict(X_va).tolist())
                    for k in all_fold_scores:
                        fn = {"accuracy": accuracy_score, "f1_macro": f1_score,
                              "precision_macro": precision_score,
                              "recall_macro": recall_score}[k]
                        kw = {"average": "macro", "zero_division": 0.0} if k != "accuracy" else {}
                        all_fold_scores[k].append(fn(y_va, model.predict(X_va), **kw))
                    fold_rows.append({
                        "held_out_subject": str(s),
                        "split": "chronological_within_subject",
                        "macro_f1": float(f1_score(y_va, model.predict(X_va),
                                                   average="macro", zero_division=0.0)),
                    })
                continue

            model.fit(X_tr, y_tr)
            y_pred = model.predict(X_va)
            y_true_all.extend(y_va.tolist())
            y_pred_all.extend(y_pred.tolist())
            for k in all_fold_scores:
                fn = {"accuracy": accuracy_score, "f1_macro": f1_score,
                      "precision_macro": precision_score,
                      "recall_macro": recall_score}[k]
                kw = {"average": "macro", "zero_division": 0.0} if k != "accuracy" else {}
                all_fold_scores[k].append(fn(y_va, y_pred, **kw))
            fold_rows.append({
                "held_out_subject": str(held),
                "split": "subject_independent" if not chronological else "chronological",
                "macro_f1": float(f1_score(y_va, y_pred, average="macro", zero_division=0.0)),
            })

    yt, yp = np.asarray(y_true_all), np.asarray(y_pred_all)
    metrics = {
        "split_method": "leave_one_subject_out"
                        + ("_chronological" if chronological else "")
                        + (f"_repeated_{repeats}" if repeats > 1 else ""),
        "repeats": repeats,
        "n_subjects": int(len(unique)),
        "accuracy": float(accuracy_score(yt, yp)),
        "f1_macro": float(f1_score(yt, yp, average="macro", zero_division=0.0)),
        "precision_macro": float(precision_score(yt, yp, average="macro", zero_division=0.0)),
        "recall_macro": float(recall_score(yt, yp, average="macro", zero_division=0.0)),
        "confusion_matrix": confusion_matrix(yt, yp, labels=[0, 1, 2]).tolist(),
        "classification_report": classification_report(
            yt, yp, labels=[0, 1, 2], target_names=list(LABEL_MAP.values()),
            zero_division=0.0,
        ),
        "fold_metrics": fold_rows,
        "n_validation": int(len(yt)),
    }
    if repeats > 1:
        mean_ci = {k: (float(np.mean(v)), float(np.std(v))) for k, v in all_fold_scores.items()}
        metrics["mean_std_across_repeats"] = {
            k: {"mean": round(v[0], 4), "std": round(v[1], 4)} for k, v in mean_ci.items()
        }
    return metrics


def stress_correlation_evaluate(X, y, subjects, stress_values, model=None) -> dict:
    """ETH-style evaluation: Spearman rho between predicted score and
    self-reported stress (0-10), per subject and pooled.
    Uses the subject-independent folds; predictions come from LOOCV.
    """
    from scipy.stats import spearmanr
    import xgboost as xgb

    unique = np.unique(subjects)
    per_subject_rho = []
    all_pred, all_true = [], []
    for held in unique:
        tr_mask = subjects != held
        va_mask = subjects == held
        if stress_values is None or np.isnan(stress_values[va_mask]).all():
            continue
        m = model if model is not None else build_classifier(
            n_estimators=400, random_seed=42)
        if model is None:
            m.fit(X[tr_mask], y[tr_mask])
        proba = m.predict_proba(X[va_mask]) if model is None else m.predict_proba(X[va_mask])
        score = np.sum(proba * np.array([0, 50, 100]), axis=1)
        mask = ~np.isnan(stress_values[va_mask])
        if mask.sum() > 5:
            rho, p = spearmanr(score[mask], stress_values[va_mask][mask])
            per_subject_rho.append({"subject": str(held), "spearman_rho": float(rho),
                                    "p_value": float(p), "n": int(mask.sum())})
            all_pred.extend(score[mask].tolist())
            all_true.extend(stress_values[va_mask][mask].tolist())

    pooled = {}
    if all_pred:
        rho, p = spearmanr(all_pred, all_true)
        pooled = {"pooled_spearman_rho": float(rho), "p_value": float(p),
                  "n": len(all_pred)}
    return {
        "metric": "spearman_rho_predicted_score_vs_selfreported_stress",
        "per_subject": per_subject_rho,
        "pooled": pooled,
        "note": "ETH Zurich 2025 comparable: one-fits-all rho=0.078, personalised 0.188-0.296",
    }


def train_final_model(X, y, params: Optional[dict] = None) -> "xgb.XGBClassifier":
    model = build_classifier(params, n_estimators=500, random_seed=42)
    model.fit(X, y)
    return model


def export_onnx(model, out_dir: str) -> Optional[str]:
    try:
        import onnxmltools
        from onnxmltools.convert.common.data_types import FloatTensorType
        import onnx

        onnx_model = onnxmltools.convert_xgboost(
            model, initial_types=[("float_input", FloatTensorType([None, NUM_FEATURES]))],
            target_opset=15,
        )
        path = os.path.join(out_dir, "xgb_model.onnx")
        onnx.save_model(onnx_model, path)
        return path
    except Exception as e:
        print(f"[WARN] ONNX export skipped: {e}")
        return None


def write_manifest(out_dir: str, *, dataset_hash: str, dataset_desc: str,
                   mapping: dict, metrics: dict, onnx_path: Optional[str],
                   git_commit: Optional[str]) -> None:
    manifest = {
        "model_id": f"mindpulse-xgb-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "trained_on": "REAL behavioral data (SWELL-KW) with subject-independent validation",
        "dataset_sha256": dataset_hash,
        "dataset_desc": dataset_desc,
        "feature_schema_version": "23-raw-v1",
        "feature_mapping": mapping,
        "metrics_validation": metrics,
        "exported_onnx": onnx_path is not None,
        "training_commit": git_commit,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "labels": LABEL_MAP,
        "note": (
            "SWELL-KW labels are stressor-condition proxies (neutral/interruption/"
            "time_pressure -> 0/1/2), NOT clinical stress levels. Metrics are "
            "subject-independent (LOOCV)."
        ),
    }
    with open(os.path.join(out_dir, "artifacts_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)


def git_commit_of_repo() -> Optional[str]:
    try:
        import subprocess
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip() or None
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True, help="SWELL-KW features file (.tab/.csv/.ods/.xlsx) or folder")
    ap.add_argument("--out", default="artifacts_out", help="output dir for model artifacts")
    ap.add_argument("--export-onnx", action="store_true", help="also export browser ONNX model")
    ap.add_argument("--extra-csv", help="optional MindPulse-format CSV appended to training set")
    ap.add_argument("--condition-map", default="",
                    help="map raw condition values to labels, e.g. 'Block 1:0,Block 2:1,Block 3:2'")
    ap.add_argument("--repeats", type=int, default=1,
                    help="repeat LOOCV N times with different seeds (mean/std reported)")
    ap.add_argument("--chronological", action="store_true",
                    help="within held-out subject: train on earlier 70% minutes, test on later 30%")
    ap.add_argument("--stress-correlation", action="store_true",
                    help="also evaluate Spearman rho of predicted score vs self-reported Stress column")
    ap.add_argument("--tune", action="store_true",
                    help="tune hyperparameters with inner GroupKFold CV before LOOCV")
    args = ap.parse_args()

    condition_map = {}
    for pair in args.condition_map.split(","):
        if not pair.strip():
            continue
        if ":" not in pair:
            raise SystemExit(f"--condition-map entries must be 'value:label', got '{pair}'")
        value, label = pair.split(":", 1)
        condition_map[value.strip()] = int(label.strip())

    os.makedirs(args.out, exist_ok=True)
    git_commit = git_commit_of_repo()

    if os.path.isdir(args.data) or args.data.lower().endswith(
            (".tab", ".csv", ".xlsx", ".ods")):
        X, y, subjects, mapping, stress = load_swellkw(args.data, condition_map)
        dataset_desc = f"SWELL-KW per-minute features from {args.data}"
    else:
        X, y, subjects = load_mindpulse_csv(args.data)
        stress = None
        mapping = {"adapter": "mindpulse_csv_23_features"}
        dataset_desc = f"MindPulse-format CSV {os.path.basename(args.data)}"

    if subjects is None:
        raise SystemExit("Dataset has no subject column (user_id / filename). "
                         "Subject-independent validation is impossible — aborting. "
                         "Never train with random-row splits on behavioral data.")

    with open(args.data if os.path.isfile(args.data) else __file__, "rb") as f:
        dataset_hash = hashlib.sha256(f.read()).hexdigest()[:16]
    if os.path.isdir(args.data):
        h = hashlib.sha256()
        for fname in sorted(os.listdir(args.data)):
            with open(os.path.join(args.data, fname), "rb") as f:
                h.update(f.read())
        dataset_hash = h.hexdigest()[:16]

    if args.extra_csv:
        X2, y2, s2 = load_mindpulse_csv(args.extra_csv)
        if s2 is None:
            raise SystemExit("--extra-csv must contain a user_id column")
        X = np.concatenate([X, X2])
        y = np.concatenate([y, y2])
        subjects = np.concatenate([subjects, s2])
        dataset_desc += f" + {os.path.basename(args.extra_csv)}"

    dist = pd.DataFrame({"label": y, "subject": subjects}).groupby("label").size()
    print("\nClass distribution (label: rows)")
    print(dist.to_string())
    print(f"Subjects: {len(np.unique(subjects))}")

    tuned_params = None
    if args.tune:
        print("\n===== STEP 1: HYPERPARAMETER TUNING (inner GroupKFold CV) =====")
        tuned_params = tune_hyperparameters(X, y, subjects)

    metrics = loocv_evaluate(X, y, subjects, repeats=args.repeats,
                             chronological=args.chronological,
                             model_params=tuned_params)
    print("\n===== LOOCV METRICS (subject-independent) =====")
    print(f"accuracy={metrics['accuracy']:.4f}  f1_macro={metrics['f1_macro']:.4f}  "
          f"precision={metrics['precision_macro']:.4f}  recall={metrics['recall_macro']:.4f}")
    if "mean_std_across_repeats" in metrics:
        print("across repeats (mean, std):",
              {k: v for k, v in metrics["mean_std_across_repeats"].items()})
    print(metrics["classification_report"])

    if args.stress_correlation and stress is not None:
        corr = stress_correlation_evaluate(X, y, subjects, stress)
        print("\n===== STRESS CORRELATION (self-report, ETH-style) =====")
        print(json.dumps(corr["pooled"], indent=1))
        print("per-subject rho mean:",
              round(float(np.mean([s["spearman_rho"] for s in corr["per_subject"]])), 4))
        metrics["stress_correlation"] = corr

    model = train_final_model(X, y, tuned_params)
    if tuned_params:
        metrics["tuned_hyperparameters"] = tuned_params

    import joblib
    joblib.dump(model, os.path.join(args.out, "model_xgb.joblib"))
    joblib.dump(compute_global_stats(X), os.path.join(args.out, "global_stats.joblib"))

    onnx_path = export_onnx(model, args.out) if args.export_onnx else None
    write_manifest(args.out, dataset_hash=dataset_hash, dataset_desc=dataset_desc,
                   mapping=mapping, metrics=metrics, onnx_path=onnx_path,
                   git_commit=git_commit)

    print(f"\nArtifacts written to {os.path.abspath(args.out)}:")
    for fname in sorted(os.listdir(args.out)):
        print("  -", fname)


if __name__ == "__main__":
    main()
