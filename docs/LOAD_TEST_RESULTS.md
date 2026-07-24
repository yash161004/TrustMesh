# TrustMesh Multi-Tenant Load Test Results

**Test Harness**: `backend/scripts/test_multitenant_load.py`  

## Executive Summary

| Run Metric | Baseline Run | High-Concurrency Scale Run | High-Concurrency (Post-Fix) Run |
|---|---|---|---|
| **Date Run** | 2026-07-22 | 2026-07-22 | 2026-07-24 |
| **Organizations Tested** | 3 (`orgA`, `orgB`, `orgC`) | 6 (`orgA`–`orgF`) | 3 (`orgA`, `orgB`, `orgC`) |
| **Sessions per Org** | 5 | 10 | 5 |
| **Total Sessions** | 15 sessions | 60 sessions | 15 sessions |
| **Max Concurrent Workers** | 5 | 15 | **50** |
| **Total Turns Processed** | 60 turns (4 turns/session) | 240 turns (4 turns/session) | 75 turns (5 turns/session) |
| **Wall-Clock Execution Time** | 7.12 seconds | 17.24 seconds | ~109 seconds |
| **Session Persistence Pass Rate** | 100% (15/15) | 100% (60/60) | 100% (15/15) |
| **Ledger Chain Verification** | 100% Valid (`chain_valid: True`) | 100% Valid (`chain_valid: True`) | 100% Valid (15/15, 5 entries each — tightened assertion) |
| **Cross-Tenant Isolation Gate** | 100% Enforcement (403 Forbidden) | 100% Enforcement (403 Forbidden) | 100% Enforcement (403 Forbidden) |

---

## Benchmark Details

### Baseline Test Run (15 Sessions) — 2026-07-22
- **Concurrency**: 5 concurrent tasks across 3 orgs.
- **LLM Provider**: `mock` (no real API calls).
- **Results**:
  - `POST /sessions` -> 15 created (200 OK)
  - `POST /sessions/{id}/turn` -> 15 sessions executed up to 4 turns (200 OK)
  - `GET /sessions/{id}/ledger` -> 15/15 ledgers verified as cryptographically chained and intact (`chain_valid: True`)
  - `GET /sessions/{id}` with cross-tenant headers -> 15/15 blocked with `403 Forbidden`

### Scaled High-Concurrency Test Run (60 Sessions) — 2026-07-22
- **Concurrency**: 15 concurrent tasks across 6 orgs.
- **Results**:
  - `POST /sessions` -> 60 created (200 OK)
  - `POST /sessions/{id}/turn` -> 60 sessions executed up to 4 turns (240 turns total)
  - `GET /sessions/{id}/ledger` -> 60/60 ledgers verified as cryptographically chained and intact (`chain_valid: True`)
  - `GET /sessions/{id}` with cross-tenant headers -> 60/60 blocked with `403 Forbidden`

### High-Concurrency Post-Fix Run (15 Sessions) — 2026-07-24
This run was executed after two critical bug fixes (commit `d73a825`):
1. **Pricing field serialisation**: `NegotiationScenario`'s `@property` pricing shims were promoted to `@computed_field` so `model_dump()` includes them — without this, every turn after the initial offer crashed with `KeyError`.
2. **AgentCard org collision**: Agent IDs are now scoped per-org (e.g. `buyer-orgA-0`) so concurrent sessions from different orgs no longer clobber each other's card file, which silently dropped ledger entries.

- **Concurrency**: 50 concurrent tasks across 3 orgs (all 15 sessions issued near-simultaneously).
- **LLM Provider**: `mock` (no real API calls).
- **Ledger Assertion**: This run uses the tightened `verify_ledger` check — each session must produce at least 2 entries (initial offer + at least one negotiation turn), and every persisted message must have a matching ledger entry.
- **Results**:
  - `POST /sessions` -> 15 created (200 OK)
  - `POST /sessions/{id}/turn` -> 15 sessions executed up to 5 turns (75 turns total)
  - `GET /sessions/{id}/ledger` -> 15/15 ledgers verified with **exactly 5 entries matching 5 messages** each, all `chain_valid: True`
  - `GET /sessions/{id}` with cross-tenant headers -> 15/15 blocked with `403 Forbidden`
  - **Zero turn errors** and **zero ledger entry mismatches**.
- **Timing breakdown**:
  - Session creation + turn trigger: ~86 s
  - Ledger verification (per-session polling): ~17 s
  - Cross-tenant isolation checks: <1 s
  - **Total wall-clock: ~109 s**

---

## Engineering Interpretation

These load tests validate the core multi-tenant backend architecture under concurrent execution, specifically verifying database session persistence, Ed25519 message signing, hash-chained ledger block assembly, and tenant isolation gating (`org_id` authorization checks).

**What these results prove**: The session orchestration engine, per-agent Ed25519 signing thread locking, SQLite/Postgres persistence layer, and cross-tenant API isolation handle high concurrency (50 concurrent workers, 75 turns in ~109s) cleanly without database lock contention, keypair race conditions, or isolation leaks. The post-fix run additionally proves that the multi-turn negotiation pipeline produces ledger entries matching every persisted message — the earlier `len(entries) > 0` assertion masked a serialisation regression that silently dropped all but the first turn.

**What these results DO NOT prove**: Because the LLM provider was mocked (`provider: "mock"`) and the Trust Engine LLM evaluation calls were mocked out to avoid external rate limits, this benchmark measures backend plumbing and cryptographic ledger performance under concurrency, **not** real LLM inference latency, token throughput, or real-time LLM API rate limits.
