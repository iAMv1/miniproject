"""MindPulse — Self-supervised typing-behavior encoder (GRU, masked reconstruction).

Pretrains a small GRU on unlabeled keystroke sequences (136M + IKDD + KUPA-KEYS)
with masked hold/flight reconstruction. The encoder learns a general model of
typing dynamics; the frozen embeddings then feed the labeled fine-tuning head.

Designed to run on Kaggle GPU (torch preinstalled). Local CPU can run with
--epochs 1 and small hidden size for smoke tests.

Usage:
    python pretrain_encoder.py --data sequences.npz --out encoder.pt \
        --epochs 20 --hidden 128 --layers 2 --batch 512
"""

from __future__ import annotations

import argparse
import os

import numpy as np
import torch
import torch.nn as nn


class TypingEncoder(nn.Module):
    """GRU encoder: 2 input channels (log-hold, log-flight) -> hidden -> embedding.
    A linear decoder reconstructs both channels per step (masked)."""

    def __init__(self, hidden: int = 128, layers: int = 2, dropout: float = 0.1):
        super().__init__()
        self.hidden = hidden
        self.layers = layers
        self.input_norm = nn.LayerNorm(2)
        self.gru = nn.GRU(2, hidden, num_layers=layers, batch_first=True,
                          dropout=dropout if layers > 1 else 0.0)
        self.head = nn.Linear(hidden, 2)

    def forward(self, x, mask):
        # x: [B, T, 2] (hold, flight), mask: [B, T]
        x = self.input_norm(x)
        out, _ = self.gru(x)
        recon = self.head(out)  # [B, T, 2]
        return recon

    def embed(self, x, mask):
        x = self.input_norm(x)
        out, _ = self.gru(x)
        # mean-pool over valid steps
        m = mask.unsqueeze(-1).float()
        return (out * m).sum(1) / m.sum(1).clamp(min=1.0)


def load_data(path: str):
    d = np.load(path)
    x = np.stack([d["hold"], d["flight"]], axis=-1).astype(np.float32)
    mask = d["mask"]
    src = d["source"]
    return x, mask, src


def train(args) -> None:
    x, mask, src = load_data(args.data)
    print(f"data: {x.shape} sessions | sources: {dict(zip(*np.unique(src, return_counts=True)))}")
    if args.limit:
        x, mask, src = x[:args.limit], mask[:args.limit], src[:args.limit]
        print(f"limited to {len(x)}")

    n = len(x)
    val_n = max(1, int(n * 0.05))
    x_val, mask_val = x[:val_n], mask[:val_n]
    x_tr, mask_tr = x[val_n:], mask[val_n:]

    model = TypingEncoder(hidden=args.hidden, layers=args.layers)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    loss_fn = nn.MSELoss(reduction="none")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    print(f"device: {device} | params: {sum(p.numel() for p in model.parameters()):,}")

    xv = torch.from_numpy(x_val).to(device)
    mv = torch.from_numpy(mask_val).to(device)

    for epoch in range(1, args.epochs + 1):
        model.train()
        total, seen = 0.0, 0
        perm = torch.randperm(len(x_tr))
        for i in range(0, len(x_tr), args.batch):
            idx = perm[i:i + args.batch]
            xb = torch.from_numpy(x_tr[idx]).to(device)
            mb = torch.from_numpy(mask_tr[idx]).to(device)

            # masked reconstruction: corrupt 40% of valid steps with noise
            corrupt = (torch.rand_like(xb) < 0.4) & mb.unsqueeze(-1)
            xc = xb.clone()
            xc[corrupt] = xc[corrupt] + torch.randn_like(xc[corrupt]) * 0.5

            recon = model(xc, mb)
            loss = loss_fn(recon, xb)
            loss = (loss.mean(-1) * mb).sum() / mb.sum().clamp(min=1.0)

            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            total += loss.item() * len(idx)
            seen += len(idx)

        model.eval()
        with torch.no_grad():
            recon = model(xv, mv)
            vloss = (loss_fn(recon, xv).mean(-1) * mv).sum() / mv.sum().clamp(min=1.0)
        print(f"epoch {epoch:2d} | train {total/seen:.4f} | val {vloss.item():.4f}")

    torch.save({"state": model.state_dict(), "hidden": args.hidden,
                "layers": args.layers, "max_len": x.shape[1]}, args.out)
    print(f"saved encoder -> {args.out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=r"C:\Users\ItzP\miniproject\training\data\sequences.npz")
    ap.add_argument("--out", default=r"C:\Users\ItzP\miniproject\training\data\encoder.pt")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--hidden", type=int, default=128)
    ap.add_argument("--layers", type=int, default=2)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--limit", type=int, default=0, help="truncate dataset (smoke tests)")
    args = ap.parse_args()
    train(args)


if __name__ == "__main__":
    main()
