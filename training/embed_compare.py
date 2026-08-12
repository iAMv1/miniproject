"""MindPulse — Extract encoder embeddings for labeled windows + LOOCV comparison.

1. Loads pretrained encoder.pt + embed_inputs.npz
2. Embeds each labeled window's sequence -> 128-dim vector
3. Joins embeddings to the 23-feature matrices by row_idx
4. LOOCV with and without embeddings -> comparison table
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, r"C:\Users\ItzP\miniproject\training")
import cloud_train as ct  # noqa: E402
from pretrain_encoder import TypingEncoder  # noqa: E402


def main() -> None:
    enc_path = sys.argv[1] if len(sys.argv) > 1 else \
        r"C:\Users\ItzP\miniproject\training\data\encoder.pt"
    ckpt = torch.load(enc_path, map_location="cpu")
    model = TypingEncoder(hidden=ckpt["hidden"], layers=ckpt["layers"])
    model.load_state_dict(ckpt["state"])
    model.eval()
    print(f"encoder loaded: hidden={ckpt['hidden']} layers={ckpt['layers']}")

    d = np.load(r"C:\Users\ItzP\miniproject\training\data\embed_inputs.npz")
    x = np.stack([d["hold"], d["flight"]], axis=-1).astype(np.float32)
    mask = d["mask"]
    row_idx = d["row_idx"]
    print(f"windows to embed: {len(x)}")

    embs = []
    with torch.no_grad():
        for i in range(0, len(x), 512):
            xb = torch.from_numpy(x[i:i + 512])
            mb = torch.from_numpy(mask[i:i + 512])
            embs.append(model.embed(xb, mb).numpy())
    E = np.vstack(embs).astype(np.float32)
    print(f"embeddings: {E.shape}")

    # labeled matrices
    X1, y1, s1, _, _ = ct.load_swellkw(
        r"C:\Users\ItzP\miniproject\training\data\Behavioral-features - per minute.tab")
    k = pd.read_csv(r"C:\Users\ItzP\miniproject\training\data\kaggle_raw_rebuilt.csv")
    F = ct.FEATURE_NAMES
    X2 = k[F].to_numpy(dtype=np.float32)
    y2 = k["label"].to_numpy(dtype=np.int32)
    s2 = k["user_id"].astype(str).to_numpy()

    X = np.concatenate([X1, X2])
    y = np.concatenate([y1, y2])
    s = np.concatenate([s1, s2])
    n_swell = len(X1)

    # alignment: embed row_idx refers to row position in the ORIGINAL files
    # swell row_idx = position in per-minute tab (incl. relax rows) -> map to
    # training indices via user/label alignment; kaggle row_idx = rebuilt csv row
    emb_map = {}
    for i, r in enumerate(row_idx):
        emb_map[d["source"][i], int(r)] = E[i]

    # swell: per-minute tab row -> index into X1 (rows after relax exclusion)
    pm = pd.read_csv(r"C:\Users\ItzP\miniproject\training\data\Behavioral-features - per minute.tab",
                     sep="\t")
    pm = pm[pm["Condition"] != "R"].reset_index(drop=True)
    pm_idx = {i: i for i in range(len(pm))}  # same order as X1

    Xa = np.zeros((len(X), 128), dtype=np.float32)
    have = np.zeros(len(X), dtype=bool)
    for (src, r), e in emb_map.items():
        if src == "kaggle":
            # rebuilt csv row -> position in X2 (row order preserved)
            pos = n_swell + int(r)
            if pos < len(X):
                Xa[pos] = e
                have[pos] = True
        else:
            pos = int(r)
            if pos in pm_idx:
                Xa[pos] = e
                have[pos] = True
    print(f"windows with embeddings: {int(have.sum())}/{len(X)}")

    Xh = np.concatenate([X, Xa], axis=1)
    idx_have = np.where(have)[0]

    print("\n=== LOOCV comparison (2 repeats) ===")
    print("-- 23 features only (all windows) --")
    m1 = ct.loocv_evaluate(X, y, s, repeats=2)
    print(f"  acc {m1['accuracy']:.4f} | f1 {m1['f1_macro']:.4f}")
    print("-- 23 + embeddings (windows with sequences only) --")
    m2 = ct.loocv_evaluate(Xh[idx_have], y[idx_have], s[idx_have], repeats=2)
    print(f"  acc {m2['accuracy']:.4f} | f1 {m2['f1_macro']:.4f}")
    print("-- 23 features only (same subset) --")
    m3 = ct.loocv_evaluate(X[idx_have], y[idx_have], s[idx_have], repeats=2)
    print(f"  acc {m3['accuracy']:.4f} | f1 {m3['f1_macro']:.4f}")


if __name__ == "__main__":
    main()
