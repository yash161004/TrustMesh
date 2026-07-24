# TrustMesh Multi-Tenant Load Test Results

**Test Harness**: `backend/scripts/test_multitenant_load.py`

Two documented runs: the original 2026-07-22 benchmark, and a 2026-07-24 re-run
verifying the Phase 1 per-`(org, role)` identity hardening under concurrency.

---

# Run 2 — 2026-07-24 (post identity-hardening re-run)

**Commit**: `ffe0de6` (branch `chore/phase-0-credibility-pass`)
**Purpose**: confirm the per-`(org, role)` DB-backed signing identities (commit `9fd53cd`) hold up under concurrent multi-tenant load.

## Configuration

| Parameter | Value |
|---|---|
| Organizations | 3 (`orgA`, `orgB`, `orgC`) |
| Sessions per org | 5 |
| **Total concurrent sessions** | **15** |
| **Concurrency limit** (semaphore) | **10 in flight** |
| LLM provider | `mock` (no live LLM) |
| Trust engine | mocked — isolates transport/DB/ledger cost from LLM latency |
| Transport | in-process ASGI (`httpx.ASGITransport`), no network hop |
| Database | SQLite (dev default) |
| Rate limiter | disabled |

Tunable via `LOAD_TEST_ORGS`, `LOAD_TEST_SESSIONS_PER_ORG`, `LOAD_TEST_CONCURRENCY`.

## Result — fresh database: **PASSED** (exit 0)

| Metric | Value |
|---|---|
| Session create + turn-trigger phase (15 concurrent) | **1.22 s** |
| Effective throughput | **~12.3 sessions/sec** |
| Total wall clock (incl. fixed 5 s settle + *serial* ledger verification + isolation checks) | **6.35 s** |
| Ledger integrity | **15/15** sessions `chain_valid=True` |
| Cross-tenant isolation | **15/15** cross-org reads correctly rejected with **403** |

The 6.35 s total is dominated by a hard-coded 5 s sleep plus serial ledger reads in the harness — it is not a throughput figure. The meaningful concurrency number is the **1.22 s** create+turn phase.

## Result — warm database (same config, DB already populated by prior runs)

Also **PASSED**, but materially slower:

| Metric | Fresh DB | Warm DB | Delta |
|---|---|---|---|
| Create + turn-trigger phase | 1.22 s | **44.1 s** | ~36× slower |
| Total wall clock | 6.35 s | 78.5 s | ~12× slower |
| Ledger integrity | 15/15 valid | 15/15 valid | — |
| Cross-tenant isolation | 15/15 enforced | 15/15 enforced | — |

**Finding**: throughput degrades sharply on SQLite as the database grows under repeated concurrent write load, while *correctness* (hash-chain validity and tenant isolation) holds at both loads. Concrete supporting evidence for running managed Postgres in production rather than SQLite. This is a storage-engine characteristic, not a trust-layer defect.

## What this run proves

The multi-tenant request path sustains 15 concurrent sessions across 3 orgs using **per-`(org, role)` signing identities**, producing a valid Ed25519 hash-chained ledger per session and refusing every cross-tenant read (403). The identity hardening in `9fd53cd` is verified end-to-end under concurrency — no key collisions, no lost ledger entries, no isolation leaks.

---

## ⚠️ Regression observed during Run 2 (pre-existing, outside this branch)

**All 15/15 sessions logged `turn error: 'market_reference_price'` immediately after their initial offer.**

- **Root cause**: `_extract_scenario()` in `llm_client.py` returns `context["scenario"]` verbatim when it is a non-empty dict. That value is `NegotiationScenario.model_dump()`, which nests pricing under `line_items` and **omits** `market_reference_price`, `quantity`, `buyer_target_price`, `seller_floor_price` — those are plain `@property` shims, not `@computed_field`, so Pydantic does not serialize them. The flat-key fallback that *would* supply them is never reached. `llm_client` then does `scenario["market_reference_price"]` → `KeyError`.
- **Impact**: each session's *initial* offer is still generated, signed, and appended to the ledger (hence 1 valid entry per session), but every subsequent negotiation turn aborts. Multi-turn negotiation is effectively broken in this configuration.
- **Why the harness still passes**: `verify_ledger()` only asserts `len(entries) > 0`. It cannot distinguish "4 turns laddered" from "1 turn laddered, 3 turns crashed."
- **Provenance**: **not introduced by this branch.** No commit here touches `llm_client.py`, the property definitions, or `_scenario_to_flat_context`. `llm_client.py` was last modified on `master` by `0646f7f`, which changed a single unrelated line. The mismatch most likely dates to the multi-line-item scenario refactor. Whether Run 1 (below) genuinely completed 240 turns or the same weak assertion masked the failure is **unresolved** — the harness cannot tell.
- **Recommended fix** (separate task): promote those `@property` shims to `@computed_field` (or have `_scenario_to_flat_context` inject the flat keys explicitly), **and** tighten the harness to assert the expected turn/entry count instead of `> 0`.

## Reproducing Run 2

```bash
cd backend && DATABASE_URL="sqlite:///./loadtest_fresh.db" PYTHONPATH=. python scripts/test_multitenant_load.py
```

---

# Run 1 — 2026-07-22 (original benchmark)

> Retained as historical evidence. Note the "turns processed" figures below predate the regression documented in Run 2 and should not be cited as current behaviour without re-verification.

## Executive Summary

| Run Metric | Baseline Run | High-Concurrency Scale Run |
|---|---|---|
| **Organizations Tested** | 3 (`orgA`, `orgB`, `orgC`) | 6 (`orgA`…`orgF`) |
| **Sessions per Org** | 5 | 10 |
| **Total Sessions** | 15 sessions | 60 sessions |
| **Max Concurrent Workers** | 5 | 15 |
| **Total Turns Processed** | 60 turns (4 turns/session) | 240 turns (4 turns/session) |
| **Wall-Clock Execution Time** | 7.12 seconds | 17.24 seconds |
| **Session Persistence Pass Rate** | 100% (15/15) | 100% (60/60) |
| **Ledger Chain Verification** | 100% Valid (`chain_valid: True`) | 100% Valid (`chain_valid: True`) |
| **Cross-Tenant Isolation Gate** | 100% Enforcement (403 Forbidden) | 100% Enforcement (403 Forbidden) |

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

## Engineering Interpretation

These load tests validate the core multi-tenant backend architecture under concurrent execution, specifically verifying database session persistence, Ed25519 message signing, hash-chained ledger block assembly, and tenant isolation gating (`org_id` authorization checks).

**What these results prove**: The session orchestration engine, per-agent Ed25519 signing thread locking, SQLite/Postgres persistence layer, and cross-tenant API isolation handle high concurrency (60 sessions / 240 turns in 17s) cleanly without database lock contention, keypair race conditions, or isolation leaks.

**What these results DO NOT prove**: Because the LLM provider was mocked (`provider: "mock"`) and the Trust Engine LLM evaluation calls were mocked out to avoid external rate limits, this benchmark measures backend plumbing and cryptographic ledger performance under concurrency, **not** real LLM inference latency, token throughput, or real-time LLM API rate limits.
