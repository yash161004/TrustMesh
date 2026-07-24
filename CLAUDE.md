# TrustMesh — Project Instructions for Claude Code

## What this project is
A cryptographically-verifiable trust and audit layer for AI-agent-to-AI-agent negotiation.
Agents negotiate (price, terms, multi-line-item deals); TrustMesh scores each turn for
manipulation/policy violations and signs the record into a tamper-evident hash chain.
One-line pitch (use this framing in docs/comments, not hype language):
"Prove — cryptographically, not just claim — that no agent was manipulated or made an
unauthorized commitment during an autonomous negotiation."

Full current plan and priorities: see `docs/TrustMesh_Master_Roadmap.md` (read it before
starting any multi-step task — it has the phase we're currently on).

## Stack
- Backend: FastAPI (Python), SQLAlchemy, Alembic migrations
- Auth/multi-tenancy: Clerk (orgs + users)
- Data: Postgres in staging (`docker-compose.staging.yml`); production target is Postgres
  via `render.yaml` — <verify current prod DB setting before assuming it's fixed>
- Frontend: Astro + React + Tailwind
- Realtime: WebSockets for live session streaming
- Crypto: Ed25519 signing (`crypto/signing.py`), SHA-256 hash chain for the ledger
- CI: GitHub Actions — `.github/workflows/pytest.yml`, `manipulation_eval.yml`

## Repo layout (high-level — confirm against actual tree if it's drifted)
- `backend/app/` — FastAPI app: `routes/`, `models.py`, `policy.py`, `identity/agent_card.py`
- `backend/crypto/` — Ed25519 signing + verification
- `backend/scripts/` — durable, named utilities only, grouped by function and documented
  in `scripts/README.md`: consolidated operational CLIs (`db_inspect.py`, `db_admin.py`,
  `user_provisioning.py`, `qa_screenshots.py`), seed/data-gen (`seed_demo_data.py`,
  `seed_ledger_entries.py`, `run_real_negotiations.py`), the eval suite / TrustMesh-Bench
  (`run_manipulation_holdout.py` (CI-wired), `run_holdout.py`, `run_benchmark.py`,
  `run_adversarial_*.py`, `compute_calibration_metrics.py`), identity/crypto
  (`generate_agent_cards.py`, `tamper_ledger_demo.py`, `sweep_ledger_integrity.py`, …),
  the Postgres migration pair, tenancy tests, and the Phase-3 ML trainer
  (`train_deal_outcome_model.py`). Prefer a subcommand on an existing consolidated CLI over
  a new file. Do NOT add one-off debug/investigation scripts here — put throwaway scripts in
  `/tmp` or a gitignored path. (Root eval console dumps are gitignored; see `.gitignore`.)
- `frontend/` — Astro/React dashboard
- `docs/` — durable documentation, eval results, QA history
- Currency handling: `currency_registry.py` — config-driven via `TRUSTMESH_CURRENCIES` env
  var. Never hardcode a currency list elsewhere; extend the registry instead.

## Commands
- Run backend tests: `<verify: likely pytest from backend/>`
- Run frontend: `<verify: likely npm run dev from frontend/>`
- Run the adversarial/manipulation holdout: `run_manipulation_holdout.py` /
  `run_adversarial_benchmark.py` — regenerate `docs/EVAL_RESULTS.md` after ANY change that
  could affect detector behavior (prompt changes, calibration changes, model swaps)
- Migrations: Alembic — never hand-edit a migration that's already been applied in staging

## Non-negotiables
- Never write or restore "verified multi-model consensus" language anywhere in code
  comments or docs — the actual default is self-consistency sampling (same model, 3 calls,
  temp ~0.15, majority vote). Cross-provider voting is opt-in and documented as unstable
  under free-tier rate limits. This is a stated project value, not a stylistic preference.
- Never commit API keys or secrets, in scripts or anywhere else. If you touch
  `backend/scripts/`, check for accidentally-committed credentials while you're in there.
- Confidence should be reported (confidence intervals / "we are X% confident"), not
  collapsed into a binary flagged/clear badge.
- AgentCard signing, once wired, replaces the shared per-role keypair — don't reintroduce
  a shared-key signing path as a "simpler" fallback.
- Multi-line-item / multi-currency support is the real shape of the data model now — don't
  regress `NegotiationScenario` back to single-product/single-currency assumptions.

## Working style for this project
- Scope tasks tightly — one phase item from the roadmap per session, not "improve the
  codebase." State the scope explicitly and don't wander outside it.
- Before editing a system I (the user) haven't fully reviewed, explain what it currently
  does and why the change is needed — I need to be able to defend every design choice in
  an academic viva, so understanding matters as much as the working code.
- Always run relevant tests after a change and report the result, not just "done."
- After any change to the trust engine, policy rules, or manipulation detector, regenerate
  the eval results doc — a claim about detection quality is only valid with a fresh number
  behind it.

## Do not
- Do not add new debug/one-off scripts to `backend/scripts/` — see repo layout above.
- Do not reintroduce cross-provider "consensus" language or logic without an explicit,
  separate decision to do so.
- Do not silently assume 1:1 currency parity — `currency_registry.convert()` should raise
  `NotImplementedError` until real conversion is implemented, not fake it.
