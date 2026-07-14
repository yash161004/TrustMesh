# TrustMesh — Phase-by-Phase Guide 🛡️

> **An easy-to-understand walkthrough of what each phase does, how it works, and how everything connects.**

---

## 📚 Phase Files

Each phase has its own detailed guide:

| # | Phase | Status | File |
|---|-------|--------|------|
| 0 | **Foundation** | ✅ Done | [`docs/phase-0.md`](./phase-0.md) |
| 1 | **Agent Logic** | 🟢 Active | [`docs/phase-1.md`](./phase-1.md) |
| 2 | **Trust Engine** | 🔜 Coming | [`docs/phase-2.md`](./phase-2.md) |
| 3 | **Cryptographic Ledger** | 🔜 Coming | [`docs/phase-3.md`](./phase-3.md) |
| 4 | **WebSocket Live Stream** | 🔜 Coming | [`docs/phase-4.md`](./phase-4.md) |
| 5 | **Advanced Analysis** | 🔜 Coming | [`docs/phase-5.md`](./phase-5.md) |

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

### The data flows through all layers:

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
│   ├── PHASES.md                   # ← THIS FILE — overview index
│   ├── phase-0.md                  # Foundation (Completed)
│   ├── phase-1.md                  # Agent Logic (Active)
│   ├── phase-2.md                  # Trust Engine (Planned)
│   ├── phase-3.md                  # Cryptographic Ledger (Planned)
│   ├── phase-4.md                  # WebSocket Live Stream (Planned)
│   └── phase-5.md                  # Advanced Analysis (Planned)
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

> 👉 **Start with [`phase-0.md`](./phase-0.md)** for the foundation, then jump to **[`phase-1.md`](./phase-1.md)** for the active agent logic.
