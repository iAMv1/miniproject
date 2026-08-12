"""MindPulse — Personalized evaluation v2 (clean, from first principles).

Variants (chronological within-subject split: early 70% train, late 30% test):
  V1: per-user model, raw features            (ETH personalized analogue)
  V2: global model, user-z features           (baseline-normalized, shared model)
  V3: per-user model, user-z features         (full personalization)

Metrics per subject: 3-class acc/F1 (reference), BINARY deviation F1,
Spearman rho vs self-reported stress (SWELL Stress column), pooled stats.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, r"C:\Users\ItzP\miniproject\training")
import cloud_train as ct  # noqa: E402
from cloud_train import safe_predict  # noqa: E402

F = ct.FEATURE_NAMES


def user_z(raw: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    z = (raw - mean) / np.maximum(std, 1e-6)
    return np.clip(z, -5, 5).astype(np.float32)


def bin_f1(t, p):
    tb = (np.asarray(t) > 0).astype(int)
    pb = (np.asarray(p) > 0).astype(int)
    tp = ((tb == 1) & (pb == 1)).sum()
    fp = ((tb == 0) & (pb == 1)).sum()
    fn = ((tb == 1) & (pb == 0)).sum()
    return float(2 * tp / max(2 * tp + fp + fn, 1))


def acc3(t, p):
    return float(np.mean(np.asarray(t) == np.asarray(p)))


def run_variant(X, y, s, stress, use_user_z: bool, per_user_model: bool):
    rows = []
    for subj in np.unique(s):
        idx = np.where(s == subj)[0]
        cut = int(len(idx) * 0.7)
        tr, va = idx[:cut], idx[cut:]
        if len(va) < 5 or len(tr) < 10:
            continue
        Xtr, Xva = X[tr], X[va]
        if use_user_z:
            mu = Xtr.mean(axis=0)
            sd = Xtr.std(axis=0)
            Xtr = user_z(Xtr, mu, sd)
            Xva = user_z(Xva, mu, sd)
        if per_user_model:
            model = ct.build_classifier(n_estimators=300, random_seed=42)
            model.fit(Xtr, y[tr])
        else:
            # global model trained on ALL other subjects' data, with THIS
            # subject's early minutes only for baseline stats
            model = ct.build_classifier(n_estimators=300, random_seed=42)
            others = np.where(s != subj)[0]
            model.fit(X[others], y[others])
            if use_user_z:
                # refit on user-z-transformed others
                mu = X[others].mean(axis=0)
                sd = X[others].std(axis=0)
                model = ct.build_classifier(n_estimators=300, random_seed=42)
                model.fit(user_z(X[others], mu, sd), y[others])
                Xva = user_z(Xva, mu, sd)

        yv = y[va]
        pv = safe_predict(model, Xva)
        if len(yv) != len(pv):
            print(f"DEBUG {subj}: len(va)={len(va)} len(Xva)={len(Xva)} "
                  f"len(yv)={len(yv)} len(pv)={len(pv)} "
                  f"len(y)={len(y)} len(X)={len(X)} max(va)={va.max() if len(va) else None} "
                  f"va[:3]={va[:3]} X.shape={X.shape} y.shape={np.shape(y)} "
                  f"s.shape={np.shape(s)} type(y)={type(y)} type(s)={type(s)}")
            raise SystemExit
        score = model.predict_proba(Xva) @ np.array([0, 50, 100.0])
        r = {"subject": subj, "acc3": acc3(yv, pv),
             "bin_f1": bin_f1(yv, pv)}
        m = ~np.isnan(stress[va])
        if m.sum() >= 5:
            rho, p = spearmanr(score[m], stress[va][m])
            r["rho"] = float(rho)
            r["rho_n"] = int(m.sum())
        rows.append(r)
    df = pd.DataFrame(rows)
    out = {"n_subjects": len(df),
           "acc3_mean": round(float(df["acc3"].mean()), 3),
           "acc3_median": round(float(df["acc3"].median()), 3),
           "bin_f1_mean": round(float(df["bin_f1"].mean()), 3)}
    if "rho" in df:
        out["rho_mean"] = round(float(df["rho"].mean()), 3)
        out["rho_median"] = round(float(df["rho"].median()), 3)
    return out


def main():
    X, y, s, _, stress = ct.load_swellkw(
        r"C:\Users\ItzP\miniproject\training\data\Behavioral-features - per minute.tab")
    print(f"SWELL: {X.shape}, subjects {len(np.unique(s))}, "
          f"labels {dict(zip(*np.unique(y, return_counts=True)))}")

    for label, use_z, per_u in [("V1 per-user model, raw feats", False, True),
                                ("V2 global model, user-z feats", True, False),
                                ("V3 per-user model, user-z feats", True, True)]:
        print(f"\n=== {label} ===")
        res = run_variant(X, y, s, stress, use_z, per_u)
        for k, v in res.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

