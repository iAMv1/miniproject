# MindPulse — Desktop Agent (full-OS tracking → Supabase)

Global keyboard/mouse/app-switch capture that feeds the same MindPulse
pipeline as the browser collector — but across your **entire OS**, not just
one browser tab.

## What it does

1. Hooks global input with `pynput` (Windows/macOS/Linux).
2. Every 30s builds a feature window with the **same math and units** as the
   browser collector (`frontend/src/lib/features.ts`): typing rhythm (ms),
   mouse speed (px/s), clicks/rage-clicks, scroll, app-switch frequency,
   switch entropy, session fragmentation.
3. Calls the `infer` edge function → score/level.
4. Persists to `stress_history`, `focus_snapshots`, `telemetry_events`
   (RLS-scoped to **your** account via your JWT).
5. Prunes `stress_history` older than 90 days on first successful window.

Privacy: timings + key *categories* + app-name **hashes** only. Never typed
content, never app names in clear text.

## Setup

```bash
cd backend/desktop_agent
pip install -r requirements.txt

# 1. Web app → /privacy → "Desktop agent pairing" → copy refresh token
python pair.py --anon-key <NEXT_PUBLIC_SUPABASE_ANON_KEY> --refresh-token <token>

# 2. Run (leave it running — it survives in the background)
python agent.py
```

The agent auto-refreshes the session (rotated refresh token is saved back to
`config.json`). On auth failure it logs and keeps trying.

## Limitations (honest)

- macOS/Linux may require accessibility/input-monitoring permission for
  `pynput` hooks.
- The live gauge on `/tracking` shows **browser-tab** windows; desktop
  windows land in History / Focus / Calibration / stats. (Live desktop→web
  streaming = Supabase Realtime, not wired yet.)
- Pause preference (browser) is separate; `touch agent.pause` isn't
  implemented — Ctrl+C stops the agent.

## Tests

```bash
python -m pytest tests/test_desktop_features.py -q   # parity vs browser math
```
