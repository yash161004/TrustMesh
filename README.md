# TrustMesh 🛡️

> **Phase 0 — Foundation** · Verification and anti-manipulation trust layer for AI-to-AI negotiation.

TrustMesh sits between two independent LLM agents (a **Buyer** and a **Seller**) that negotiate a B2B procurement deal in real time. A **Trust Engine** monitors every exchange for manipulation, broken commitments, and policy violations. A **Cryptographic Ledger** produces a tamper-evident record of each message, signed with Ed25519 keys.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        TrustMesh                            │
│                                                             │
│  ┌──────────────┐     WebSocket      ┌──────────────────┐  │
│  │  Buyer Agent │◄──────────────────►│   Seller Agent   │  │
│  │  (Gemini /   │        │           │   (Gemini /      │  │
│  │   Groq LLM)  │        ▼           │    Groq LLM)     │  │
│  └──────────────┘  ┌─────────────┐  └──────────────────┘  │
│                    │ Trust Engine│                          │
│                    │ · Manip. det│                          │
│                    │ · Commit ck │                          │
│                    │ · Policy chk│                          │
│                    └──────┬──────┘                          │
│                           │                                 │
│                    ┌──────▼──────┐                          │
│                    │ Crypto Ledg │  Ed25519 signatures      │
│                    │ (SQLite)    │  SHA-256 chain hashes    │
│                    └─────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

### Component Map

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend API** | FastAPI + Uvicorn | REST + WebSocket server |
| **Data Models** | Pydantic v2 | Validation of negotiation messages |
| **Agent Logic** | Gemini 2.5 Flash / Groq | LLM-powered negotiation agents *(Phase 1+)* |
| **Trust Engine** | Python (heuristics + LLM) | Manipulation & policy detection *(Phase 2+)* |
| **Crypto Ledger** | `cryptography` Ed25519 | Tamper-evident message chain *(Phase 3+)* |
| **Database** | SQLite + SQLAlchemy async | Local dev persistence |
| **Frontend** | React + Vite + Tailwind | Dashboard & monitoring UI |

---

## Project Structure

```
TrustMesh/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI app factory
│   │   ├── config.py        # Settings (pydantic-settings)
│   │   ├── models.py        # Core Pydantic schemas
│   │   ├── router.py        # API router aggregator
│   │   └── routes/
│   │       └── health.py    # GET /api/v1/health
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── .gitignore
└── README.md
```

---

## Phase Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **0** | Foundation — project scaffolding | ✅ **Current** |
| **1** | Agent Logic — Buyer & Seller LLM agents | 🔜 |
| **2** | Trust Engine — manipulation & policy detection | 🔜 |
| **3** | Cryptographic Ledger — Ed25519 signing & verification | 🔜 |
| **4** | WebSocket Live Stream — real-time dashboard | 🔜 |
| **5** | Advanced Analysis — scoring, reports, export | 🔜 |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

---

### 1 · Clone & enter the repo

```bash
git clone <your-repo-url>
cd TrustMesh
```

---

### 2 · Backend setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env file and add your API keys
cp .env.example .env
# Edit .env — add GEMINI_API_KEY and GROQ_API_KEY

# Run the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be live at: **http://localhost:8000**

- Health check: `GET http://localhost:8000/api/v1/health`
- Interactive docs: **http://localhost:8000/docs**
- ReDoc: **http://localhost:8000/redoc**

---

### 3 · Frontend setup

```bash
cd frontend

npm install
npm run dev
```

Frontend will be live at: **http://localhost:5173**

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Phase 1+ | Google Gemini API key (AI Studio) |
| `GROQ_API_KEY` | Phase 1+ | Groq API key (fallback LLM) |
| `APP_ENV` | No | `development` / `production` |
| `APP_HOST` | No | Server bind host (default `0.0.0.0`) |
| `APP_PORT` | No | Server bind port (default `8000`) |
| `DATABASE_URL` | No | SQLAlchemy URL (default SQLite) |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins |

> ⚠️ **Never commit your `.env` file.** The `.gitignore` already excludes it.

---

## API Reference (Phase 0)

### `GET /api/v1/health`

Returns service health and metadata.

**Response 200:**
```json
{
  "status": "ok",
  "service": "TrustMesh Backend",
  "phase": "0 — Foundation",
  "timestamp": "2026-07-14T07:00:00.000000+00:00",
  "version": "0.1.0"
}
```

---

## Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** — modern, high-performance async web framework
- **[Pydantic v2](https://docs.pydantic.dev/)** — data validation and serialisation
- **[SQLAlchemy 2 + aiosqlite](https://docs.sqlalchemy.org/)** — async ORM (expanded in later phases)
- **[Google Gemini 2.5 Flash](https://ai.google.dev/)** — primary LLM for agents
- **[Groq](https://groq.com/)** — ultra-fast LLM inference (fallback)
- **[React + Vite](https://vitejs.dev/)** — lightning-fast frontend tooling
- **[Tailwind CSS](https://tailwindcss.com/)** — utility-first CSS framework
- **[Recharts](https://recharts.org/)** — composable charting for the dashboard
- **[cryptography](https://cryptography.io/)** — Ed25519 signing (Phase 3+)

---

## Contributing

This is currently a solo research project. Contributions welcome once the core architecture stabilises in Phase 2.

---

## License

MIT © TrustMesh Contributors
