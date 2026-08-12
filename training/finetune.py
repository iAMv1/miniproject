"""MindPulse — Fine-tuning stage: typing-encoder embeddings + engineered features.

Combines:
  (a) 23 engineered per-minute features (SWELL-KW + rebuilt Kaggle raw)
  (b) typing-encoder embeddings for windows where raw keystroke sequences
      are available (optional, requires per-window sequence data)

Evaluation: leave-one-subject-out, repeated, same protocol as cloud_train.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\ItzP\miniproject\training")
import cloud_train as ct  # noqa: E402


def main() -> None:
    X1, y1, s1, mapping, stress1 = ct.load_swellkw(
        r"C:\Users\ItzP\miniproject\training\data\Behavioral-features - per minute.tab")
    k = pd.read_csv(r"C:\Users\ItzP\miniproject\training\data\kaggle_raw_rebuilt.csv")
    F = ct.FEATURE_NAMES
    X2 = k[F].to_numpy(dtype=np.float32)
    y2 = k["label"].to_numpy(dtype=np.int32)
    s2 = k["user_id"].astype(str).to_numpy()

    X = np.concatenate([X1, X2])
    y = np.concatenate([y1, y2])
    s = np.concatenate([s1, s2])
    print(f"fine-tune data: {X.shape}, {len(np.unique(s))} subjects")

    m = ct.loocv_evaluate(X, y, s, repeats=2)
    print("\nLOOCV (2 repeats):")
    for kk in ["accuracy", "f1_macro", "precision_macro", "recall_macro"]:
        print(f"  {kk}: {m[kk]:.4f}")
    print(m["classification_report"].splitlines()[-4])


if __name__ == "__main__":
    main()
