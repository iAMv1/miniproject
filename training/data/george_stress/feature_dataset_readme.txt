DATA INSTRUCTIONS
=================

This project uses two public datasets. Place them under `data/` so the
final layout is:

    data/
    ├── KeyStroke/
    │   ├── user_1/
    │   │   ├── keystrokes.tsv
    │   │   ├── usercondition.tsv
    │   │   └── mousedata.tsv
    │   └── user_2/
    │       ├── keystrokes.tsv
    │       ├── usercondition.tsv
    │       └── mousedata.tsv
    └── IKDD/
        ├── any_ks&dl_user001_(1).txt
        ├── any_ks&dl_user002_(1).txt
        └── ... (374 files total)


1. Stress Detection by Keystroke & Mouse  (Kaggle)
--------------------------------------------------
URL:       https://www.kaggle.com/datasets/anmolkumar/stress-detection-by-typing-pattern
Required:  Yes — used for supervised training.
Files:     keystrokes.tsv, usercondition.tsv, mousedata.tsv
           (other files such as activewindows.tsv, inactivity.tsv, and
           mouse_mov_speeds.tsv may be present in the download but are
           not used by this pipeline.)

Download the full archive, unzip, and place the `user_1` and `user_2`
folders inside `data/KeyStroke/` so the paths above match.


2. IKDD Keystroke Dynamics
--------------------------
URL:       https://github.com/MachineLearningVisionRG/IKDD
Required:  Optional — only used for distributional analysis in the
           notebook (not required for `train_models.py` to run).

Clone or download and place all `any_ks&dl_userNNN_(*).txt` files inside
`data/IKDD/`.


Path configuration
------------------
The path is set near the top of `train_models.py` and `features.py`.
By default it expects:

    KAGGLE_PATH = "./data/KeyStroke"
    USERS       = ["user_1", "user_2"]

Update if you place the data elsewhere.
