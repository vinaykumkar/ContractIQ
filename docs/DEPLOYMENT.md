# ContractIQ — Deployment Notes (documentation only)

ContractIQ is designed as a **local-first** application. This document sketches
how it *could* be deployed later — nothing is deployed automatically and the
local SQLite setup remains the default.

## Production single-port serving (IMPLEMENTED)

The backend serves a built frontend automatically: after `cd frontend && npm run build`,
FastAPI mounts `frontend/dist` and falls back to `index.html` for non-`/api` GETs
(SPA deep links like `/contracts/<id>` resolve). One server, one port:

- `run_contractiq_prod.bat` — production launcher (http://127.0.0.1:8010; default
  port 8010, override with `BACKEND_PORT`. Port 8000 is avoided by default because
  another project on the development machine uses it)
- `run_contractiq.bat` — dev-server mode (unchanged, hot reload)
- The API stays under `/api`; `/docs` remains available.

## Frontend on GitHub Pages (free)

1. `cd frontend && npm run build` → static output in `frontend/dist/`.
2. Publish `dist/` (e.g. `gh-pages` branch or GitHub Pages action).
3. Set `VITE_API_BASE_URL=https://<your-backend-host>/api` at build time —
   it must point to the deployed backend, not localhost.
4. React Router uses `BrowserRouter`; for a sub-path deployment (e.g.
   `/contractiq/`) add a matching Vite `base` and a 404.html fallback so
   deep links like `/contracts/<id>` resolve.

## Backend on Render (free tier)

- **Start command:** `pip install -r backend/requirements.txt -r ml/requirements.txt
  && cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment variables:** `CONTRACTIQ_DB_URL` (see database note),
  `CONTRACTIQ_CORS_ORIGINS` (set to the Pages URL), `CONTRACTIQ_STORE_RAW_TEXT`.
- **Model storage:** upload/attach `ml/models/final/` (~128 MB) with the
  service, or fetch it from a Release asset at startup. Do **not** rely on a
  Hugging Face cache.
- **CPU inference limitation:** free tiers are CPU-only — expect ~80 s per
  median contract. Consider async workers or a paid GPU instance if needed.
- **Database persistence:** free instances have ephemeral disks — a local
  SQLite file is wiped on redeploy. Use a hosted PostgreSQL via
  `CONTRACTIQ_DB_URL` (SQLAlchemy URL-based config already supports it; the
  schema is portable, but a migration to a real migration tool is recommended
  before production use).

## What is intentionally NOT done

No PostgreSQL migration, no container image, no authentication, no horizontal
scaling — the local Windows package remains the primary deliverable.
