# TrustMesh Backend Scripts

Operational, evaluation, identity/crypto, and data-generation utilities for the TrustMesh backend.

> **Scope Rule:** This directory contains durable, named operational utilities only. Do **not** add temporary debug or one-off investigation scripts here. Unused one-off scripts (`backfill_trust.py`, `benchmark_write_time_integrity.py`, `check_agent_card_consistency.py`, `migrate_sqlite_to_postgres.py`, `run_adversarial_round2.py`, `run_holdout.py`, `test_org_visibility.py`, `verify_migration.py`) have been consolidated or removed to maintain clean repository hygiene.

---

## 1. Operational & Administration CLIs

- **`db_inspect.py`** — Consolidated DB inspection CLI utility.
  ```bash
  python scripts/db_inspect.py session-status
  python scripts/db_inspect.py trust-json [--limit 5]
  python scripts/db_inspect.py count-reports
  python scripts/db_inspect.py status
  python scripts/db_inspect.py users [--limit 5]
  ```

- **`db_admin.py`** — Consolidated DB administration CLI utility.
  ```bash
  python scripts/db_admin.py clear-users
  python scripts/db_admin.py make-admin [--clerk-user-id <id>]
  python scripts/db_admin.py resync-sequences
  python scripts/db_admin.py init-schema [--url <postgres_url>]
  ```

- **`user_provisioning.py`** — CLI utility for user and system account provisioning.
  ```bash
  python scripts/user_provisioning.py insert-system
  python scripts/user_provisioning.py insert-user --email user@example.com --role admin --org-id org_123
  ```

- **`check_ngrok.py`** — Health check utility to verify ngrok tunnel status and retrieve the active public URL for Clerk webhooks.
  ```bash
  python backend/scripts/check_ngrok.py
  ```

- **`qa_screenshots.py`** — Playwright dashboard screenshot generator for QA verification.
  ```bash
  python scripts/qa_screenshots.py
  ```

---

## 2. Seed & Data-Generation

- **`seed_demo_data.py`** — Seeds realistic demo negotiation sessions, scenarios, trust reports, and violations without requiring live LLM API calls.
  ```bash
  python scripts/seed_demo_data.py
  ```

- **`seed_ledger_entries.py`** — Generates Ed25519-signed, hash-chained ledger entries for seeded sessions. Run after `seed_demo_data.py`.
  ```bash
  python scripts/seed_ledger_entries.py [session_id]
  ```

- **`run_real_negotiations.py`** — Throttled real-LLM multi-turn negotiation batch runner with rate-limit backoff.
  ```bash
  python scripts/run_real_negotiations.py
  ```

---

## 3. Evaluation & Benchmark Runners (TrustMesh-Bench)

- **`run_manipulation_holdout.py`** — ManipulationDetector adversarial holdout suite. **Invoked by CI (`.github/workflows/manipulation_eval.yml`)**.
  ```bash
  python scripts/run_manipulation_holdout.py --limit 8 --no-cache
  ```

- **`run_benchmark.py`** — Primary negotiation benchmark evaluation suite across policy and commitment detectors.
  ```bash
  python scripts/run_benchmark.py
  ```

- **`run_adversarial_benchmark.py`** — Adversarial scenario benchmark runner testing LLM prompt injection resistance.
  ```bash
  python scripts/run_adversarial_benchmark.py
  ```

- **`compute_calibration_metrics.py`** — Computes Brier score and Expected Calibration Error (ECE) for the manipulation detector.
  ```bash
  python scripts/compute_calibration_metrics.py
  ```

---

## 4. Identity, Security & Crypto

- **`generate_agent_cards.py`** — Generates signed AgentCard JSON specifications for agent identities.
  ```bash
  python scripts/generate_agent_cards.py
  ```

- **`run_agent_card_test.py`** — End-to-end AgentCard signature verification test suite (cited in `docs/PROJECT_REPORT.md`).
  ```bash
  python scripts/run_agent_card_test.py
  ```

- **`tamper_ledger_demo.py`** — Demonstrates tamper detection by mutating a ledger entry and verifying chain invalidation.
  ```bash
  python scripts/tamper_ledger_demo.py [session_id]
  python scripts/tamper_ledger_demo.py [session_id] --restore
  ```

- **`sweep_ledger_integrity.py`** — Full-database cryptographic hash chain integrity verification sweep.
  ```bash
  python backend/scripts/sweep_ledger_integrity.py
  ```

---

## 5. Machine Learning & Performance Benchmarking

- **`train_deal_outcome_model.py`** — Trains the deal-outcome prediction model (Scikit-Learn Random Forest) on negotiation history.
  ```bash
  python scripts/train_deal_outcome_model.py
  ```

- **`test_multitenant_load.py`** — Concurrent multi-tenant load testing utility for measuring API throughput and tenant isolation under load.
  ```bash
  python scripts/test_multitenant_load.py
  ```
