# TrustMesh — Technical Defense Executive One-Pager

**Project:** TrustMesh — Tamper-Evident Cryptographic Audit Layer for Autonomous AI Negotiations  
**Scope:** Single-enterprise B2B agent fleet governance & verifiable auditability  

---

## 1. Problem Statement & Scope

Commercial autonomous AI agents negotiate contracts, prices, and terms without human intervention. Without a verifiable audit layer, enterprises cannot prove what an agent committed to, whether a transcript was altered after the fact, or whether an agent fell victim to adversarial LLM manipulation tactics.

**TrustMesh solves this** by executing an off-chain, cryptographically signed, hash-chained ledger alongside real-time manipulation detection.

---

## 2. System Architecture Blueprint

```
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                              TrustMesh Enterprise System                               │
 │                                                                                        │
 │  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌────────────────────────┐ │
 │  │ Clerk Multi-Tenant Auth │  │ AgentCard Identity      │  │ Three-Detector Engine  │ │
 │  │ Org-Scoped Isolation    │  │ Ed25519 Key Signing     │  │ Real-Time Verification │ │
 │  └────────────┬────────────┘  └────────────┬────────────┘  └───────────┬────────────┘ │
 │               │                            │                           │              │
 │               └────────────────────────────┼───────────────────────────┘              │
 │                                            ▼                                          │
 │                     ┌───────────────────────────────────────────┐                     │
 │                     │     SHA-256 Hash-Chained Audit Ledger     │                     │
 │                     │  H_n = SHA-256(H_{n-1} || Sign || Turn)   │                     │
 │                     └──────────────────────┬────────────────────┘                     │
 └────────────────────────────────────────────┼──────────────────────────────────────────┘
                                              ▼
                              Managed Postgres 15 / SQLite DB
```

---

## 3. Cryptographic Ledger Proof

1. **Ed25519 Message Signature:**  
   $$\sigma_n = \text{Sign}_{K_{\text{priv}}}(\text{Turn}_n)$$
2. **SHA-256 Block Chain Binding:**  
   $$H_n = \text{SHA-256}(H_{n-1} \parallel \sigma_n \parallel \text{CanonicalJSON}(\text{Turn}_n))$$
3. **Tamper Guarantee:** Any out-of-band edit or reordering of $\text{Turn}_k$ ($k \le n$) causes immediate signature verification failure and breaks the hash chain at sequence $k$ (`broken_at = k`).

---

## 4. Key Performance & Verification Metrics

| Benchmark | Value | Context |
|---|:---:|---|
| **Backend Pytest Suite** | **53 / 53 Passed** | Covers Ed25519 signing, DB persistence, fleet anomaly z-scores |
| **SDK Pytest Suite** | **31 Passed (2 Skipped)** | Standalone `trustmesh-sdk` with LangChain, Generic, CrewAI, AutoGen adapters |
| **Frontend SSR Build** | **Exit Code 0** | Astro SSR + Tailwind + Vercel bundling |
| **Load Test Concurrency** | **50 Workers / 109s** | Zero key collisions, 100% chain validity, 100% 403 cross-tenant isolation |
| **CI Holdout Gate** | **Pass ($\ge 0.95$)** | `/eval` continuous holdout metric gate |

---

## 5. Live 3-Minute Demo Walkthrough

1. **Dashboard Overview (`http://localhost:80`)**: Point out price negotiation curve, seller vs. buyer trust scores, and green `Chain Verified` badge.
2. **Tamper Attack Simulation**: Execute `python scripts/tamper_ledger_demo.py` to mutate a database record. Refresh browser to show red pulsing `Chain Broken` badge highlighting sequence #1.
3. **Recovery Verification**: Run `python scripts/tamper_ledger_demo.py --restore` and refresh browser to show instant chain recovery (`Chain Verified`).
