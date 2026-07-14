# Phase 1 — Agent Logic 🟢 Active

> **AI agents come to life!** Instead of just a health check, the system can now actually **run negotiations** between two AI-powered agents (Buyer & Seller).

**📅 Status:** Current (Active) | **🔗 Back to overview:** [PHASES.md](./PHASES.md)

---

## What Was Built

| Component | What It Does |
|-----------|-------------|
| **BuyerAgent** | AI agent that tries to buy at the lowest price |
| **SellerAgent** | AI agent that tries to sell at the highest price |
| **BaseAgent** | Shared logic for both agents (message history, LLM calls) |
| **LLM Client** | Connects to Gemini or Groq AI APIs |
| **Session Manager** | Coordinates the back-and-forth negotiation |
| **Session API** | REST endpoints to create, start, and run negotiations |
| **Mock Responses** | Works without API keys (returns simulated data) |

---

## How It Works

### API Flow

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

---

## How the Agents Work

Each agent has:

1. **System prompt** — instructions telling the AI how to behave (buyer vs seller mindset)
2. **Memory** — keeps track of the last 10 messages
3. **Strategy** — knows when to raise/lower prices, when to accept, when to walk away
4. **Fallback** — if the AI gives a bad response, it has a backup plan

### BuyerAgent Strategy

| Rule | Value |
|------|-------|
| Starting offer | 15% below asking price |
| Price change | Increases slowly each turn |
| Accept condition | Price ≤ target price |
| Max budget | Configurable (`max_price`) |

### SellerAgent Strategy

| Rule | Value |
|------|-------|
| Starting offer | Asking price |
| Price change | Decreases slowly each turn |
| Accept condition | Price ≥ floor price |
| Min price | Configurable (`floor_price`) |

---

## Working Without API Keys

If you haven't set `GEMINI_API_KEY` or `GROQ_API_KEY`, the system uses **mock mode**:
- Simulates realistic negotiation responses
- Works completely offline
- Perfect for testing and development

---

## Key Files

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

## API Reference

### `POST /api/v1/sessions`
Create a new negotiation session.

### `POST /api/v1/sessions/{id}/start`
Start the session with the buyer's initial offer.

### `POST /api/v1/sessions/{id}/turn`
Process one or more negotiation turns until completion.

### `GET /api/v1/sessions/{id}`
Get session details.

### `GET /api/v1/sessions/{id}/messages`
Get all messages in the session.

### `GET /api/v1/sessions`
List all sessions.
