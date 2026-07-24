# TrustMesh — Frequently Asked Questions & Troubleshooting Guide

---

## 1. General System & Architecture

### Q: What is TrustMesh and how does it differ from a traditional LLM monitoring dashboard?
**A:** Traditional LLM dashboards store logs in a centralized database without cryptographic integrity guarantees — anyone with DB write access can alter transcripts post-hoc. TrustMesh digitally signs every negotiation turn using Ed25519 and binds entries into a SHA-256 hash-chain ($H_n = \text{SHA-256}(H_{n-1} \parallel \sigma_n \parallel \text{Turn}_n)$). Any modification, deletion, or reordering breaks the chain and is identified instantly.

### Q: Does TrustMesh require a public blockchain or token gas fees?
**A:** No. TrustMesh is an off-chain enterprise solution. Public blockchains incur high transaction fees and latency, and expose sensitive B2B negotiation data. TrustMesh provides cryptographically equivalent tamper-evidence for single-enterprise agent fleets without public chain overhead.

---

## 2. SDK & Framework Integration

### Q: How do I integrate TrustMesh into an existing CrewAI or AutoGen agent workflow?
**A:** Install the optional adapter extra:
```bash
pip install "trustmesh-sdk[crewai]"   # for CrewAI
pip install "trustmesh-sdk[autogen]"  # for AutoGen
```
Then bind `TrustMeshCrewCallback` or `TrustMeshAutoGenHandler` to your agent event pipeline:
```python
from trustmesh import TrustMeshWatcher
from trustmesh.adapters.crewai import TrustMeshCrewCallback

watcher = TrustMeshWatcher(agent_id="buyer-agent", session_id="session-01")
handler = TrustMeshCrewCallback(watcher)

agent = Agent(..., step_callback=handler.on_step)
task = Task(..., callback=handler.on_task_finish)

ok, broken_at = handler.verify()
```

### Q: Can `trustmesh-sdk` be used without installing any agent frameworks?
**A:** Yes. The core package (`trustmesh-sdk`) has **zero required dependencies** except `cryptography>=40`. It includes `trustmesh.adapters.generic` which audits any standard OpenAI-style message dictionary (`{"role": "...", "content": "..."}`).

---

## 3. Operations & Troubleshooting

### Q: How do I run database migrations on a fresh PostgreSQL deployment?
**A:** Run Alembic migrations from the `backend/` directory:
```bash
cd backend && alembic upgrade head
```

### Q: Why is the classical ML model artifact (`deal_outcome_model.joblib`) not committed in git?
**A:** Per the project's strict academic honesty constraint, model artifacts trained exclusively or predominantly on synthetic data are deferred from production deployment. The feature pipeline (`deal_outcome_features.py`) is fully functional, but model deployment is gated until $\ge 30$ real LLM negotiation dialogues accumulate.

### Q: What should I do if a tamper alert is triggered?
**A:** When `tamper_alerted_at` is set or the webhook notification fires:
1. Identify the session ID and sequence number reported in the alert payload.
2. Execute `python backend/scripts/sweep_ledger_integrity.py` to inspect the chain status.
3. Compare the database entry against the signed backup or immutable audit storage to identify and revert unauthorized SQL modifications.
