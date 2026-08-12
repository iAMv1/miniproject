"""MindPulse — End-to-end fine-tuning: pretrained encoder + classification head.

The frozen-embedding experiment hurt (-0.03 F1); the standard fix is
end-to-end fine-tuning of the encoder with a label head, evaluated with
subject-grouped cross-validation (GroupKFold, 5 folds).

Inputs (dataset):
  embed_inputs.npz   — per-window hold/flight sequences (2,163 windows)
  labels.csv         — window_id -> label (from SWELL per-minute + Kaggle rebuilt)

Output: grouped-CV metrics (acc, macro-F1) to compare against XGBoost baselines.
"""
import glob
import os

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold

import sys
sys.path.insert(0, glob.glob("/kaggle/input/**/", recursive=True)[0])
from pretrain_encoder import TypingEncoder  # noqa: E402


class Head(nn.Module):
    def __init__(self, hidden, n_class=3):
        super().__init__()
        self.fc = nn.Sequential(nn.Linear(hidden, 64), nn.ReLU(), nn.Dropout(0.2),
                                nn.Linear(64, n_class))

    def forward(self, e):
        return self.fc(e)


def main():
    inp = glob.glob("/kaggle/input/**/embed_inputs.npz", recursive=True)[0]
    lab = glob.glob("/kaggle/input/**/labels.csv", recursive=True)[0]
    enc = glob.glob("/kaggle/input/**/encoder.pt", recursive=True)[0]

    d = np.load(inp)
    x = np.stack([d["hold"], d["flight"]], axis=-1).astype(np.float32)
    mask = d["mask"]
    wids = d["window_id"]
    src = d["source"]

    lab_df = pd.read_csv(lab)
    lab_map = dict(zip(lab_df["window_id"], lab_df["label"]))
    subj_map = dict(zip(lab_df["window_id"], lab_df["subject"]))

    y = np.asarray([lab_map.get(w, -1) for w in wids])
    subs = np.asarray([subj_map.get(w, "?") for w in wids])
    keep = y >= 0
    x, mask, y, subs = x[keep], mask[keep], y[keep], subs[keep]
    print(f"labeled windows: {len(x)}, subjects: {len(np.unique(subs))}")

    ckpt = torch.load(enc, map_location="cpu")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = TypingEncoder(hidden=ckpt["hidden"], layers=ckpt["layers"])
    model.load_state_dict(ckpt["state"])
    head = Head(ckpt["hidden"])
    model.to(device)
    head.to(device)

    loss_fn = nn.CrossEntropyLoss()
    opt = torch.optim.AdamW(list(model.parameters()) + list(head.parameters()),
                            lr=1e-4, weight_decay=1e-4)

    gkf = GroupKFold(n_splits=5)
    preds = np.zeros(len(y), dtype=np.int64)
    for fold, (tr, va) in enumerate(gkf.split(x, y, groups=subs)):
        model.train()
        head.train()
        xt = torch.from_numpy(x[tr]).to(device)
        mt = torch.from_numpy(mask[tr]).to(device)
        yt = torch.from_numpy(y[tr]).to(device)
        for epoch in range(12):
            perm = torch.randperm(len(xt))
            for i in range(0, len(xt), 256):
                idx = perm[i:i + 256]
                e = model.embed(xt[idx], mt[idx])
                logits = head(e)
                loss = loss_fn(logits, yt[idx])
                opt.zero_grad()
                loss.backward()
                opt.step()
        model.eval()
        head.eval()
        with torch.no_grad():
            xv = torch.from_numpy(x[va]).to(device)
            mv = torch.from_numpy(mask[va]).to(device)
            e = model.embed(xv, mv)
            preds[va] = head(e).argmax(1).cpu().numpy()
        print(f"fold {fold}: macro_f1={f1_score(y[va], preds[va], average='macro', zero_division=0):.4f}")

    print(f"\nGROUPED-CV (5 folds): acc {accuracy_score(y, preds):.4f} | "
          f"macro_f1 {f1_score(y, preds, average='macro', zero_division=0):.4f}")
    np.save("/kaggle/working/grouped_cv_preds.npy", preds)
    print("saved grouped_cv_preds.npy")
    print("=== DONE ===")


if __name__ == "__main__":
    main()
