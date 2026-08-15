# MindPulse — Codebase Diagrams

Rendered on GitHub automatically. Paste any block into Claude for discussion.

## 1. System architecture (what talks to what)

```mermaid
flowchart LR
  subgraph Browser["Browser (Next.js on Vercel)"]
    P1["/tracking · Your Rhythm"]
    P2["/focus · /calibration · /wellness · /chat · /history"]
    C1["use-feature-collector<br/>keydown/mousemove/click/scroll<br/>+ visibilitychange/blur/focus<br/>(tab switches, away-gaps)"]
    F1["lib/features.ts<br/>23-feature vector, ms units"]
    H1["use-stress-stream<br/>poll 5s · dirty-flag dedup"]
  end

  subgraph Supabase["Supabase (the only backend)"]
    A1["Auth<br/>Google / email · JWT"]
    E1["Edge fn: infer<br/>JS tree-walker XGBoost<br/>rate limit 60/min/IP"]
    E2["Edge fn: chat<br/>JWT signature + role check<br/>Gemini proxy"]
    T1[("stress_history")]
    T2[("focus_snapshots")]
    T3[("user_baselines")]
    T4[("wellness_checkins")]
    T5[("wellness_insights")]
    T6[("interventions")]
    T7[("chat_sessions")]
    T8[("chat_messages")]
    T9[("ema_checkins")]
    T10[("telemetry_events")]
  end

  subgraph Desktop["Desktop agent (backend/desktop_agent)"]
    D1["pynput global hooks<br/>keys/mouse/scroll + app-switch hashes"]
    D2["30s windows · same math as features.ts<br/>(parity-tested)"]
    D3["supabase_api.py<br/>JWT auto-refresh · REST writes"]
  end

  G1["Gemini API"]

  C1 --> F1 --> H1
  H1 -- "POST /functions/v1/infer" --> E1
  E1 --> T1
  E1 --> T2
  E1 --> T3
  D1 --> D2 --> D3 -- "infer + inserts (RLS: user JWT)" --> E1
  D3 --> T1
  D3 --> T2
  D3 --> T10
  P1 --> C1
  P2 --> E2 -- "generateContent (GEMINI_API_KEY secret)" --> G1
  E2 --> T7
  E2 --> T8
  P2 --> T1
  P2 --> T2
  P2 --> T4
  P2 --> T6
  P2 --> T9
```

## 2. Browser telemetry data flow (the live gauge chain)

```mermaid
flowchart TD
  A["user types / moves mouse / switches tabs"] --> B["collector accumulates<br/>hold/flight (ms) · speeds (px/s) · clicks · switches · gaps"]
  B --> C{"30s window flush:<br/>any activity OR tab switch?"}
  C -- "no → discard (silence is never a signal)" --> A
  C -- "yes" --> D["computeFeatures (lib/features.ts)"]
  D --> E["wsRef.send({type:'features', …})"]
  E --> F["pollOnce (dirty-flag: infer only on new vector)"]
  F --> G["edge fn infer → score/level/deviation"]
  G --> H["gauge + live tiles + READY signal_state"]
  G --> I["insert stress_history (RLS)"]
  G --> J["insert focus_snapshots + deep_work_minutes"]
  G --> K["upsert user_baselines (mean/std/threshold)"]
  K --> L["calibration flips is_calibrated after ≥5 windows"]
```

## 3. Desktop agent (full-OS coverage) vs browser (tab-only)

```mermaid
flowchart LR
  subgraph BrowserOnly["Browser (web app)"]
    B1["events only fire while the tab is focused"]
    B2["tab switches counted via visibilitychange/blur"]
  end
  subgraph FullOS["Desktop agent"]
    D1["global pynput hooks — every app, every tab"]
    D2["app switches as privacy-safe sha256 hashes"]
    D3["idle share = session_fragmentation"]
  end
  subgraph Shared["Shared pipeline"]
    S1["same 23 features, same ms units (parity tests both sides)"]
    S2["infer edge fn → stress_history / focus_snapshots / telemetry_events"]
  end
  B1 --> B2 --> S1
  D1 --> D2 --> D3 --> S1
  S1 --> S2
```

## 4. Data tables + RLS (who can touch what)

```mermaid
flowchart LR
  subgraph Tables["public schema — every table RLS-scoped to auth.uid()"]
    T1["stress_history<br/>score · level · deviation · features"]
    T2["focus_snapshots<br/>focus_score · context_switches · deep_work_minutes"]
    T3["user_baselines<br/>mean/std jsonb · threshold (seeded per window)"]
    T4["wellness_checkins<br/>unique(user_id, check_date) upsert"]
    T5["wellness_insights<br/>currently empty — journal derives from check-ins"]
    T6["interventions · chat_sessions · chat_messages · ema_checkins · telemetry_events"]
  end
  W["Browser collector"] --> T1
  W --> T2
  W --> T3
  D["Desktop agent"] --> T1
  D --> T2
  D --> T6
  U["user JWT (RLS: auth.uid() = user_id)"] -.all writes pass through.-> Tables
  A["anon key"] --x Tables
  A -- "infer (public model, rate-limited)" --> E["edge fn infer"]
  A --x E2["edge fn chat → 401 (JWT signature + role=authenticated)"]
```

## 5. Page → hook → API map

```mermaid
flowchart LR
  T["/tracking"] --> H["use-stress-stream + use-feature-collector"]
  F["/focus"] --> A["api.getFocusState → focus_snapshots"]
  C["/calibration"] --> A2["api.calibration → user_baselines + history"]
  W["/wellness"] --> A3["api.getWellnessJournal → derived patterns from check-ins"]
  CH["/chat"] --> A4["api.createChatSession + chat edge fn"]
  H["/history"] --> A5["api.history → stress_history (21-day trend)"]
  A["stats/forecast"] --> T1["stress_history"]
```

## 6. Security posture (what was fixed, what holds)

```mermaid
flowchart LR
  S1["chat_messages RLS using(true) — CROSS-USER READ/WRITE"] --> S1f["user_id column + auth.uid()=user_id policy ✅"]
  S2["chat fn open to anon key (quota theft)"] --> S2f["in-function JWT signature verify + role=authenticated → anon 401 ✅"]
  S3["frontend/.env.local committed"] --> S3f["untracked + gitignored ✅"]
  S4["infer unauthenticated"] --> S4f["rate limit 60/min/IP (per-instance window) 🟡"]
  S5["config.json (desktop agent refresh token)"] --> S5f["gitignored ✅"]
```

## 7. Known open items (for discussion)

1. Live gauge shows browser windows only — desktop windows land in History/Focus/Calibration. Live desktop→web streaming = Supabase Realtime (not wired).
2. `wellness_insights` table has no generator — journal derives client-side instead.
3. `infer` rate limit is per-instance memory (no global counter on free tier).
4. Frontend tests: vitest on `lib/features.ts` only (3 tests). Backend: 11 tests incl. agent parity.
5. Legacy FastAPI backend + Tauri shell still in repo — not part of the deployed stack.
