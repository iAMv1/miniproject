# Deployment (Railway backend + Vercel frontend)

This project is set up to deploy:

- `backend/` to **Railway**
- `frontend/` to **Vercel**

## 1) Deploy backend to Railway

1. Create a Railway project from this repository.
2. Add a service and set the service root directory to `backend`.
3. Deploy using Dockerfile auto-detection.
4. Configure environment variables in Railway:
   - Required:
     - `JWT_SECRET_KEY`
     - `ALLOWED_ORIGINS` (set to your Vercel frontend URL)
     - `SUPABASE_URL`
     - `SUPABASE_ANON_KEY`
   - Optional:
     - `SUPABASE_SERVICE_KEY`
     - `OPENAI_API_KEY` or `GEMINI_API_KEY`
     - `LOG_LEVEL`
     - `GOOGLE_REDIRECT_URI`
     - `FRONTEND_CALLBACK_URL`
5. Verify health endpoint:
   - `https://<railway-backend-domain>/api/v1/health`

## 2) Deploy frontend to Vercel

1. Import this repository in Vercel.
2. Set the project root directory to `frontend`.
3. Configure environment variables in Vercel:
   - Required:
     - `NEXTAUTH_SECRET`
     - `NEXT_PUBLIC_API_URL=https://<railway-backend-domain>/api/v1`
     - `NEXT_PUBLIC_WS_URL=wss://<railway-backend-domain>/api/v1/ws/stress`
       - This path matches the current frontend stress stream hook. If you change backend WebSocket routing, update this value accordingly.
   - Optional:
     - `GOOGLE_CLIENT_ID`
     - `GOOGLE_CLIENT_SECRET`
4. Deploy the project.

## 3) Cross-service configuration

After both deployments are live:

1. Update Railway `ALLOWED_ORIGINS` to your Vercel URL, for example:
   - `ALLOWED_ORIGINS=https://<vercel-frontend-domain>`
2. If Google OAuth is enabled, set Railway values:
   - `GOOGLE_REDIRECT_URI=https://<vercel-frontend-domain>/api/auth/google/callback`
   - `FRONTEND_CALLBACK_URL=https://<vercel-frontend-domain>/auth/callback`
3. Redeploy services if environment variables changed.

## 4) Optional persistence

If model artifacts must persist across restarts, attach a Railway volume at:

- `/app/app/ml/artifacts`
