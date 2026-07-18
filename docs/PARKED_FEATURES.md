# Parked Features

## AgentCard / ERC-8004 Identity

**What exists:** 
- `app/identity/agent_card.py` and `app/crypto/signing.py`
- An Ed25519-based, ERC-8004-style AgentCard implementation. It mints JSON identity cards, signs them, and persists them locally.

**Status:**
- Dormant. The code is entirely un-integrated.
- It is not wired into the `TrustEngine` or any part of the API request path.
- The feature is fully functional in isolation, with solid test coverage via `test_crypto.py` (17 tests) and various offline utility scripts (e.g. `generate_agent_cards.py`).

**Why it's parked:**
- This feature was built ahead of any documented plan.
- The cryptographic identity layer is not in scope for the current SaaS migration (Phase 0 through 5).
- It makes the most sense to revisit this feature *after* Phase 3 (Auth + Tenancy) has landed. A signed identity layer will integrate much more naturally once real users and organizations are fully established in the database.
