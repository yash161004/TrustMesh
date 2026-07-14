# Phase 4 — WebSocket Live Stream 🔜 Coming

> **Watch negotiations happen live** — like watching a tennis match between two AI agents, with every serve and return appearing instantly on your dashboard.

**📅 Status:** Planned | **🔗 Back to overview:** [PHASES.md](./PHASES.md)

---

## What It Will Do

Instead of clicking "refresh" or making API calls to see updates, the dashboard will show negotiations **streaming in real-time**.

---

## How It Will Work

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

### Live Features

| Feature | Description |
|---------|-------------|
| **Live Messages** | Each negotiation message appears as it's sent |
| **Price Chart** | See the price curve update in real-time |
| **Trust Scores** | Live trust score updates (from Phase 2) |
| **Status Alerts** | Instant notifications on deal acceptance/rejection |
| **Multiple Sessions** | Watch several negotiations simultaneously |

---

## Planned Architecture

```
backend/app/stream/
├── __init__.py          # Stream exports
├── ws_manager.py        # WebSocket connection manager
└── handlers.py          # Message routing & broadcasting

frontend/src/
├── hooks/
│   └── useWebSocket.js  # React hook for WebSocket connection
└── components/
    ├── LiveFeed.jsx      # Real-time message stream
    └── LiveChart.jsx     # Live-updating price chart
```

---

## Integration with Other Phases

- **Phase 1 (Agents):** Streams negotiation turns live
- **Phase 2 (Trust):** Shows trust score updates in real-time
- **Phase 3 (Ledger):** Streams signed & verified messages
- **Phase 5 (Analysis):** Provides live data stream for on-the-fly analysis
