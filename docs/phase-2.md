# Phase 2 — Trust Engine 🔜 Coming

> **The integrity checker.** Watches every message exchanged between agents and looks for manipulation, broken promises, and rule violations.

**📅 Status:** Planned (Next up) | **🔗 Back to overview:** [PHASES.md](./PHASES.md)

---

## What It Will Do

The Trust Engine is like a **lie detector** for AI agents. It examines every offer, counter-offer, and acceptance for signs of bad behavior.

### Detection Capabilities

| Check | What It Looks For |
|-------|-------------------|
| **Manipulation Detection** | Is an agent lying or being deceptive? |
| **Commitment Tracking** | Did an agent promise something and then go back on it? |
| **Policy Violations** | Is an agent breaking the negotiation rules? |
| **Pattern Analysis** | Does the agent's behavior match known manipulation patterns? |

---

## How It Will Work

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

### Scoring System

| Score Range | Meaning |
|-------------|---------|
| 90–100 | Trustworthy — normal negotiation behavior |
| 70–89 | Minor concerns — slight inconsistencies |
| 50–69 | Suspicious — potential manipulation detected |
| 0–49 | Critical — likely bad faith negotiation |

---

## Planned Architecture

```
backend/app/trust/
├── __init__.py          # Trust engine exports
├── engine.py            # Main trust evaluation logic
├── detectors/
│   ├── manipulation.py  # Deception detection heuristics
│   ├── commitments.py   # Broken promise tracking
│   └── policy.py        # Policy violation checks
└── models.py            # Trust scores & violation schemas
```

---

## Integration with Other Phases

- **Phase 1 (Agents):** Receives messages from agents, returns trust scores
- **Phase 3 (Ledger):** Trust scores get locked into the cryptographic record
- **Phase 5 (Analysis):** Trust trends across sessions are reported
