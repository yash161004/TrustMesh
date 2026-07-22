# TrustMesh Backend Scripts Directory

This directory contains database management tools, evaluation runners, identity & crypto verification scripts, and test suites.

## Consolidated CLI Tools
- `db_inspect.py` — Database inspection CLI tool (subcommands: `session-status`, `trust-json`, `count-reports`, `status`, `users`).
- `db_admin.py` — Database administration CLI tool (subcommands: `clear-users`, `make-admin`, `resync-sequences`, `init-schema`).
- `user_provisioning.py` — User provisioning CLI tool (subcommands: `insert-system`, `insert-user`).
- `qa_screenshots.py` — Automated dashboard screenshot generator using Playwright.

## Core Operations & Seed Tools
- `seed_demo_data.py` — Seeds demo sessions, scenarios, and agents into the database. Run during initial setup or demo reset.
- `seed_ledger_entries.py` — Seeds cryptographic ledger entries and hash-chain blocks for demo sessions.
- `backfill_trust.py` — Evaluates and populates trust reports for completed sessions missing trust evaluations.
- `migrate_sqlite_to_postgres.py` — Migrates data from local SQLite (`trustmesh.db`) to target PostgreSQL instance.
- `verify_migration.py` — Validates row counts and schema integrity after SQLite-to-Postgres migration.
- `tamper_ledger_demo.py` — Simulates or restores a hash-chain tamper attempt for demonstration purposes.
- `burn_in_test_v2.py` — Stress burn-in test runner for evaluating API stability over extended multi-session runs.

## Identity & Crypto Verification Tools
- `generate_agent_cards.py` — Generates and signs ERC-8004 AgentCard descriptors for all registered agent identities.
- `check_agent_card_consistency.py` — Validates consistency between AgentCard files on disk and agent database records.
- `run_agent_card_test.py` — End-to-end verification runner for AgentCard creation, signing, and tamper detection.
- `verify_all_ledgers.py` — Verifies the cryptographic hash-chain validity across all session ledgers in the database.
- `verify_real_token.py` — Validates real Clerk JWT authentication tokens against the API backend.

## Evaluation & Benchmark Runners
- `run_benchmark.py` — Benchmark suite runner evaluating trust engine scoring across standard negotiation scenarios.
- `run_holdout.py` — Evaluation runner testing trust engine accuracy on held-out negotiation scenarios.
- `run_manipulation_holdout.py` — Evaluation runner testing manipulation detector against holdout adversarial cases (invoked by CI `manipulation_eval.yml`).
- `run_adversarial_benchmark.py` — Round 1 adversarial scenario benchmark runner.
- `run_adversarial_round2.py` — Round 2 adversarial scenario benchmark runner.
- `compute_calibration_metrics.py` — Computes calibration and accuracy metrics across benchmark execution results.

## Load & Tenancy Verification Tests
- `test_multitenant_load.py` — Multi-tenant load test runner evaluating concurrent org session and ledger performance.
- `test_org_visibility.py` — Tenancy isolation test runner verifying cross-org data visibility boundaries.
