"""MindPulse — Kaggle training kernel v5 (auto-discover input path)."""
import glob
import os
import subprocess
import sys

OUT = "/kaggle/working/artifacts"
os.makedirs(OUT, exist_ok=True)

hits = glob.glob("/kaggle/input/**/swell_features.tab", recursive=True)
assert hits, "swell_features.tab not found under /kaggle/input"
DATA = os.path.dirname(hits[0])
print("DATA =", DATA)

subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q",
     "-r", os.path.join(DATA, "requirements.txt")]
)

tab = os.path.join(DATA, "swell_features.tab")
merged = os.path.join(DATA, "swell_features_merged.tab")
data_file = merged if os.path.exists(merged) else tab

subprocess.check_call(
    [sys.executable, os.path.join(DATA, "cloud_train.py"),
     "--data", data_file,
     "--out", OUT,
     "--export-onnx",
     "--repeats", "3",
     "--stress-correlation",
     "--tune"]
)

print("=== ARTIFACTS ===")
for f in sorted(os.listdir(OUT)):
    print(f, os.path.getsize(os.path.join(OUT, f)))
print("=== DONE ===")
