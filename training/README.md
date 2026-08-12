# MindPulse — Cloud Training (Kaggle / Google Colab)

Trains the production model on **real behavioral data** with
subject-independent validation, replacing the synthetic fallback.

## 1. Get the dataset

### SWELL-KW (recommended — 25 real subjects, keyboard + mouse)

Landing page: <https://ssh.datastations.nl/dataset.xhtml?persistentId=doi:10.17026/dans-x55-69zp>
(DOI `10.17026/dans-x55-69zp`, CC-BY-NC-SA — attribute it, no commercial use).

**No account needed for the feature file.** Direct download (already fetched
into `training/data/`):

```
Behavioral-features - per minute.tab   →  https://ssh.datastations.nl/api/access/datafile/171299
```

Verified structure (Aug 2026): 3,139 rows × 172 columns, 25 participants
(PP1–PP25, ~126 min each), per-minute rows. Columns of interest:

- `Condition`: `N` neutral (1,028) / `I` interruption (996) / `T` time
  pressure (664) / `R` relax (451 — excluded from training)
- `PP` participant id, `Blok` counterbalanced block order (NOT a condition)
- Behavioral per-minute: `SnMouseAct`, `SnLeftClicked`, `SnRightClicked`,
  `SnDoubleClicked`, `SnWheel`, `SnDragged`, `SnMouseDistance`,
  `SnKeyStrokes`, `SnChars`, `SnSpecialKeys`, `SnDirectionKeys`,
  `SnErrorKeys`, `SnShortcutKeys`, `SnSpaces`, `SnAppChange`,
  `SnTabfocusChange`, `CharactersRatio`, `ErrorKeyRatio`
- Ground truth: `Stress` (0–10 self-report), `NasaTLX`, `Valencrc`,
  `Arousalrc` — per-block values broadcast to minutes

`0_SWELL.zip` (7.5 GB, `https://ssh.datastations.nl/api/access/datafile/614650`)
contains everything incl. raw uLog XMLs — only needed for the full 23-feature
extraction later.

### Alternative — Kaggle 2-user dataset

Already in the repo (`backend/app/ml/artifacts/real_dataset.csv`). Use it as
a supplement with `--extra-csv`, never as the primary source (2 subjects,
label 1 only).

### Alternative — HCI-SENSE-42 (Zenodo, CC0)

42 subjects, raw keyboard/mouse events at 144 Hz, no license friction
(commercial-safe). Needs custom feature extraction — use after the SWELL-KW
pipeline is proven.

## 2. What the loader maps

| MindPulse feature | SWELL-KW source |
|---|---|
| typing_speed_wpm | derived: SnChars / 5 |
| error_rate | ErrorKeyRatio |
| click_count | SnLeftClicked |
| mouse_speed_mean | SnMouseDistance (px/min → px/s) |
| rage_click_count | derived: SnMouseAct − SnLeftClicked − SnWheel |
| tab_switch_freq | SnTabfocusChange |
| switch_entropy | SnAppChange |
| direction_change_rate | SnDirectionKeys |
| scroll_velocity_std | SnWheel |
| session_duration_min | minute index within block |
| hour_of_day / day_of_week | parsed from `timestamp` (20120918T131600000) |
| hold/flight/rhythm features | NOT in per-minute file → zero-filled and reported in the mapping table |

The mapping report is printed at load time — never silent. For the missing
temporal features (hold time, flight time, pauses, rhythm entropy) the raw
uLog XMLs are required; see "Next step" below.

## 3. Run training

### Google Colab

```python
!pip install -q -r /content/drive/MyDrive/mindpulse/training/requirements.txt
```

```python
!python /content/drive/MyDrive/mindpulse/training/cloud_train.py \
    --data "/content/drive/MyDrive/mindpulse/training/data/Behavioral-features - per minute.tab" \
    --out /content/drive/MyDrive/mindpulse/artifacts \
    --export-onnx
```

The file is already staged at `training/data/` (see `training/data/README.md`
for license). If the condition column uses block codes (e.g. "Block 1/2/3")
the script stops and tells you the exact values; pass:

```python
--condition-map "Block 1:0,Block 2:1,Block 3:2"
```

(Before trusting this mapping, check the block order per participant in the
dataset documentation — blocks are counterbalanced.)

### Kaggle

1. Create a **Dataset** with `Behavioral-features - per minute.tab`
   (`Create → New Dataset → upload`).
2. Notebook → `Settings → Add Input` → your dataset.
3. `pip install -r training/requirements.txt`, then run the same command
   with `--data /kaggle/input/<slug>/<filename>` and
   `--out /kaggle/working/artifacts`.
4. `Output → Commit`, download artifacts, commit them to
   `backend/app/ml/artifacts/`.

### Scheduled retraining

Kaggle `Settings → Schedule` or Colab `Tools → Scheduled notebooks` re-run
the notebook periodically; ship the new artifacts as a GitHub Release.

## 4. Wire the backend

```env
# .env
MINDPULSE_MODEL_URL=https://github.com/iAMv1/miniproject/releases/download/model-v2/model_xgb.joblib
MINDPULSE_STATS_URL=https://github.com/iAMv1/miniproject/releases/download/model-v2/global_stats.joblib
```

Upload `model_xgb.joblib` + `global_stats.joblib` as a GitHub Release asset
(public URL, no auth needed). `load_model()` in `app/ml/model.py` downloads
and verifies them at startup; the synthetic fallback is only used if the
download fails.

`--export-onnx` also regenerates `xgb_model.onnx` for
`frontend/public/models/` — browser and backend then run the SAME weights.

## 5. What the manifest proves

`artifacts_manifest.json` records: dataset SHA256, feature mapping
(SWELL-KW column → MindPulse feature), LOOCV metrics per held-out subject,
class distribution, training commit, timestamp. Keep it with the artifacts.

## Next step (full 23 features)

The official per-minute file lacks hold/flight times, pause structure and
rhythm features. The raw uLog XMLs (folder `A - ... raw data uLog/`) contain
every keystroke/mouse event with timestamps. Plan: write
`training/ulog_parser.py` (Noldus uLog 3.2.5 XML → per-minute 23-feature
matrix) so the full MindPulse feature set is extracted from real events.
Not needed to get the pipeline running — the current mapping already trains
on real data.

## License note

SWELL-KW: CC-BY-NC (attribute, non-commercial). HCI-SENSE-42: CC0
(commercial-safe alternative). The 2-user Kaggle set: verify its terms.
