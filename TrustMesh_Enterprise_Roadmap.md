# TrustMesh — Enterprise, End-to-End Roadmap
*Written after a direct audit of `github.com/yash161004/TrustMesh` (master, as of July 22, 2026) — not from the docs alone.*

---

## 0. Credit where it's due — what's already been fixed since the last roadmap

I'm not going to pretend nothing changed. Comparing the actual code to the July 20 roadmap, real work landed:

- **The honesty fix shipped.** `DEFENSE_PREP.md` now states plainly that self-consistency sampling (3 calls, same model, temp 0.15, majority vote) is the default, and that cross-provider voting is opt-in and documented as unstable under free-tier limits. No more "verified multi-model consensus" language.
- **Calibration work shipped.** The three-run variance (1.00/1.00 → 0.75/1.00 → 1.00/0.33) is now root-caused, fixed, and re-verified at 1.00/1.00/1.00 across 3 consecutive runs — with an honest footnote that this is holdout performance, not a generalization claim.
- **`NegotiationScenario` is already multi-line-item.** `models.py` has `proposed_items: list[ProposedItem]` and `policy.py` evaluates per-SKU floor/cap/quantity. The single-SKU limitation from the last roadmap is gone.
- **PDF session export shipped.** `pdf_generator.py` exists and is wired into `routes/sessions.py`.
- **A real staging Postgres path exists** (`docker-compose.staging.yml`, `migrate_sqlite_to_postgres.py`, 3 Alembic migrations).

That's four out of roughly six "before Aug 9" items from the last roadmap actually done, ahead of schedule. Say that in your next presentation — it's a better story than silence.

---

## 1. What the audit found that still needs fixing

### 1.1 The one that matters most: production still deploys SQLite, not Postgres

`render.yaml` — the file that defines your actual production deploy — sets:
```
DATABASE_URL: sqlite+aiosqlite:///./trustmesh.db
```
Staging runs Postgres 15. Your migrations are written for Postgres. Your own `migrate_sqlite_to_postgres.py` script exists because someone already decided SQLite wasn't the end state. But the file that controls what's actually live still ships SQLite — which means the deployed instance has no real concurrent-write safety, and its data lives on ephemeral container disk. This is the single most "college project, not enterprise" signal in the entire repo, and it's a config change, not new code.

**Fixed file provided:** `render.yaml` (attached) — swaps in Render's managed Postgres via a `databases:` block, wired to `DATABASE_URL` automatically. Drop it in and this is closed.

### 1.2 AgentCard identity is still exactly as parked as last time

`PARKED_FEATURES.md` still says it plainly: fully built (17 tests, Ed25519 signing, `verify_agent_card`), completely unwired from the request path. `routes/agent_cards.py` only *lists* cards from disk — nothing in `TrustEngine` or the message-signing path calls it. This was §2.4 in the last roadmap and it's unchanged. Auth + orgs are live now (Clerk, per your own docs) — the blocker that justified parking it is gone. This is the highest-ROI unfinished item in the whole codebase: the code already exists, it just needs to be called.

### 1.3 Currency handling is still a flat hardcoded list, not config-driven

`currency_registry.py` is one line: `VALID_CURRENCIES = ["USD", "EUR", "GBP", "INR", "JPY"]`. It's used in `policy.py` via a crude substring check against free-text `delivery_terms` to catch a "secret currency swap" — functional, but brittle (a delivery note that happens to contain the literal substring "JPY" for unrelated reasons would false-positive), and adding a currency means editing source and redeploying.

**Fixed file provided:** `currency_registry.py` (attached) — class-based registry, config-driven via `TRUSTMESH_CURRENCIES` env var, carries per-currency metadata (symbol, decimal precision) needed once line items go properly multi-currency, and has an explicit `convert()` integration point that raises `NotImplementedError` rather than silently pretending 1:1 parity — so nobody accidentally ships a silent money bug. `VALID_CURRENCIES` is still exported for backward compatibility, so nothing else needs to change to adopt it.

### 1.4 `backend/scripts/` still has 47 files

Still the same debris category flagged before: `run_auth_test.py`, `run_auth_test_2.py`, `run_auth_test_3.py`, `insert_test_user.py`, `insert_test_users.py`, `insert_dummy_user.py`, etc. A technical reviewer who opens this folder reads it as "cleanup never happened," independent of how good the core system is. This is still zero new code, pure signal improvement — consolidate to `scripts/db_inspect.py`, `scripts/qa_screenshots.py`, `scripts/seed_demo_data.py` (keep), delete the rest, one `scripts/README.md` explaining what's left.

### 1.5 No classical ML component yet

Tier 1 item #1 from the last roadmap — deal-outcome prediction via a simple scikit-learn model on your own seeded/backfilled session history — hasn't been started. This is still the cheapest way to make the project legible to a Data-Scientist-focused interviewer, since right now the entire system is "prompt engineering + rules + one LLM judge," with zero classical ML.

