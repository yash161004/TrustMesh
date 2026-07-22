# TrustMesh Multi-Tenant Load Test Results

**Date Run**: 2026-07-22  
**Test Harness**: `backend/scripts/test_multitenant_load.py`  

## Executive Summary

| Run Metric | Baseline Run | High-Concurrency Scale Run |
|---|---|---|
| **Organizations Tested** | 3 (`orgA`, `orgB`, `orgC`) | 6 (`orgA`, `orgB`, `orgC`, `orgD`, `orgE`, `orgF`) |
| **Sessions per Org** | 5 | 10 |
| **Total Sessions** | 15 sessions | 60 sessions |
| **Max Concurrent Workers** | 5 | 15 |
| **Total Turns Processed** | 60 turns (4 turns/session) | 240 turns (4 turns/session) |
| **Wall-Clock Execution Time** | 7.12 seconds | 17.24 seconds |
| **Session Persistence Pass Rate** | 100% (15/15) | 100% (60/60) |
| **Ledger Chain Verification** | 100% Valid (`chain_valid: True`) | 100% Valid (`chain_valid: True`) |
| **Cross-Tenant Isolation Gate** | 100% Enforcement (403 Forbidden) | 100% Enforcement (403 Forbidden) |

---

## Benchmark Details

### Baseline Test Run (15 Sessions)
- **Concurrency**: 5 concurrent tasks across 3 orgs.
- **Results**:
  - `POST /sessions` -> 15 created (200 OK)
  - `POST /sessions/{id}/turn` -> 15 sessions executed up to 4 turns (200 OK)
  - `GET /sessions/{id}/ledger` -> 15/15 ledgers verified as cryptographically chained and intact (`chain_valid: True`)
  - `GET /sessions/{id}` with cross-tenant headers -> 15/15 blocked with `403 Forbidden`

### Scaled High-Concurrency Test Run (60 Sessions)
- **Concurrency**: 15 concurrent tasks across 6 orgs.
- **Results**:
  - `POST /sessions` -> 60 created (200 OK)
  - `POST /sessions/{id}/turn` -> 60 sessions executed up to 4 turns (240 turns total)
  - `GET /sessions/{id}/ledger` -> 60/60 ledgers verified as cryptographically chained and intact (`chain_valid: True`)
  - `GET /sessions/{id}` with cross-tenant headers -> 60/60 blocked with `403 Forbidden`

---

## Engineering Interpretation

These load tests validate the core multi-tenant backend architecture under concurrent execution, specifically verifying database session persistence, Ed25519 message signing, hash-chained ledger block assembly, and tenant isolation gating (`org_id` authorization checks).

**What these results prove**: The session orchestration engine, per-agent Ed25519 signing thread locking, SQLite/Postgres persistence layer, and cross-tenant API isolation handle high concurrency (60 sessions / 240 turns in 17s) cleanly without database lock contention, keypair race conditions, or isolation leaks.

**What these results DO NOT prove**: Because the LLM provider was mocked (`provider: "mock"`) and the Trust Engine LLM evaluation calls were mocked out to avoid external rate limits, this benchmark measures backend plumbing and cryptographic ledger performance under concurrency, **not** real LLM inference latency, token throughput, or real-time LLM API rate limits.
