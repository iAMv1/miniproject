# MindPulse Operations Runbook

MindPulse is an **experimental, non-diagnostic behavioral signal product**. It estimates changes in interaction behavior and must not be represented as clinical stress detection.

## 1. Local startup

Create a server environment with Python 3.11, install only `backend/requirements.txt`, and set a local signing secret. Desktop event capture is optional and must use the separate `backend/desktop-requirements.txt`; it is not a web-server dependency.

```bash
cd backend
export JWT_SECRET_KEY="replace-with-a-long-local-secret"
export ALLOWED_ORIGINS="http://localhost:3000"
python -m pip install -r requirements.txt
PYTHONPATH=. python -m uvicorn app.main:app --host 0.0.0.0 --port 5000
```

In a second terminal, install the locked frontend dependencies and start the Next.js app.

```bash
cd frontend
npm ci
export NEXT_PUBLIC_API_URL="http://localhost:5000/api/v1"
export NEXT_PUBLIC_WS_URL="ws://localhost:5000/api/v1/ws/stress"
export NEXTAUTH_SECRET="replace-with-a-long-local-secret"
npm run dev
```

Verify `GET /api/v1/health` returns HTTP 200 before testing authentication and live tracking.

## 2. Required production configuration

| Variable | Required | Purpose |
|---|---:|---|
| `JWT_SECRET_KEY` | Yes | Signs backend access tokens. Use a unique high-entropy secret per environment. |
| `NEXTAUTH_SECRET` | Yes | Signs frontend auth sessions. Use a unique high-entropy secret per environment. |
| `ALLOWED_ORIGINS` | Yes | Comma-separated approved frontend origins. Never leave broad wildcards in production. |
| `NEXT_PUBLIC_API_URL` | Yes | HTTPS backend API URL. |
| `NEXT_PUBLIC_WS_URL` | Yes | Secure WebSocket URL (`wss://`) for the backend stream. |
| `MINDPULSE_MODEL_URL` / `MINDPULSE_STATS_URL` | Recommended | Versioned model and preprocessing artifacts with verified provenance. |

Do not commit `.env` files or use the build-only secret emitted by the frontend build wrapper as a deployed secret.

## 3. Behavioral signal states

| State | Meaning | Product behavior |
|---|---|---|
| `READY` | There is measured activity and a calibrated personal baseline. | Show the personalized behavioral trend and optional guidance. |
| `CALIBRATING` | Activity is present, but personal calibration is incomplete. | Show an early trend only; prompt for context or calibration. |
| `INSUFFICIENT_ACTIVITY` | The time window lacks enough observable interaction activity. | Abstain. Do not infer relaxation, stress, or productivity. |
| `UNAVAILABLE` | Model loading or service availability is incomplete. | Show service status and avoid user-facing conclusions. |

The legacy three-class value remains for compatibility. The product-facing interpretation should prefer `signal_state` and `deviation_level`.

## 4. Privacy operations

The authenticated privacy controls provide two server-backed functions.

| Endpoint | Result |
|---|---|
| `GET /api/v1/privacy/export` | Exports locally stored history, interventions, privacy-minimized telemetry metadata, and EMA check-ins as JSON. Account credentials are excluded. |
| `DELETE /api/v1/privacy/data` | Deletes the same behavioral data and the per-user baseline while retaining the account so the user can continue using the product. |

The browser pause control stops local feature collection on that device. It does not delete stored data and does not control separately running desktop collectors; those must honor the same user preference before transmission.

## 5. Release checklist

1. Run `PYTHONPATH=backend pytest -q backend/tests`.
2. Run `python -m compileall -q backend`.
3. Run `npm ci`, `npm run lint`, `npx --no-install tsc --noEmit`, and `npm run build` in `frontend/`.
4. Configure unique production secrets and narrow CORS origins.
5. Verify health, signup/login, authenticated inference, WebSocket updates, privacy export, and privacy deletion in staging.
6. Confirm `signal_state` is surfaced in the tracking UI before enabling automated guidance.
7. Validate the model artifact manifest, hashes, dataset provenance, and held-out metrics before changing model claims.
8. Monitor application logs for model-load failures and unexpected authentication errors after release.

## 6. Known boundaries

The staged SWELL-KW mapping uses a small, non-clinical dataset and the per-minute source lacks several event-level keyboard features. Those fields are documented in the artifact manifest. Better model claims require real product-native EMA labels, subject-independent validation, and a measured full feature pipeline—not a larger neural architecture alone.
