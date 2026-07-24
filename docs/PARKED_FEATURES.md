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
- The persistent cross-session reputation ledger itself already exists and is wired — `AgentReputationRecord` in `db.py`, keyed by `agent_id` (the same ID AgentCard signs with). `session_manager.py::evaluate_trust_for_session` reads it via `get_agent_reputation()` before scoring, feeds it into `evaluate_session` as the prior, and writes it back via `update_agent_reputation_v2()` after. This is a real, live read-score-write loop, not a stub.
- The actual gap: **this data is invisible to any user.** `get_agent_reputation` is only called internally — there's no API route exposing an agent's reputation/history, and nothing in the frontend (`AgentDirectory.tsx`, `api.ts`) surfaces it. The mechanism that makes the "reputation-portable agent identity" business pitch (Advanced Roadmap §4 item 3) real already exists; what's missing is making it visible — a `GET /api/v1/agents/{agent_id}/reputation` endpoint and a reputation history view in the agent directory page.
- ~~Secondary, lower-priority improvement once visibility exists: the update rule itself is a flat penalty/recovery (`-0.1` per session with any violation, `+0.02` clean-session recovery, uncapped by severity) — works, but doesn't weight by violation severity or decay old violations over time.~~ **Done.** `update_agent_reputation_v2` in `db.py` now (a) applies a **severity-weighted penalty** (LOW 0.02 / MEDIUM 0.05 / HIGH 0.12 / CRITICAL 0.25, summed per session and capped at 0.30, mirroring the `_PENALTY_MAP` ratios in `trust/engine.py`) instead of a flat `-0.1`, and (b) applies **time decay** — on every update the stored score first drifts toward the 0.75 neutral baseline with a 30-day half-life, so an old violation's drag fades if the agent behaves (and an undeserved boost fades if it goes idle). `session_manager.py` passes each agent's non-disputed violation severities into the call. The flat `-0.1` path is retained as a backward-compatible fallback when no severities are supplied. Covered by 8 new tests in `tests/test_reputation.py` (severity scaling, cap, unknown-severity handling, symmetric decay, backward compat, and a DB-backed age-out test).
