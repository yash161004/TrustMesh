# TrustMesh — Production Deployment Guide

*Step-by-step instructions for deploying the TrustMesh Backend (Render/Docker) and Enterprise Frontend (Vercel/Astro SSR).*

---

## 1. Architecture Overview

- **Backend:** FastAPI application running on Python 3.10+ containerized with Docker or deployed to Render Web Service.
- **Database:** Managed PostgreSQL 15 instance (Render / Supabase).
- **Background Cron:** Periodic integrity sweep worker executing hourly (`0 * * * *`).
- **Frontend:** Astro SSR web app with React components deployed to Vercel or Node.js SSR host.
- **Authentication:** Clerk OAuth / JWT multi-tenant authentication.

---

## 2. Environment Variables Matrix

### Backend Environment Variables (`backend/.env`)

| Variable | Description | Example / Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@ep-host:5432/trustmesh` |
| `CLERK_SECRET_KEY` | Clerk Backend Secret Key for JWT validation | `sk_live_...` |
| `CLERK_ISSUER_URL` | Clerk JWT Issuer Domain | `https://clerk.yourdomain.com` |
| `ALLOWED_ORIGINS` | CORS origins for frontend domain | `https://trustmesh.vercel.app` |
| `TAMPER_ALERT_WEBHOOK_URL` | Webhook URL for ledger tamper alerts | `https://hooks.slack.com/services/...` |
| `GEMINI_API_KEY` | Optional: Gemini LLM API key | `AIzaSy...` |
| `GROQ_API_KEY` | Optional: Groq LLM API key | `gsk_...` |

### Frontend Environment Variables (`web-astro/.env`)

| Variable | Description | Example / Default |
|---|---|---|
| `PUBLIC_API_BASE_URL` | Production FastAPI backend URL | `https://trustmesh-backend.onrender.com` |
| `PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk Frontend Publishable Key | `pk_live_...` |
| `PUBLIC_REPO_URL` | GitHub repository URL for commit links | `https://github.com/yash161004/TrustMesh` |

---

## 3. Deploying Backend to Render

1. **Connect Repository:** Link your `yash161004/TrustMesh` repository in the Render Dashboard.
2. **Apply Render Blueprint:** Render will auto-detect `render.yaml` which provisions:
   - `trustmesh-backend` (Web Service)
   - `trustmesh-db` (Postgres 15 Database)
   - `trustmesh-ledger-sweep` (Cron Job executing `0 * * * *`)
3. **Database Migration:** On first deploy, Alembic migrations run automatically:
   ```bash
   alembic upgrade head
   ```
4. **Health Check:** Verify API status:
   ```bash
   curl https://trustmesh-backend.onrender.com/health
   ```

---

## 4. Deploying Frontend to Vercel

1. **Connect Repository:** Import the `web-astro` subdirectory in Vercel.
2. **Framework Preset:** Select **Astro** (Vercel Adapter `@astrojs/vercel` is pre-configured in `astro.config.mjs`).
3. **Set Environment Variables:** Configure `PUBLIC_API_BASE_URL` and `PUBLIC_CLERK_PUBLISHABLE_KEY`.
4. **Deploy:** Click **Deploy**. Vercel will build the SSR serverless function entrypoints.

---

## 5. Post-Deployment Integrity & Health Verification

- **API Endpoint Check:** `GET /api/v1/eval-results/latest` returns holdout accuracy & precision metrics.
- **Fleet Anomaly Endpoint:** `GET /api/v1/fleet/anomalies` returns org-scoped agent outlier z-scores.
- **Ledger Sweep Verification:** Check logs of `trustmesh-ledger-sweep` cron worker on Render to ensure hourly database integrity sweeps run cleanly.
