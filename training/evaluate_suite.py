"""MindPulse — Senior-grade model evaluation suite.

Protocol (no leakage, reproducible):
  1. FIXED subject-grouped split: 20% of subjects held out as FINAL TEST.
     Never touched during development. Seed fixed: 42.
  2. Development: repeated GroupKFold CV on the remaining 80% subjects.
  3. Models compared on dev (macro-F1): majority baseline, logistic
     regression, random forest, XGBoost default, XGBoost tuned, tuned +
     isotonic calibration (fit on dev fold only).
  4. Best model (dev macro-F1) -> retrained on all dev subjects -> FINAL
     TEST evaluation (single honest run).
  5. Diagnostics on test: per-class report, confusion matrix, binary
     stress-vs-not variant, calibration (ECE), permutation feature
     importance, error-case analysis.
"""

from __future__ import annotations

import json
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\ItzP\miniproject\training")
import cloud_train as ct  # noqa: E402

from sklearn.calibration import CalibratedClassifierCV  # noqa: E402
from sklearn.dummy import DummyClassifier  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score, brier_score_loss, classification_report, confusion_matrix,
    f1_score, precision_score, recall_score,
)
from sklearn.model_selection import GroupKFold, GroupShuffleSplit  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402

SEED = 42
TEST_SUBJECT_FRACTION = 0.2
DEV_FOLDS = 5


def load_all():
    X1, y1, s1, _, _ = ct.load_swellkw(
        r"C:\Users\ItzP\miniproject\training\data\Behavioral-features - per minute.tab")
    k = pd.read_csv(r"C:\Users\ItzP\miniproject\training\data\kaggle_raw_rebuilt.csv")
    F = ct.FEATURE_NAMES
    X2, y2, s2 = (k[F].to_numpy(np.float32), k["label"].to_numpy(np.int32),
                  k["user_id"].astype(str).to_numpy())
    return (np.concatenate([X1, X2]), np.concatenate([y1, y2]),
            np.concatenate([s1, s2]))


def make_models(tuned_params):
    return {
        "majority": DummyClassifier(strategy="most_frequent"),
        "logistic": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "random_forest": RandomForestClassifier(n_estimators=400, random_state=SEED,
                                                n_jobs=-1),
        "xgb_default": ct.build_classifier(n_estimators=400, random_seed=SEED),
        "xgb_tuned": ct.build_classifier(tuned_params, n_estimators=400, random_seed=SEED),
        "xgb_tuned_calibrated": CalibratedClassifierCV(
            ct.build_classifier(tuned_params, n_estimators=400, random_seed=SEED),
            method="isotonic", cv=3),
    }


def evaluate(y_true, y_pred):
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_neutral": float(f1_score(y_true, y_pred, labels=[0], average=None, zero_division=0)),
        "f1_mild": float(f1_score(y_true, y_pred, labels=[1], average=None, zero_division=0)),
        "f1_stressed": float(f1_score(y_true, y_pred, labels=[2], average=None, zero_division=0)),
    }


def binary_eval(y_true, y_pred):
    stress_true = (y_true > 0).astype(int)
    stress_pred = (y_pred > 0).astype(int)
    return {
        "binary_accuracy": float(accuracy_score(stress_true, stress_pred)),
        "binary_f1": float(f1_score(stress_true, stress_pred, zero_division=0)),
        "binary_macro_f1": float(f1_score(stress_true, stress_pred, average="macro")),
    }


def ece(y_true, proba, n_bins=10):
    """Expected Calibration Error on the predicted class."""
    conf = proba.max(axis=1)
    correct = (proba.argmax(1) == y_true).astype(float)
    bin_edges = np.linspace(0, 1, n_bins + 1)
    e = 0.0
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
        m = (conf >= lo) & (conf < hi)
        if m.sum() == 0:
            continue
        e += (m.sum() / len(y_true)) * abs(conf[m].mean() - correct[m].mean())
    return float(e)


