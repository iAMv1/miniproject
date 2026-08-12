"""MindPulse — Kaggle pretraining kernel: typing-behavior GRU encoder.

Trains the masked-reconstruction encoder on 59K keystroke sessions
(IKDD + KUPA-KEYS), saves encoder.pt to /kaggle/working/artifacts.
"""
import glob
import os
import subprocess
import sys

OUT = "/kaggle/working/artifacts"
os.makedirs(OUT, exist_ok=True)

hits = glob.glob("/kaggle/input/**/sequences.npz", recursive=True)
assert hits, "sequences.npz not found under /kaggle/input"
DATA = hits[0]
print("DATA =", DATA)

subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q",
     "torch", "numpy"]
)

subprocess.check_call(
    [sys.executable,
     glob.glob("/kaggle/input/**/pretrain_encoder.py", recursive=True)[0],
     "--data", DATA,
     "--out", os.path.join(OUT, "encoder.pt"),
     "--epochs", "15",
     "--hidden", "128",
     "--layers", "2",
     "--batch", "512",
     "--lr", "1e-3"]
)

print("=== ARTIFACTS ===")
for f in sorted(os.listdir(OUT)):
    print(f, os.path.getsize(os.path.join(OUT, f)))
print("=== DONE ===")
