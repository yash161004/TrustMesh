# Parked Features

## Deal-Outcome Prediction Model — **BLOCKED on data, not on code**

**What exists and is verified working:**
- Full offline pipeline: `scripts/train_deal_outcome_model.py` (trains + CV-compares
  LogisticRegression vs GradientBoosting, writes a git-SHA-stamped `docs/ML_MODEL_RESULTS.md`),
  `app/ml/deal_outcome_features.py` (pure feature extraction), and `app/ml/predict.py`
  (thin inference module).
- The online path is wired: `GET /api/v1/sessions/{id}/prediction` calls `predict.py` and
  degrades gracefully (`model_available: false`, other fields null) when no artifact exists,
  so the UI simply hides the prediction rather than erroring.
- The pipeline was run end-to-end and confirmed to load, extract features, and exit cleanly.

**The actual blocker (a data gap, not a bug):** training requires `MIN_SESSIONS_TO_TRAIN = 30`
labeled sessions (`data_source LIKE 'real_llm_%'`, status COMPLETED, outcome DEAL/NO_DEAL).
Only **15** such sessions exist so far, so the script correctly refuses to train — a model fit
on 15 rows would report a precise-looking metric that is actually noise, which is exactly what
the guard exists to prevent. Note: the legacy `data_source='real'` bucket (~694 rows) is
deliberately **excluded** from the query because it is suspected to contain mock/seed rows
(see `scripts/inspect_real_rows.py`); pointing training at it without vetting would risk
training on non-genuine negotiations.

**To unblock (no code change needed):** accumulate ≥30 real `real_llm_*` COMPLETED sessions
(via real usage or `scripts/run_real_negotiations.py`), then run
`python -m scripts.train_deal_outcome_model` against that DB and commit the resulting
`app/ml/artifacts/deal_outcome_model.joblib` + generated `docs/ML_MODEL_RESULTS.md`. Parked
here intentionally rather than forced, to avoid shipping a meaningless model or spending LLM
quota prematurely.

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

### Identity Scoping Decision (Cross-Tenant Collision Fix)
- **Kept Approach:** File-path scoping (`card_file_path(agent_id, org_id)` with fallback to unscoped path for pre-migration cards). Verified safe because `verify_agent_card` checks `org_id` against payload content, eliminating cross-tenant collisions.
- **Shelved Approach (DB migration `a1b2c3d4e5f6`):** The DB-backed identity migration (`a1b2c3d4e5f6_add_org_binding_to_agent_identities.py`) on `chore/phase-0-credibility-pass` is shelved unused. Reasoning: single-instance Render deployment has no shared-disk failure mode requiring DB identity state right now, so file-path scoping avoids unnecessary surface area before defense while remaining available if multi-backend scaling is needed.
