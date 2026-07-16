# TrustMesh

> Verification and anti-manipulation trust layer for AI-to-AI negotiation.

TrustMesh sits between two LLM agents (a **Buyer** and a **Seller**) negotiating a B2B procurement deal. A **Trust Engine** monitors every exchange for manipulation, broken commitments, and policy violations. A **Cryptographic Ledger** produces a tamper-evident, Ed25519-signed record of each message. A **React dashboard** with live WebSocket streaming shows everything in real time.

---

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│  Buyer Agent (LLM)  ◄──── Negotiation ────►  Seller Agent (LLM) │
│         │                                        │              │
│         ▼                                        ▼              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Trust Engine — detects manipulation, policy violations,  │  │
│  │  broken commitments, and currency swaps                   │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Cryptographic Ledger — Ed25519 signatures, SHA-256      │  │
│  │  hash chain, append-only, tamper-evident                  │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Dashboard — React + Vite + Tailwind + Recharts           │  │
│  │  Real-time price chart, trust scores, violations,         │  │
│  │  ledger viewer via WebSocket                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

For a detailed phase-by-phase walkthrough, see **[docs/PHASES.md](docs/PHASES.md)**.

---

## Quick Start

### Option A — Run locally

**Prerequisites:** Python 3.11+, Node.js 18+

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add API keys if using live LLMs
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

- **Backend:** http://localhost:8000 (API docs at /docs)
- **Frontend:** http://localhost:5173

### Option B — Docker

```bash
docker compose up --build
```

- **Frontend:** http://localhost
- **Backend API:** http://localhost:8000

---

## Demo Seed Script

Populate the database with realistic negotiation sessions so the dashboard
shows trust scores, violations, and ledger entries instantly — no live LLM
calls required.

```bash
cd backend
python scripts/seed_demo_data.py
```

This creates 4 sessions:

| # | Scenario | Expected Trust Outcome |
|---|----------|----------------------|
| 1 | Clean deal — fair negotiation, both within bounds | No violations, high scores |
| 2 | Budget exceeded — buyer offers above cap | PolicyDeviationFlagger flags it |
| 3 | Broken commitment — seller moves backward on price | CommitmentConsistencyChecker flags it |
| 4 | Currency swap — seller switches to USD in an INR deal | PolicyDeviationFlagger + CommitmentConsistencyChecker flag it |

After seeding, restart the backend and open the dashboard — the trust panel,
violations list, and ledger panel will all be populated.

To re-seed, delete `backend/trustmesh.db` and run the script again.

---

## Benchmark Suite

The benchmark suite runs controlled negotiation scenarios and measures trust
engine accuracy. See `backend/scripts/` for available runners:

```bash
cd backend
python scripts/run_benchmark.py
python scripts/run_manipulation_holdout.py
```

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in as needed:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | For live LLM | (empty = mock) | Google Gemini API key |
| `GROQ_API_KEY` | For live LLM | (empty = mock) | Groq API key (fallback) |
| `APP_ENV` | No | `development` | `development` or `production` |
| `APP_HOST` | No | `0.0.0.0` | Server bind host |
| `APP_PORT` | No | `8000` | Server bind port |
| `LOG_LEVEL` | No | `info` | Logging level |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./trustmesh.db` | SQLAlchemy database URL |
| `ALLOWED_ORIGINS` | No | `http://localhost:5173,...` | CORS origins (comma-separated) |

> Never commit `.env` — it's already in `.gitignore`.

---

## Project Status

### Completed

| Phase | Component | Status |
|-------|-----------|--------|
| 0 | Foundation — project scaffolding, models, health check | ✅ Done |
| 1 | Agent Logic — Buyer & Seller LLM agents (Gemini / Groq / mock) | ✅ Done |
| 2 | Trust Engine — policy deviation, commitment consistency, manipulation detection | ✅ Done |
| 3 | Cryptographic Ledger — Ed25519 signing, SHA-256 hash chain, ledger endpoint | ✅ Done |
| 4 | WebSocket Live Stream — real-time dashboard updates, connection manager | ✅ Done |
| — | Dashboard — trust scores, violations, ledger viewer, price chart | ✅ Done |
| — | Docker deployment — backend + frontend compose setup | ✅ Done |
| — | Demo seed script — pre-populated realistic sessions | ✅ Done |

| — | ManipulationDetector — advanced price-swing / circular-pricing patterns | ✅ Done |
| — | Benchmark suite — automated accuracy measurement | ✅ Done |
| — | Phase 5 — Advanced Analysis (scoring, reports, export) | ✅ Done |

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + Uvicorn |
| Data Models | Pydantic v2 |
| Database | SQLite + SQLAlchemy async |
| LLM Agents | Gemini 2.5 Flash / Groq (mock fallback) |
| Trust Engine | Rule-based heuristics + LLM extraction |
| Crypto | `cryptography` — Ed25519, SHA-256 |
| Frontend | React 19 + Vite 8 + Tailwind CSS |
| Charts | Recharts |
| Live Updates | WebSocket (FastAPI) |

---

## Project Structure

```
TrustMesh/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── models.py            # Core Pydantic schemas
│   │   ├── db.py                # SQLAlchemy ORM + CRUD
│   │   ├── session_manager.py   # Negotiation coordinator
│   │   ├── llm_client.py        # Gemini / Groq client
│   │   ├── router.py            # API router aggregator
│   │   ├── routes/              # REST + WebSocket endpoints
│   │   ├── agents/              # Buyer & Seller LLM agents
│   │   ├── crypto/              # Ed25519 signing + hash chain
│   │   └── trust/               # Trust engine + detectors
│   ├── scripts/                 # Seed + benchmark runners
│   ├── tests/                   # Pytest test suite
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/                     # React app
│   ├── nginx.conf               # Production reverse proxy
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
├── docs/                        # Phase-by-phase guides
├── docker-compose.yml
└── README.md
```

---

## License

MIT
