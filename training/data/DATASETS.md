# MindPulse — Data Acquisition Catalog (verified Aug 2026)

Complete inventory of every dataset acquired during the research hunt, with
source, license, size, role, and processing status. All files local under
`training/data/`.

## Labeled datasets (training/evaluation)

| Dataset | Subjects | Labels | Source | License | Local path | Role |
|---|---|---|---|---|---|---|
| SWELL-KW per-minute features | 25 | 3-class stressor conditions + self-report Stress 0-10 (2,688 min) | DANS DataStation SSH (API, no account) | CC-BY-NC-SA | `data/Behavioral-features - per minute.tab` | PRIMARY training + validation (LOOCV) |
| SWELL-KW raw uLog XMLs | 25 | (same block labels) | DANS API (75 files) | CC-BY-NC-SA | `data/swell_ulog/` | pause/burst/rhythm features; future full extraction |
| Kaggle 2-user RAW source | 2 | self-report Stress_Val Neutral/S_Stressed/V_Stressed every ~30 min | Kaggle API | Kaggle terms | `data/kaggle_raw_rebuilt.csv` | REAL multi-class windows (86) rebuilt by `rebuild_kaggle_labels.py` |
| fnokeke EMA study | 1-2 | self-report stress (4 levels) + fatigue/affect | GitHub (public repo) | repo terms | `data/fnokeke_ema_study/` | real-world EMA + raw kb/mouse; methodology reference, small |
| georgejbarakat stress features | 2 | stress_label binary (464 windows) | GitHub (public repo) | repo terms | `data/george_stress/` | dwell/IKI/mouse features — validates feature schema |

## Unlabeled corpora (self-supervised pretraining)

| Dataset | Subjects | Content | Source | License | Local path | Role |
|---|---|---|---|---|---|---|
| IKDD keystroke dynamics | 374 | per-user keystroke latency rows + demographics (533 files, ~280 MB) | GitHub MachineLearningVisionRG/IKDD | repo terms | `data/ikdd/` | SSL encoder pretraining (typing dynamics) |
| 136M keystrokes | many | per-user keystroke sequences (1.6 GB) | Kaggle API | Kaggle terms | `$TEMP/typing136/extracted/` | SSL encoder pretraining (scale) |
| KUPA-KEYS | 1,006 | raw key down/up events + CEFR proficiency marks | Hugging Face ALTACambridge/KUPA-KEYS (public) | CC-BY-NC-SA | `data/kupa_keys/` (downloading) | SSL pretraining + writing-process features |

## Gated / request-only (not acquired — documented for the paper's related work)

| Dataset | Subjects | Why gated | How to obtain |
|---|---|---|---|
| SENSE-42 | 42 | Zenodo restricted | access request form at zenodo.org/records/20328098 |
| ETH Zurich 2025 (medRxiv) | 36, 8 weeks | OSF private | request at osf.io/qpekf |
| Pepa et al. 2021 | 62 | on request | email authors |
| Naegelin et al. 2023 | 90 | on request | email authors |

## Notes on correctness (per-dataset honesty)

- **SWELL-KW**: best fit — real office knowledge work, validated stressor
  protocol (neutral/interruption/time-pressure), self-report ground truth.
  Labels are stressor-condition proxies, not clinical stress.
- **Kaggle 2-user raw**: real self-reported labels exist in the SOURCE
  (`usercondition.tsv`). The repo's old `real_dataset.csv` (all label=1) was a
  mis-processing; `rebuild_kaggle_labels.py` re-extracts 23 features over
  30-min windows from raw keystroke/mouse/app logs with SWELL-compatible
  feature definitions.
- **IKDD / 136M / KUPA-KEYS**: NO stress labels. Used ONLY for unsupervised
  typing-behavior pretraining. Never claim stress labels from them.
- **fnokeke**: real EMA self-reports + raw events, but single-user pilot
  scale — usable as a real-world test set and methodology reference.
