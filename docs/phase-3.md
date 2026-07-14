# Phase 3 — Cryptographic Ledger 🔜 Coming

> **A tamper-proof record** of every negotiation. Like a notary stamp on every message — once written, it cannot be changed without detection.

**📅 Status:** Planned | **🔗 Back to overview:** [PHASES.md](./PHASES.md)

---

## What It Will Do

The Cryptographic Ledger creates an **audit trail** that guarantees:

- **Authenticity** — every message is signed by its sender (Ed25519)
- **Integrity** — any tampering is immediately detectable
- **Chain of custody** — messages are linked together (SHA-256)
- **Verifiability** — anyone can check the entire history

---

## How It Will Work

### Message Signing

```
Message ──► Hash it ──► Sign with Ed25519 ──► Store in chain
                                                    │
              ┌─────────────────────────────────────┘
              ▼
    Chain: [Msg1] ──► [Msg2] ──► [Msg3] ──► [Msg4]
           Hash: abc   Hash: def   Hash: ghi   Hash: jkl
           Sig: xxx   Sig: yyy    Sig: zzz     Sig: www
```

### Key Properties

| Property | How It Works |
|----------|-------------|
| **Digital Signatures** | Each message is signed with the sender's Ed25519 private key |
| **Hash Chaining** | Each message includes the hash of the previous message |
| **Tamper Evidence** | Changing any single message breaks the entire chain |
| **Public Verification** | Anyone with the public key can verify signatures |

---

## What a Signed Message Looks Like

```json
{
  "message_type": "OFFER",
  "sender": "buyer-agent-001",
  "price": 200.00,
  "quantity": 100,
  "delivery_terms": "Net-30, FOB destination",
  "timestamp": "2026-07-14T07:00:00Z",
  "turn_number": 1,

  "trust_score": 92,

  "hash": "sha256:abc123def456...",
  "signature": "ed25519:xyz789...",
  "prev_hash": "sha256:def456ghi789..."
}
```

---

## Planned Architecture

```
backend/app/ledger/
├── __init__.py          # Ledger exports
├── signer.py            # Ed25519 signing logic
├── verifier.py          # Signature & chain verification
├── chain.py             # Hash chain management
├── storage.py           # SQLite persistence for ledger
└── models.py            # Signed message schemas
```

---

## Integration with Other Phases

- **Phase 1 (Agents):** Receives messages and returns signed, chained records
- **Phase 2 (Trust):** Locks trust scores into the permanent record
- **Phase 4 (WebSocket):** Streams signed messages to the dashboard
- **Phase 5 (Analysis):** Provides verified data for reports
