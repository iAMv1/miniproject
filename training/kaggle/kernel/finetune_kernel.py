"""MindPulse — end-to-end fine-tuning kernel (grouped CV)."""
import glob
import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "torch", "numpy", "pandas", "scikit-learn"])

finetune = glob.glob("/kaggle/input/**/finetune_nn.py", recursive=True)[0]
sys.exit(subprocess.call([sys.executable, finetune]))
