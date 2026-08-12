# MindPulse — Session State (Aug 12 2026)

Compact handoff for a fresh session. All work is in this repo; read this file
instead of a long chat history.

## Status
- Best honest model: XGBoost, 23 features (13 real), LOOCV acc ~0.71 / F1 ~0.67
  BEFORE a data leak was found and removed. POST-FIX numbers pending the
  evaluate_suite run — do not quote the 0.71 numbers as final.
- CRITICAL: `session_duration_min` was a condition proxy (file lists blocks
  N-first for every subject; T blocks shorter by protocol). Zeroed in
  `training/cloud_train.py` (slot kept for contract).

## Verified working
- Backend boots with real-data model; auth + inference + history E2E tested
  (NEUTRAL 17-19 / MILD 51-56 / STRESSED 67-80 scores on real rows).
- Kaggle automation: dataset `afafas212141/mindpulse-swell-v3`, kernels
  v6-v8 (LOOCV/tuning), pretrain-encoder-v1 (COMPLETE), finetune-nn-v1
  (COMPLETE). Kaggle token in chat history — USER SHOULD REVOKE.

## Data (all local, `training/data/`, catalog: `training/data/DATASETS.md`)
- Labeled: SWELL-KW 25 subj/2688 min; Kaggle-raw rebuilt 86 windows
  (real self-report labels, rebuilt by `rebuild_kaggle_labels.py`);
  fnokeke EMA (small); Frustrometer 2.2GB (downloaded, labels = frustration,
  NOT stress — use only as auxiliary/transfer).
- Unlabeled: IKDD 374 users, KUPA-KEYS 1006 users, 136M (42k sessions).
- Gated (request URLs in DATASETS.md): SENSE-42, ETH OSF, Pepa, Naegelin.

## Pipeline (training/)
- `data_prep.py` → frozen `cleaned_dataset.parquet` + `splits.json`
  (subject-disjoint dev/test, seed 42, hash c7d4d10f…)
- `evaluate_suite.py` → senior protocol: fixed test subjects, 5-model dev
  leaderboard, calibration ECE, permutation importance, error analysis.
  RESULTS PENDING (backgrounded when this was written).
- SSL stage (negative result, documented in COMPLETION_REPORT.md): GRU
  encoder on 59k sessions → frozen/fine-tuned transfer did NOT beat
  XGBoost features. Labeled data is the bottleneck.
- Artifacts: `backend/app/ml/artifacts/` (model_xgb.joblib, global_stats,
  artifacts_manifest.json). Rebuild from clean pipeline before deploy.

## Security (done, E2E-verified)
- Demo token removed, JWT secret ephemeral unless set, all routes authed,
  WS/SSE token auth, rate limiting, bcrypt direct (passlib removed),
  schema bounds match real data, distribution guards (zero-mask + clip).

## Known gaps
- Browser ONNX still old synthetic weights (onnxmltools dead on py3.12).
- Desktop→backend telemetry bridge NOT built (the product's own data
  collection channel).
- No test suite, no commit yet (working tree dirty — commit when user asks).
- Kaggle token KGAT_55233… was pasted in chat: REVOKE.
