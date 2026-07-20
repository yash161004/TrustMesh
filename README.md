# TrustMesh

> The Impartial Referee for the Agentic AI Economy.

As we enter the era of **Agentic AI**, autonomous agents will negotiate contracts, manage supply chains, and execute trades on our behalf. But how do we trust them to play by the rules?

**TrustMesh** is a trusted verification system that acts as an impartial referee for AI-to-AI (A2A) negotiations. It evaluates every exchange for manipulation, broken commitments, and policy violations, and records it all on a tamper-evident cryptographic ledger. 

📖 **[Read the 90-Second Demo Script](docs/DEMO_SCRIPT.md)**

---

## 📸 See it in Action

### Dashboard & Live Negotiation
![Dashboard Overview](docs/screenshots/01_dashboard_overview.png)

### Real-time Trust Engine & Flagging
When an agent attempts a manipulation tactic (e.g. faking scarcity), the Trust Engine flags it live.
![Trust Scores](docs/screenshots/02_trust_scores.png)
![Violations List](docs/screenshots/03_violations_list.png)

### Cryptographic Ledger (ERC-8004 Inspired)
Every message is signed via Ed25519 and hashed to form a tamper-evident chain. Note that "Ledger Verified" indicates true cryptographic chain integrity, independent of whether policy violations occurred during the negotiation.
![Ledger Verified](docs/screenshots/04_ledger_verified.png)
*(If anyone tampers with a signed message post-facto, the chain breaks instantly.)*
![Ledger Broken](docs/screenshots/05_ledger_broken.png)

---

## Architecture & Trust Story

TrustMesh evaluates its own internal agents, separating the **negotiation logic** from the **verification logic**.

```text
┌───────────────────────────────────────────────────────────────┐
│                       TrustMesh Platform                      │
│                                                               │
│  [Buyer Agent] ◄──────── Negotiation ────────► [Seller Agent] │
│      (LLM)                                          (LLM)     │
│        │                                              │       │
│        ▼                                              ▼       │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ 1. Trust Engine (Evaluator)                              │ │
│  │    Detects manipulation, broken commitments, and policy  │ │
│  │    violations in real-time.                              │ │
│  └────────────────────────┬─────────────────────────────────┘ │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ 2. Cryptographic Ledger (Ed25519)                        │ │
│  │    Every message is digitally signed & hashed into an    │ │
│  │    append-only, tamper-evident chain.                    │ │
│  └────────────────────────┬─────────────────────────────────┘ │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ 3. Live Dashboard (WebSocket)                            │ │
│  │    Streams the negotiation, trust scores, and ledger     │ │
│  │    verification directly to the frontend UI.             │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

**The Trust Story:**
1. **Identity:** Every agent holds an **AgentCard** (ERC-8004 descriptor) binding its public key to its authorized capabilities.
2. **Behavioral Guardrails:** The **Trust Engine** analyzes every turn, heavily penalizing agents that use high-pressure manipulation tactics or deviate from budget constraints.
3. **Mathematical Proof:** Visibility is not enough for enterprise compliance. TrustMesh provides cryptographic proof that the exact negotiation history is mathematically immutable.

For a detailed phase-by-phase walkthrough of what was built, see **[docs/PHASES.md](docs/PHASES.md)**.

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
cd web-astro
npm install
npm run dev
```

- **Backend:** http://localhost:8000 (API docs at /docs)
- **Frontend:** http://localhost:4321

### Option B — Docker

```bash
docker compose up --build
```

- **Frontend:** http://localhost
- **Backend API:** http://localhost:8000

---

## Webhooks & Ngrok (Development)

If you are using Clerk (or any other external service) with webhooks in local development, you must expose your local server using `ngrok`.

> **⚠️ IMPORTANT:** Ngrok free-tier accounts now receive a persistent static domain (e.g., `https://*.ngrok-free.dev`). While your URL won't change on restart, if your dev machine restarts or the ngrok process dies, webhooks will **silently fail** because Clerk will try to hit the dead tunnel.

**To ensure webhooks work:**
1. Keep ngrok running: `ngrok http 8000` (or `ngrok.cmd http 8000` on Windows)
2. Ensure your backend server is also running on port 8000.
3. Ensure your Clerk Webhook Endpoint URL includes the full path (e.g., `https://scabby-wobble-unblock.ngrok-free.dev/api/v1/webhooks/clerk`).

You can use the included health-check script to verify your tunnel is up:
```bash
python backend/scripts/check_ngrok.py
```

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
| `OPENROUTER_API_KEY` | For live LLM | (empty = mock) | OpenRouter API key (tie-break vote) |
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
| Frontend | Astro + Tailwind CSS v4 |
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
├── web-astro/
│   ├── src/                     # Astro app
│   ├── public/
│   ├── Dockerfile
│   ├── package.json
│   └── astro.config.mjs
├── docs/                        # Phase-by-phase guides
├── docker-compose.yml
└── README.md
```

---

## License

MIT
