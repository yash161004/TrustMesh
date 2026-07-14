# Phase 0 — Foundation ✅ Done

> **Project scaffolding** — the skeleton of the entire project. Think of it as laying the foundation, framing the walls, and running the electrical wiring before any rooms are finished.

**📅 Status:** Complete | **🔗 Back to overview:** [PHASES.md](./PHASES.md)

---

## What Was Built

| Component | What It Does |
|-----------|-------------|
| **FastAPI Backend** | Web server that handles API requests (like a restaurant waiter) |
| **Pydantic Models** | Rules for what a negotiation message looks like (like a form template) |
| **Health Check** | A simple endpoint to see if the server is alive (`GET /api/v1/health`) |
| **React Frontend** | A beautiful dashboard showing the system status |
| **Configuration** | Environment variables, CORS settings, database URL |
| **Project Structure** | Organized folders, Git repo, README |

---

## How It Works

```
User's Browser ────GET /api/v1/health────► FastAPI Server
                                            │
         ◄────{"status":"ok",...}────────────┘
```

1. You open the dashboard in your browser
2. The dashboard calls the health endpoint
3. The server responds with "I'm alive!" and version info
4. The dashboard displays stats, charts, and the phase roadmap

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/main.py` | Creates and configures the FastAPI app |
| `backend/app/config.py` | Reads settings from environment variables |
| `backend/app/models.py` | Defines `NegotiationMessage` and `NegotiationSession` schemas |
| `backend/app/router.py` | Connects API routes to the app |
| `backend/app/routes/health.py` | The health check endpoint |
| `frontend/src/App.jsx` | The main dashboard UI |

---

## Tech Used

- **FastAPI** — Python web framework
- **Pydantic v2** — Data validation
- **React + Vite** — Frontend framework
- **Tailwind CSS** — Styling
- **Recharts** — Charts & graphs
