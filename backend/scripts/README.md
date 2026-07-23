# TrustMesh Backend Scripts

Operational, evaluation, identity/crypto, and data-generation utilities for the backend.

> **Scope rule:** this directory is for durable, named utilities only. Do **not** add one-off
> debug or investigation scripts here — put throwaway scripts in `/tmp` or a gitignored path.
> Ten session-specific debug scripts (ad-hoc `query_*`, `inspect_*`, spent one-shot backfills,
> and localhost stress probes) were removed in the Phase 0 credibility pass; don't reintroduce
> that pattern.

## Consolidated CLI tools
These absorbed the old `insert_*` / `query_*` / one-off admin script families — use the
subcommands, don't recreate single-purpose scripts.

- `db_inspect.py` — DB inspection CLI: `session-status`, `trust-json`, `count-reports`, `status`, `users`.
- `db_admin.py` — DB administration CLI: `clear-users`, `make-admin`, `resync-sequences`, `init-schema`.
- `user_provisioning.py` — User provisioning CLI: `insert-system`, `insert-user`.
- `qa_screenshots.py` — Playwright dashboard screenshot generator for QA verification.

## Seed & data-generation
- `seed_demo_data.py` — Seeds realistic demo sessions/scenarios/agents so the dashboard shows data instantly (no live API calls; `skip_llm=True`).
- `seed_ledger_entries.py` — Builds Ed25519-signed, hash-chained ledger entries for seeded sessions. Run **after** `seed_demo_data.py`.
- `run_real_negotiations.py` — Throttled real-LLM negotiation batch runner (live Trust Engine, rate-limit backoff). Generates real session data for the deal-outcome model.
- `backfill_trust.py` — Backfills `TrustReportRecord`s for completed sessions that are missing a trust evaluation.

## Evaluation & benchmark runners (TrustMesh-Bench)
- `run_manipulation_holdout.py` — ManipulationDetector adversarial holdout. **Invoked by CI (`.github/workflows/manipulation_eval.yml`).**
- `run_holdout.py` — CommitmentConsistencyChecker holdout (with LLM response caching). Commitment-detector counterpart to the manipulation holdout.
- `run_benchmark.py` — Integrated trust-engine benchmark across the standard scenario suite (policy + commitment detectors).
- `run_adversarial_benchmark.py` — Adversarial scenario benchmark, round 1.
- `run_adversarial_round2.py` — Adversarial scenario benchmark, round 2.
- `compute_calibration_metrics.py` — Brier score / ECE calibration metrics for the manipulation judge (forces `majority_vote=False` to measure the single judge in isolation).

## Identity & crypto (AgentCard + ledger)
- `generate_agent_cards.py` — Generates signed ERC-8004-style AgentCards for every agent identity.
- `check_agent_card_consistency.py` — Verifies every identity has a valid on-disk card and no cards are orphaned.
- `run_agent_card_test.py` — End-to-end AgentCard sign/verify/tamper test (cited in `docs/PROJECT_REPORT.md`).
- `tamper_ledger_demo.py` — Tampers a ledger entry, then confirms `verify_chain()` detects it. Demo asset. `--restore` reverts.
- `sweep_ledger_integrity.py` — Full-DB ledger integrity sweep for out-of-band tampering. Designed to run on a schedule (cron).
- `benchmark_write_time_integrity.py` — Measures `verify_chain()` write-time overhead at various chain lengths.

## Migration (SQLite → Postgres)
- `migrate_sqlite_to_postgres.py` — Migrates local SQLite data into the target Postgres instance.
- `verify_migration.py` — Validates row counts and schema integrity after the migration above.

## Multi-tenancy & load tests
- `test_multitenant_load.py` — Concurrent multi-tenant load test against the FastAPI app.
- `test_org_visibility.py` — Verifies cross-org data-visibility isolation boundaries.

## ML
- `train_deal_outcome_model.py` — Trains the deal-outcome prediction model (logistic regression / gradient boosting) on seeded/backfilled session history. Read-only against the DB.
