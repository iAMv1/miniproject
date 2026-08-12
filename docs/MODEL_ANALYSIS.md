# MindPulse — Model Analysis (every level, honest)

Date: Aug 12 2026. Status: after two confound removals (session_duration_min,
hour_of_day) and one fixed subject-held-out test.

## 1. Current config (exact)

- Algorithm: XGBoost, objective `multi:softprob`, 3 classes (0/1/2)
- Hyperparameters (tuned, GroupKFold-5 inner CV, seed 42):
  `n_estimators=400, max_depth=5, learning_rate=0.05, subsample=1.0,
  colsample_bytree=1.0, min_child_weight=5, gamma=0.0, reg_alpha=0.0,
  reg_lambda=4.0`
- Input: 23-feature vector. REAL features: click_count, typing_speed_wpm,
  rage_click_count, scroll_velocity_std, direction_change_rate,
  switch_entropy, mouse_speed_mean, mouse_speed_std, error_rate,
  tab_switch_freq (10). ZEROED by design: hold_*, flight_* (no key-up data),
  pause_*, burst, rhythm_entropy, session_fragmentation, session_duration_min,
  hour_of_day, day_of_week (13 slots kept for contract).
- Input guards: zero-variance mask + p1/p99 clip (deployed in backend).
- Data: SWELL-KW 2,688 min (25 subj, stressor-condition labels) +
  Kaggle-raw rebuilt 86 windows (2 subj, self-report labels). 2,774 total.
- Split: fixed subject-held-out test (6 subj, 622 rows, seed 42), dev = rest.

## 2. Measured capability (confound-free, unseen subjects)

| Metric | Test set |
|---|---|
| 3-class accuracy | 0.43 (majority = 0.39) |
| 3-class macro-F1 | 0.39 |
| NEUTRAL F1 / MILD F1 / STRESSED F1 | 0.53 / 0.42 / 0.22 |
| Binary (stress vs not) acc / F1 | 0.60 / 0.65 (majority F1 = 0.76) |
| ECE (calibration) | 0.098 |
| Leading features (permutation) | click_count +0.043, wpm +0.025, rage_clicks +0.014 |

Verdict: universal cross-subject 3-class detection is statistically
indistinguishable from the majority baseline. Binary detection is weak and
below the majority-class F1. This is NOT a model failure — it reproduces the
field result (ETH 2025: one-fits-all ρ=0.078 ≈ chance; personalized is the
only path).

## 3. Is the model required? (perspective: product)

- The heuristic equation score (keyboard .30, speed .15, switching .25,
  mouse .20, reentry .10) currently contributes as much as the ML model.
  With the model at chance level, the deployed system's output is dominated
  by heuristics + personalization anyway.
- REQUIRED configuration: binary (stressed/not) + per-user calibration,
  NOT 3-class universal. The 3-class contract should be demoted to
  "reference classes" until personalized models are measured cleanly.
- The ML model's real value appears only per-user (ρ≈0.25 range, pending
  clean re-measurement) — the personalization code path (baseline,
  calibration) is the product.

## 4. Flaws & gaps by level

### Data
- 27 subjects total; 6-subject test set = high variance (±0.15 F1 across
  folds observed).
- Labels are stressor-CONDITION proxies (protocol) + self-reports; not
  clinical. Condition labels carry protocol artifacts (block lengths).
- Class imbalance 1059/1035/680; STRESSED under-represented and worst-F1.
- No external validation dataset (SENSE-42/ETH gated; Frustrometer is
  frustration, not stress).

### Features
- 13/23 slots dead: model effectively uses 10. Zero-fill is honest but
  wastes contract; clients sending values on dead slots are clipped/zeroed.
- Feature definitions now aligned across sources (SWELL-compatible) — but
  mouse_speed scale still differs by collection method (per-minute
  distance vs per-event sampling).
- No per-user normalization in the model path (DualNormalizer's user
  z-scores exist but the raw-model path skips them).

### Model
- XGBoost is right for tabular; the weakness is signal, not capacity.
- No class-weighting experiments, no threshold optimization on validation
  (thresholds 40/70 are arbitrary).
- Calibration: ECE 0.098 acceptable, but score→level mapping unvalidated.
- Ensemble (RF/LightGBM) absent; bagging across seeds untested on test.

### Evaluation
- Fixed subject-held-out test exists NOW (the improvement). LOOCV numbers
  earlier were confounded — do not quote 0.71.
- Repeated-CV std huge (0.17-0.20) — single-fold numbers are unstable;
  report mean±std or CIs.
- Binary evaluation not the headline yet — should be.

### Deployment
- Backend loads the model and serves 3-class levels with confidence —
  currently OVERCLAIMS (model ≈ chance). Must either (a) ship the binary
  config with honest labels, or (b) disable 3-class claims until
  personalized results exist.
- Browser ONNX still old synthetic weights — mismatch persists.
- Manifest now records the confound-free protocol (good).

## 5. Recommended posture (ranked) — SUPERSEDED by the personalized measurement

Measured (Aug 12, chronological within-subject, 25 subjects):

| Variant | ρ mean / median | Binary F1 | 3-class acc |
|---|---|---|---|
| Global model | 0.026 / 0.094 | 0.658 | 0.316 |
| Per-user model | 0.115 / **0.227** | 0.596 | 0.095 |

Confirmed by data:
1. Universal detection ≈ 0 signal (ρ≈0 across all evaluations and feature
   treatments). DELETE universal 3-class claims.
2. Per-user models carry real signal: median ρ 0.227, inside ETH's
   personalized range (0.188-0.296). This is THE product claim.
3. V1 ≡ V3 (per-user raw == per-user user-z): z-scoring is a monotonic
   transform; XGBoost trees are invariant within one user's model.
   User-normalization cannot rescue the global path for trees.
4. 3-class per-user is infeasible at ~77 train rows; binary only.

REVISED posture:
1. Product = per-user binary deviation detection + calibration (median
   ρ≈0.23, ETH-consistent). No 3-class universal claims anywhere.
2. Paper positive result = personalized median ρ 0.227 + the clean
   universal negative (ρ≈0.03) — reproduces and sharpens ETH 2025.
3. Threshold/calibration tuning on dev folds only; per-user thresholds.
4. Labeled data via telemetry+EMA (the only real lever for ρ growth).

## 6. What would change this analysis

- Personalized ρ materially > 0.3 with clean protocol → strong product claim.
- External labeled set (SENSE-42/ETH) showing transfer → universal model
  becomes defensible.
- Test-set improvement from class-weighting/bagging ≥ +0.05 F1 → adopt.
