# Parked Features

## AgentCard / ERC-8004 Identity — **WIRED IN, no longer parked** (as of commit 6828ca7)

**What exists:**
- `app/identity/agent_card.py` and `app/crypto/signing.py`
- An Ed25519-based, ERC-8004-style AgentCard implementation. It mints JSON identity cards, signs them, and persists them locally.

**Status: live.** `session_manager.py::_persist_message` (called from both `start_session` and
`process_turn` — the real-time negotiation path, not an offline script) now:
1. Resolves `msg.sender` to its role (buyer/seller) for the active session.
2. Calls `get_or_create_agent_card(agent_id=msg.sender, role=..., org_id=..., owner_user_id=...)`
   to lazily provision a per-agent card bound to the Clerk org/user that owns it.
3. Enforces `verify_agent_card(..., expected_org_id=org_id)` — an invalid signature or an
   org-tenancy mismatch blocks the message from being signed.
4. Signs every message with `sign_message_for_agent(msg_dict, msg.sender)` — a genuine
   per-agent Ed25519 key, not the old shared per-role keypair. This closes the key-rotation
   weakness previously flagged in `DEFENSE_PREP.md` (a compromised key now only affects one
   agent's sessions, not every session for that role).

Test coverage: `test_crypto.py` (17 tests, pre-existing) plus this integration is now exercised
implicitly by any session that actually runs (not just offline utility scripts like
`generate_agent_cards.py`).

**Not yet done (real remaining gap, not a parking decision):**
- Cross-session reputation doesn't yet key off AgentCard identity — `buyer_trust_score`/
  `seller_trust_score` inputs to `evaluate_session` are still session-scoped, not a persistent
  ledger keyed by `agent_id` across sessions/orgs. That's the next real step (Advanced Roadmap
  §Tier 2 #6), not "finish wiring AgentCard" — wiring is done.
