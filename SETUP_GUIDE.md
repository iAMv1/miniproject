# MindPulse — Setup Guide (plain steps, no jargon)

Everything below needs YOUR account. The code side is done and tested —
you only do these three setups, then the app is fully online.

---

## A. Supabase (move data to the cloud database)

1. Open https://supabase.com in your browser → click **Start your project** → sign in with Google or GitHub.
2. Create an **organization** (name: anything, e.g. "mindpulse").
3. Click **New project**:
   - Name: `mindpulse`
   - Database password: choose a strong one and SAVE it somewhere (you won't need it often, but you need it once more later)
   - Region: pick the one closest to you
   - Click **Create new project** and wait ~2 minutes.
4. On the left menu, click **SQL Editor**.
5. Open the file `supabase_schema_v2.sql` from this project (it's in the root folder). Select ALL its text, copy it.
6. In the SQL Editor, paste it in the big white box, click **Run**. You should see "Success".
7. On the left menu: **Project Settings** (gear icon) → **API**.
8. Copy two things:
   - **Project URL** (looks like `https://xxxx.supabase.co`)
   - **anon public** key (long string starting with `sb_` or `eyJ...`)
9. Open `backend/.env` in this project and set:
   ```
   SUPABASE_URL=https://xxxx.supabase.co
   SUPABASE_ANON_KEY=<the long key>
   ```
10. Restart the backend: close the terminal window where it runs, start it again.
11. Done — the app now stores chat/wellness/focus in your Supabase project.

---

## B. Google Sign-In button

1. Open https://console.cloud.google.com → sign in with Google → accept terms if asked.
2. At the top, click the project dropdown → **New Project** → name `mindpulse` → **Create**.
3. Make sure "mindpulse" is selected in the dropdown.
4. In the top search bar, type **OAuth consent screen** and open it.
5. Choose **External** → **Create**.
6. Fill: App name = `MindPulse`, User support email = your email → **Save and Continue** (leave scopes empty, leave test users empty) → finish the wizard.
7. Left menu: **Credentials** → **+ Create Credentials** → **OAuth client ID**.
8. Application type: **Web application**. Name: `mindpulse-local`.
9. Under **Authorized JavaScript origins**: click **+ Add URI**, type `http://localhost:3000`.
10. Under **Authorized redirect URIs**: click **+ Add URI**, type `http://localhost:3000/api/auth/google/callback`.
11. Click **Create**. A popup shows **Client ID** and **Client Secret** — copy both.
12. Open `backend/.env` and set:
    ```
    GOOGLE_CLIENT_ID=<client id>
    GOOGLE_CLIENT_SECRET=<client secret>
    ```
13. Open `frontend/.env.local` (create the file if it doesn't exist) and set:
    ```
    NEXT_PUBLIC_GOOGLE_CLIENT_ID=<same client id>
    ```
14. Restart backend AND frontend.
15. If the button says the app is "in testing": go back to the OAuth consent screen and click **Publish app**, or add your own email under **Test users** first — either works for you.

---

## C. Google Colab cloud training (optional, for training the model in the cloud)

1. Open https://colab.research.google.com → sign in with Google → **New notebook**.
2. Upload this project's `training/` folder to Google Drive (drive.google.com → My Drive → drag the folder in).
3. In the notebook, run the commands listed in `training/README.md` under "Google Colab".
4. When it finishes, download the `artifacts` folder it created.
5. To make the app use it: put `model_xgb.joblib` and `global_stats.joblib` somewhere public (a GitHub Release, or a Google Drive link), then set in `backend/.env`:
   ```
   MINDPULSE_MODEL_URL=<direct download link to model_xgb.joblib>
   MINDPULSE_STATS_URL=<direct download link to global_stats.joblib>
   ```

---

## D. Security housekeeping (2 minutes)

1. **Revoke the old Kaggle token**: open https://www.kaggle.com/settings → API → **Revoke** (it was shared in a chat earlier).
2. **Set a strong app-secret key**: open https://randomkeygen.com → copy a 48-character key → in `backend/.env` set:
   ```
   JWT_SECRET_KEY=<the key>
   ```

---

## What's already done (so you know the base works)

- Backend: all 22 API endpoints live-tested, plus WebSocket and SSE
- Chat AI works with real Gemini answers (your key, model fixed)
- Extended features (chat/wellness/focus) work on local storage — they switch to Supabase automatically after step A
- Model: honest evaluation, per-user calibration, telemetry + EMA loop
- Everything pushed to GitHub
