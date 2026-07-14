# TrustMesh — Phase-by-Phase Guide 🛡️

> **An easy-to-understand walkthrough of what each phase does, how it works, and how everything connects.**

---

## Table of Contents

1. [How the Whole System Works (Big Picture)](#how-the-whole-system-works-big-picture)
2. [Phase 0 — Foundation ✅ Done](#phase-0--foundation--done)
3. [Phase 1 — Agent Logic 🟢 Active](#phase-1--agent-logic--active)
4. [Phase 2 — Trust Engine 🔜 Coming](#phase-2--trust-engine--coming)
5. [Phase 3 — Cryptographic Ledger 🔜 Coming](#phase-3--cryptographic-ledger--coming)
6. [Phase 4 — WebSocket Live Stream 🔜 Coming](#phase-4--websocket-live-stream--coming)
7. [Phase 5 — Advanced Analysis 🔜 Coming](#phase-5--advanced-analysis--coming)
8. [How All Phases Connect](#how-all-phases-connect)
9. [File Map](#file-map)

---

## How the Whole System Works (Big Picture)

TrustMesh is like a **trusted referee** between two AI agents (a Buyer and a Seller) who negotiate a business deal.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TrustMesh System                            │
│                                                                     │
│  ┌──────────────┐        Negotiation         ┌──────────────────┐  │
│  │  Buyer Agent │◄──────────────────────────►│   Seller Agent   │  │
│  │  (LLM)       │    ─── OFFER / COUNTER ──► │   (LLM)          │  │
│  │              │    ◄── ACCEPT / REJECT ─── │                  │  │
│  └──────┬───────┘                            └───────┬──────────┘  │
│         │                                            │              │
│         ▼                                            ▼              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Trust Engine (Phase 2)                     │  │
│  │  · Checks for manipulation and lies                          │  │
│  │  · Verifies agents keep their commitments                    │  │
│  │  · Flags policy violations                                   │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                      │
│                             ▼                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │               Cryptographic Ledger (Phase 3)                  │  │
│  │  · Every message is digitally signed (Ed25519)               │  │
│  │  · Messages are chained together (tamper-evident)            │  │
│  │  · Anyone can verify the full history                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Dashboard (Frontend — React + Vite)              │  │
│  │  · See negotiation happening live (Phase 4)                  │  │
│  │  · View trust scores and reports (Phase 5)                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Simple Analogy

Think of it like **two people negotiating a car sale with a notary watching**:

| Real World | TrustMesh |
|------------|-----------|
| Buyer | `BuyerAgent` (wants lowest price) |
| Seller | `SellerAgent` (wants highest price) |
| The conversation | `NegotiationMessage` (offers, counters, accept/reject) |
| Notary watching for tricks | **Trust Engine** (Phase 2) |
| Signed contract | **Crypto Ledger** (Phase 3) |
| Live video feed | **WebSocket Stream** (Phase 4) |
| Final report | **Analysis Dashboard** (Phase 5) |

---

## Phase 0 — Foundation ✅ Done

### What It Is
The **scaffolding** — the skeleton of the entire project. Think of it as laying the foundation, framing the walls, and running the electrical wiring before any rooms are finished.

### What Was Built

| Component | What It Does |
|-----------|-------------|
| **FastAPI Backend** | Web server that handles API requests (like a restaurant waiter) |
| **Pydantic Models** | Rules for what a negotiation message looks like (like a form template) |
| **Health Check** | A simple endpoint to see if the server is alive (`GET /api/v1/health`) |
| **React Frontend** | A beautiful dashboard showing the system status |
| **Configuration** | Environment variables, CORS settings, database URL |
| **Project Structure** | Organized folders, Git repo, README |

### How It Works

```
User's Browser ────GET /api/v1/health────► FastAPI Server
                                            │
         ◄────{"status":"ok",...}────────────┘
```

1. You open the dashboard in your browser
2. The dashboard calls the health endpoint
3. The server responds with "I'm alive!" and version info
4. The dashboard displays stats, charts, and the phase roadmap

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/main.py` | Creates and configures the FastAPI app |
| `backend/app/config.py` | Reads settings from environment variables |
| `backend/app/models.py` | Defines `NegotiationMessage` and `NegotiationSession` schemas |
| `backend/app/router.py` | Connects API routes to the app |
| `backend/app/routes/health.py` | The health check endpoint |
| `frontend/src/App.jsx` | The main dashboard UI |

---

## Phase 1 — Agent Logic 🟢 Active

### What It Is
This phase brings the AI agents to life! Now instead of just a health check, the system can actually **run negotiations** between two AI-powered agents.

### What Was Built

| Component | What It Does |
|-----------|-------------|
| **BuyerAgent** | AI agent that tries to buy at the lowest price |
| **SellerAgent** | AI agent that tries to sell at the highest price |
| **BaseAgent** | Shared logic for both agents (message history, LLM calls) |
| **LLM Client** | Connects to Gemini or Groq AI APIs |
| **Session Manager** | Coordinates the back-and-forth negotiation |
| **Session API** | REST endpoints to create, start, and run negotiations |
| **Mock Responses** | Works without API keys (returns simulated data) |

### How It Works

```
1. CREATE SESSION
   POST /api/v1/sessions
   → Creates buyer + seller agents, gives them context

2. START NEGOTIATION
   POST /api/v1/sessions/{id}/start
   → Buyer makes first offer

3. NEGOTIATE (auto-run)
   POST /api/v1/sessions/{id}/turn
   → Agents go back-and-forth until they agree or give up

4. VIEW RESULTS
   GET /api/v1/sessions/{id}
   → See the full conversation and outcome
```

### The Negotiation Flow (Step by Step)

```
BUYER                          SELLER
  │                               │
  ├── OFFER $212.50 ─────────────►│
  │                               ├── COUNTER $250.00
  │◄── COUNTER $195.00 ──────────┤
  │                               │
  ├── COUNTER $210.00 ───────────►│
  │                               ├── COUNTER $205.00
  │◄── COUNTER $200.00 ──────────┤
  │                               │
  ├── ACCEPT $202.00 ────────────►│
  │                               ├── ACCEPT ✅
  │                               │   DEAL DONE!
```

### How the Agents Work

**Each agent has:**
1. A **system prompt** — instructions telling the AI how to behave (buyer mindset vs seller mindset)
2. **Memory** — keeps track of the last 10 messages
3. **Strategy** — knows when to raise/lower prices, when to accept, when to walk away
4. **Fallback** — if the AI gives a bad response, it has a backup plan

**BuyerAgent Strategy:**
- Start 15% below asking price
- Increase slowly each turn
- Accept if price ≤ target price
- Maximum budget = configurable

**SellerAgent Strategy:**
- Start at asking price
- Decrease slowly each turn
- Accept if price ≥ floor price
- Won't go below minimum

### Working Without API Keys

If you haven't set `GEMINI_API_KEY` or `GROQ_API_KEY`, the system uses **mock mode**:
- Simulates realistic negotiation responses
- Works completely offline
- Perfect for testing and development

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/agents/base.py` | Abstract base class for all negotiation agents |
| `backend/app/agents/buyer.py` | Buyer agent with procurement strategy |
| `backend/app/agents/seller.py` | Seller agent with sales strategy |
| `backend/app/agents/__init__.py` | Exports agent classes |
| `backend/app/llm_client.py` | Connects to Gemini / Groq APIs (with mock fallback) |
| `backend/app/session_manager.py` | Coordinates turn-by-turn negotiation |
| `backend/app/routes/sessions.py` | API endpoints for session management |

---

## Phase 2 — Trust Engine 🔜 Coming

### What It Will Do
The Trust Engine is the **integrity checker**. It watches every message exchanged between agents and looks for:
- **Manipulation** — is an agent lying or being deceptive?
- **Broken commitments** — did an agent promise something and then go back on it?
- **Policy violations** — is an agent breaking the rules?

### How It Will Work

```
Every Message ──► Trust Engine ──► Score + Report
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
   Manipulation   Commitment   Policy
   Detection      Tracking     Checks
```

- Each message gets a **trust score** (0-100)
- Agents with low trust scores get flagged
- The dashboard shows trust metrics in real-time

---

## Phase 3 — Cryptographic Ledger 🔜 Coming

### What It Will Do
The Cryptographic Ledger creates a **tamper-proof record** of every negotiation. It's like a notary stamp on every message.

### How It Will Work

```
Message ──► Hash it ──► Sign with Ed25519 ──► Store in chain
                                                    │
              ┌─────────────────────────────────────┘
              ▼
    Chain: [Msg1] ──► [Msg2] ──► [Msg3] ──► [Msg4]
           Hash: abc   Hash: def   Hash: ghi   Hash: jkl
           Sig: xxx   Sig: yyy    Sig: zzz     Sig: www
```

**Key properties:**
- Each message is **digitally signed** by the sender
- Messages are **chained** (each one includes the hash of the previous)
- If anyone **tampers** with any message, the chain breaks
- Anyone can **verify** the entire history

---

## Phase 4 — WebSocket Live Stream 🔜 Coming

### What It Will Do
Instead of clicking "refresh" to see updates, the dashboard will show negotiations **happening live** — like watching a tennis match.

### How It Will Work

```
Browser ◄──── WebSocket ────► Backend
                │
       Agent 1 says: "OFFER $200"
       Agent 2 says: "COUNTER $190"
       Agent 1 says: "ACCEPT ✅"
                │
         Dashboard updates
         in real-time!
```

---

## Phase 5 — Advanced Analysis 🔜 Coming

### What It Will Do
Deep analysis of negotiation data:
- **Success rates** — which strategies work best
- **Price trends** — how prices evolve over time
- **Agent performance** — which AI providers negotiate better
- **Export reports** — PDF/CSV downloads
- **Comparison views** — side-by-side session comparisons

---

## How All Phases Connect

Think of each phase as a **layer** that builds on the previous one:

```
Phase 0: Foundation
    │
    ▼
Phase 1: Agent Logic ───── Agents that can negotiate
    │                           │
    ▼                           ▼
Phase 2: Trust Engine ───── Watch agents for bad behavior
    │                           │
    ▼                           ▼
Phase 3: Crypto Ledger ──── Seal every message with signatures
    │                           │
    ▼                           ▼
Phase 4: WebSocket ──────── Watch it all happen live
    │                           │
    ▼                           ▼
Phase 5: Analysis ───────── Understand the results
```

**The data flows through all layers:**

```
                  ┌──────────────┐
                  │  Phase 1     │  Two agents negotiate
                  │  (Agents)    │  → produces messages
                  └──────┬───────┘
                         │ messages
                         ▼
                  ┌──────────────┐
                  │  Phase 2     │  Trust Engine scores
                  │  (Trust)     │  each message
                  └──────┬───────┘
                         │ messages + scores
                         ▼
                  ┌──────────────┐
                  │  Phase 3     │  Crypto Ledger signs
                  │  (Ledger)    │  & chains messages
                  └──────┬───────┘
                         │ signed messages
                         ▼
                  ┌──────────────┐
                  │  Phase 4     │  Stream to dashboard
                  │  (WebSocket) │  in real time
                  └──────┬───────┘
                         │ live data
                         ▼
                  ┌──────────────┐
                  │  Phase 5     │  Analyze & report
                  │  (Analysis)  │  on everything
                  └──────────────┘
```

### Data Example (Same Message Through All Phases)

```
Phase 1 (raw):
  {"price": 200, "qty": 100, "type": "OFFER"}

Phase 2 (trust-scored):
  {"price": 200, "qty": 100, "type": "OFFER",
   "trust_score": 92, "flags": []}

Phase 3 (signed & chained):
  {"price": 200, "qty": 100, "type": "OFFER",
   "trust_score": 92,
   "hash": "sha256:abc123...",
   "signature": "ed25519:xyz789...",
   "prev_hash": "sha256:def456..."}

Phase 4 (streamed live):
  → WebSocket pushes signed message to dashboard

Phase 5 (analyzed):
  → Dashboard shows: "Buyer's offers average $205
    with 94% trust score across 6 sessions"
```

---

## File Map

```
TrustMesh/
│
├── README.md                       # Project overview and quick start
├── docs/
│   └── PHASES.md                   # ← THIS FILE — phase explanations
│
├── backend/
│   ├── .env.example                # Template for API keys
│   ├── requirements.txt            # Python dependencies
│   │
│   └── app/
│       ├── main.py                 # FastAPI app creation (Phase 0)
│       ├── config.py               # Settings & environment vars (Phase 0)
│       ├── models.py               # Data schemas (Phase 0)
│       ├── router.py               # Route registration (Phase 0 → 1)
│       ├── llm_client.py           # Gemini/Groq API client (Phase 1)
│       ├── session_manager.py      # Negotiation coordinator (Phase 1)
│       │
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── health.py           # Health check endpoint (Phase 0)
│       │   └── sessions.py         # Session management API (Phase 1)
│       │
│       └── agents/
│           ├── __init__.py         # Agent exports
│           ├── base.py             # Base agent class (Phase 1)
│           ├── buyer.py            # Buyer negotiation agent (Phase 1)
│           └── seller.py           # Seller negotiation agent (Phase 1)
│
└── frontend/
    ├── index.html                  # HTML entry point
    ├── package.json                # Node.js dependencies
    ├── vite.config.js              # Build configuration
    ├── tailwind.config.js          # CSS utility framework
    └── src/
        ├── main.jsx                # React entry point
        ├── App.jsx                 # Main dashboard UI
        ├── App.css                 # (legacy — not used)
        └── index.css               # Global styles & utilities
```

---

> **Pro Tip:** Each phase is designed so you can run the project at any stage. Phase 0 & 1 work fully without API keys. Phase 2+ will build on top without breaking what's already working.