---

## 2. What "enterprise, end-to-end deployed" actually requires

This is the new part of the ask — last time the frame was "career + business," this time it's specifically *production-grade deployment*. That's a different, mostly orthogonal checklist to "more features," and it's the thing a panel, an investor's technical due-diligence, or a hiring manager doing a system-design interview will all probe differently than a feature list. Six dimensions, audited against what's actually in the repo:

| Dimension | Current state | What "enterprise" requires |
|---|---|---|
| **Data layer** | SQLite in prod (§1.1), Postgres in staging only | Postgres in prod, connection pooling (pgbouncer or SQLAlchemy pool tuning), automated backups, a documented recovery drill |
| **Secrets management** | `.env.example` + Render `sync: false` env vars | Fine for a solo project; enterprise-grade means a secrets manager (Render's own secret files, or Doppler/Vault) and zero long-lived API keys checked into any script (worth a one-time `git log -p` grep audit of `backend/scripts/`) |
| **Observability** | `logging_config.py` exists; no evidence of structured/centralized logging, tracing, or alerting | Structured JSON logs shipped somewhere queryable (even a free-tier Grafana Cloud/Axiom), a `/metrics` endpoint beyond what `routes/metrics.py` currently does, and at least one alert (e.g. ledger `chain_valid: false` should page someone, not just sit in a dashboard) |
| **Multi-tenancy hardening** | Clerk auth + orgs live, `test_org_visibility.py` and `test_multitenant_load.py` exist | Good foundation — the gap is *load-testing evidence*: has `test_multitenant_load.py` actually been run at a meaningful concurrency and the results written down anywhere? If not, that's a half-day task that turns an existing test into a real capacity number you can quote |
| **CI/CD** | `.github/workflows/pytest.yml` and `manipulation_eval.yml` exist | Good — extend with a deploy-on-merge-to-master workflow to Render, and a required-status-check gate so master can't merge red |
| **Security posture** | Ed25519 signing, rate limiting (`limiter.py`), Clerk auth | Missing: key rotation story (per DEFENSE_PREP.md's own admission — a compromised key currently affects *all* sessions for that role, since it's a shared keypair, not per-agent). This is exactly what AgentCard (§1.2) solves once wired in — per-agent keys are the fix, not a separate initiative |

**The honest framing for your next presentation:** you're not starting "enterprise deployment" from zero — CI, staging Postgres, multi-tenant auth, and rate limiting are all real and already there. The gap is narrower than it sounds: fix the prod database (§1.1, done via the attached file), wire the identity layer that already exists (§1.2), and add the observability/alerting layer that's currently missing entirely. That's a defensible, scoped story — "here's what's production-grade today, here's the specific three-item gap to fully enterprise-grade, here's why each item is next" — which is a much stronger answer than either "it's basic" or "it's already enterprise."

---

## 3. Build order

### Phase A — Close the gaps found in this audit (cheap, do first)
1. Apply the attached `render.yaml` and `currency_registry.py`.
2. Wire AgentCard into the message-signing path (§1.2) — bind each agent's card public key to its Clerk org/user, sign every `NegotiationMessage` at creation using the card's key instead of the current shared per-role keypair. This directly fixes the key-rotation weakness DEFENSE_PREP.md already flags.
3. Consolidate `backend/scripts/` to 3–4 named, documented scripts (§1.4).
4. Run `test_multitenant_load.py` for real, at a stated concurrency, and write the number down in `docs/`.

### Phase B — The enterprise-deployment layer (new this cycle)
5. Structured logging to a queryable sink (Axiom/Grafana Cloud free tier is enough to demonstrate the pattern).
6. One real alert wired to ledger tamper detection (`chain_valid: false` → webhook to Slack/Discord/email is a half-day task and a very concrete "this is what production monitoring means" demo).
7. Deploy-on-merge CI workflow with a required green-check gate.

### Phase C — Everything from the last roadmap's Tier 1/2, unchanged priority
8. Deal-outcome prediction model (scikit-learn on your own session history) — still the cheapest, highest-value classical-ML addition.
9. Cross-session reputation that actually feeds `evaluate_session` — now easier, since it composes directly with the AgentCard wiring in Phase A.
10. Fleet-level anomaly view across an org's sessions.

Everything from Tier 3 in the last roadmap (smart contracts, ZK reputation, RLAIF) is unchanged — still correctly sequenced after A/B/C, not before.

---

## 4. One thing I won't do

I don't have push access to your actual GitHub (I cloned it read-only to audit it) — so "remove/add" in this pass means: the two files above are ready to drop in directly, and everything else is specified precisely enough for you or Antigravity to implement without re-deriving the reasoning. I'd rather hand you a correct, honest gap list than fabricate commits I can't actually make.