def main() -> None:
    X, y, s = load_all()
    print(f"data: {X.shape}, subjects: {len(np.unique(s))}, "
          f"classes: {dict(zip(*np.unique(y, return_counts=True)))}")

    # ── 1. FIXED held-out test split (subjects, never touched until the end) ──
    gss = GroupShuffleSplit(n_splits=1, test_size=TEST_SUBJECT_FRACTION,
                            random_state=SEED)
    dev_idx, test_idx = next(gss.split(X, y, groups=s))
    test_subjects = set(np.unique(s[test_idx]))
    print(f"TEST subjects ({len(test_subjects)}): {sorted(test_subjects)}")
    X_dev, y_dev, s_dev = X[dev_idx], y[dev_idx], s[dev_idx]
    X_test, y_test, s_test = X[test_idx], y[test_idx], s[test_idx]

    # ── 2. tuned params from DEV subjects only (inner GroupKFold) ──
    t0 = time.time()
    tuned = ct.tune_hyperparameters(X_dev, y_dev, s_dev, n_iter=20, inner_folds=5)
    print(f"[tune] {time.time()-t0:.0f}s -> {tuned}")

    # ── 3. development leaderboard (GroupKFold on dev subjects) ──
    gkf = GroupKFold(n_splits=DEV_FOLDS)
    models = make_models(tuned)
    leaderboard = {}
    for name, model in models.items():
        scores = []
        for tr, va in gkf.split(X_dev, y_dev, groups=s_dev):
            model.fit(X_dev[tr], y_dev[tr])
            p = model.predict(X_dev[va])
            scores.append(evaluate(y_dev[va], p))
        avg = {k: float(np.mean([sc[k] for sc in scores])) for k in scores[0]}
        leaderboard[name] = avg
        print(f"[dev] {name:22s} macro_f1={avg['macro_f1']:.4f} "
              f"acc={avg['accuracy']:.4f}")

    best_name = max(leaderboard, key=lambda n: leaderboard[n]["macro_f1"])
    print(f"\nbest (dev macro_f1): {best_name}")

    # ── 4. final test evaluation (single honest run) ──
    best = models[best_name]
    best.fit(X_dev, y_dev)
    y_pred = best.predict(X_test)
    metrics = evaluate(y_test, y_pred)
    metrics.update(binary_eval(y_test, y_pred))
    if hasattr(best, "predict_proba"):
        metrics["ece"] = ece(y_test, best.predict_proba(X_test))
    print(f"\n=== FINAL TEST ({len(X_test)} rows, subjects unseen in dev) ===")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    print(classification_report(y_test, y_pred,
                                target_names=["NEUTRAL", "MILD", "STRESSED"],
                                zero_division=0))
    print("confusion_matrix:", confusion_matrix(y_test, y_pred, labels=[0, 1, 2]).tolist())

    # ── 5. permutation feature importance (test set) ──
    if hasattr(best, "predict"):
        imp = permutation_importance(best, X_test, y_test, n_repeats=5,
                                     scoring="f1_macro", random_state=SEED, n_jobs=-1)
        order = np.argsort(imp.importances_mean)[::-1]
        print("\n=== feature importance (top 10, permutation) ===")
        for i in order[:10]:
            print(f"  {ct.FEATURE_NAMES[i]:24s} {imp.importances_mean[i]:+.4f}")

    # ── 6. error analysis: which features separate MILD from STRESSED errors ──
    err_m = (y_test == 1) & (y_pred == 2)
    err_s = (y_test == 2) & (y_pred == 1)
    if err_m.sum() or err_s.sum():
        print("\n=== error analysis: MILD->STRESSED vs STRESSED->MILD ===")
        for f in ["typing_speed_wpm", "error_rate", "pause_frequency",
                  "tab_switch_freq", "mouse_speed_mean"]:
            i = ct.FEATURE_NAMES.index(f)
            print(f"  {f:20s} M->S mean {X_test[err_m, i].mean():.2f} | "
                  f"S->M mean {X_test[err_s, i].mean():.2f} | "
                  f"all mean {X_test[:, i].mean():.2f}")

    report = {"leaderboard_dev": leaderboard, "best_model": best_name,
              "test_subjects": sorted(test_subjects), "final_test": metrics,
              "confusion_matrix": confusion_matrix(y_test, y_pred, labels=[0, 1, 2]).tolist(),
              "tuned_params": tuned}
    json.dump(report, open(r"C:\Users\ItzP\miniproject\training\data\model_report.json", "w"),
              indent=2, default=str)
    print("\nsaved: training/data/model_report.json")


if __name__ == "__main__":
    main()
