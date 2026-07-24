# TrustMesh — Viva & Technical Defense Presentation Guide

*Prepared for MSc Semester 3 Major Project Viva & Technical Defense Panel.*

---

## 1. The Executive Pitch (First 30 Seconds)

> **"When autonomous AI agents negotiate commercial deals on an enterprise's behalf, how do you cryptographically prove — not just claim — that no agent was manipulated or made an unauthorized commitment? TrustMesh is that tamper-evident audit layer."**

### Scope Boundaries (What TrustMesh DOES and DOES NOT claim)
- **NOT inventing negotiation strategy:** We do not claim novel game-theoretic negotiation algorithms (ANAC, Deal-or-No-Deal literature already owns that).
- **NOT a public blockchain identity protocol:** We do not require ERC-8004 or cross-org public chain consensus.
- **IS an enterprise audit layer:** A deployable, off-chain, tamper-evident verification system for a single enterprise's fleet of negotiating agents.

---

## 2. System Architecture & Core Technology Stack

```
                                 ┌─────────────────────────────────┐
                                 │     Client / Marketing Site     │
                                 │  (Astro, Tailwind, Vercel/SSR)  │
                                 └────────────────┬────────────────┘
                                                  │
                                                  ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                             TrustMesh FastAPI Backend                             │
│                                                                                   │
│  ┌───────────────────────┐   ┌────────────────────────┐   ┌────────────────────┐  │
│  │ Clerk Multi-Tenant    │   │  AgentCard Identity    │   │ Three-Detector     │  │
│  │ Auth & Org Scoping    │   │  Ed25519 Signing       │   │ Trust Engine       │  │
│  └───────────┬───────────┘   └───────────┬────────────┘   └─────────┬──────────┘  │
│              │                           │                          │             │
│              ▼                           ▼                          ▼             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                      SHA-256 Hash-Chained Audit Ledger                       │  │
│  │        h_n = SHA-256( h_{n-1} || Sign_Ed25519(Turn_n) || Turn_n )           │  │
│  └───────────────────────────────────────┬─────────────────────────────────────┘  │
└──────────────────────────────────────────┼────────────────────────────────────────┘
                                           │
                                           ▼
                            ┌──────────────────────────────┐
                            │    Managed Postgres 15 DB    │
                            │ (SQLite async dev fallback)  │
                            └──────────────────────────────┘
```

---

## 3. Cryptographic Verification & Audit Proof

### How Hash-Chained Ledgering Works
1. Every message turn $T_n$ is signed by the agent's unique Ed25519 private key:
   $$\sigma_n = \text{Sign}_{K_{\text{priv}}}(T_n)$$
2. The ledger entry hash $H_n$ binds the previous block hash $H_{n-1}$, the signature $\sigma_n$, and the normalized message payload:
   $$H_n = \text{SHA-256}(H_{n-1} \parallel \sigma_n \parallel \text{CanonicalJSON}(T_n))$$
3. **Tamper Detection Guarantee:** If any historical turn $T_k$ ($k \le n$) is modified, deleted, or reordered in the database via direct SQL mutation or out-of-band edit:
   - The signature verification $\text{Verify}_{K_{\text{pub}}}(T_k, \sigma_k)$ fails.
   - The hash chain breaks at sequence $k$ ($H_k \neq \text{SHA-256}(\dots)$).
   - `verify_chain` identifies the exact sequence number where corruption occurred (`broken_at = k`).

---

## 4. Multi-Tenant Isolation & Identity Hardening

- **Org-Scoped AgentCard Paths:** Agent identities are path-scoped per organization (`{org_id}__{agent_id}.json`) to prevent multi-tenant key collisions.
- **Strict Authorization:** `verify_agent_card` and all `/api/v1/sessions/*` endpoints reject cross-tenant requests with `403 Forbidden`.
- **Concurrency Tested:** Verified under high concurrency (15–50 concurrent workers across multiple orgs) with **0 key collisions**, **0 cross-tenant leaks**, and **100% ledger validity**.

---

## 5. Three-Detector Trust Engine

| Detector | Mechanism | What It Catches |
|---|---|---|
| **1. Policy Rules** | Deterministic floor/ceiling/quantity checks & word-boundary currency symbol detection | Unauthorized price drops, quantity mismatches, unapproved delivery terms |
| **2. Commitment Consistency** | Turn-over-turn delta analysis on line items & price trends | Sudden concession jumps, inconsistent term shifting |
| **3. LLM Manipulation Detector** | Structured LLM-as-judge with few-shot calibration anchors | Urgency pressure, false anchors, emotional manipulation, split-the-difference traps |

---

## 6. Antagonistic Defense Q&A (Anticipated Viva Questions)

### Q1: "Isn't LLM manipulation detection inherently non-deterministic and unreliable?"
> **Answer:** Yes, LLM-as-judge detectors exhibit calibration variance. We explicitly document this in `LITERATURE_REVIEW.md` (§3) and `docs/EVAL_RESULTS.md`. Rather than hiding it, we address it with three specific engineering controls:
> 1. **Few-shot calibration anchoring** in the system prompt.
> 2. **Self-consistency majority voting** (3 calls at temperature 0.15).
> 3. **Confidence-interval bands** emitted alongside every trust score (`overall_confidence`, per-violation confidence bands, disagreement rates) so human reviewers see detector uncertainty.

### Q2: "Why use custom Ed25519 + SHA-256 hash chains instead of a public blockchain?"
> **Answer:** Enterprise B2B procurement data requires strict confidentiality and low latency. Public blockchains expose transaction contents, incur gas fees, and add latency unacceptable for multi-turn negotiation. An append-only Ed25519 hash chain provides the exact cryptographic tamper-evidence required for enterprise auditability, without public data exposure or blockchain overhead.

### Q3: "Did you train a machine learning model or just use prompt engineering?"
> **Answer:** We built a complete classical ML deal-outcome feature extraction pipeline (`deal_outcome_features.py`, scikit-learn classifier, 5-fold `StratifiedKFold` CV). However, per our strict academic honesty rules, we **deliberately deferred deploying the model artifact** because 42 of the 57 training rows originate from synthetic seed scripts. We chose to report the feature pipeline as built while honestly withholding the model until real LLM negotiation session data accumulates.

### Q4: "How does this scale across different agent frameworks (CrewAI, AutoGen, LangChain)?"
> **Answer:** We packaged the core audit engine as a standalone, zero-dependency Python SDK (`trustmesh-sdk`). It provides native adapters (`TrustMeshCallbackHandler`, `TrustMeshCrewCallback`, `TrustMeshAutoGenHandler`, `generic.py`) that hook into agent step loops without modifying framework code.

---

## 7. Live Demonstration Cheat-Sheet

1. **Show Public Evaluation Page:** Navigate to `/eval` — point to the live continuous benchmark metrics and the `CI Gate: Pass (≥0.95)` badge.
2. **Show Fleet Anomaly View:** Navigate to `/dashboard/fleet` — demonstrate z-score statistical outlier detection across organization agents.
3. **Show Cryptographic Verification:** Run `python sdk/examples/minimal_agent_loop.py` in the terminal to demonstrate real Ed25519 signing and instant detection of a forged turn.
