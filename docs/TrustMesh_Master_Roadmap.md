# TrustMesh — Master Roadmap
*Consolidated July 23, 2026. Supersedes the July 20 Advanced Roadmap and July 22 Enterprise Roadmap as the single source of truth — those two are kept for historical audit detail, this is the execution plan.*

**Context:** MSc IT (AI/ML) Sem 3 mini project + long-term business/portfolio play, both weighted equally, no hard submission deadline yet. Goal: make this genuinely excellent, not just "acceptable" — and specifically able to survive a skeptical technical panel without hand-waving.

---

## 0. The One-Line Pitch (say this first, every time)

> When autonomous AI agents negotiate deals on a company's behalf, how do you *prove* — cryptographically, not just claim — that no agent was manipulated or made an unauthorized commitment? TrustMesh is that audit layer.

Not "HTTPS for AI negotiations," not "billion-dollar problem" — that framing invites skepticism in an academic setting. Understated + evidence-backed wins a viva. Save the bigger framing for an actual investor conversation, if one ever happens.

**What TrustMesh is not claiming (say this too — it defuses the "how is this different" question before it's asked):**
- Not inventing agent negotiation strategy (ANAC, Deal-or-No-Deal, etc. already own that)
- Not a cross-organizational blockchain identity protocol (that's what ERC-8004/A2A are for)
- It's the narrower, more immediately deployable thing: a single enterprise's internal, tamper-evident audit layer for its own fleet of negotiating agents.

---

## 1. Credit — what's real right now

Confirmed by direct repo audit (not just docs):
- Real multi-tenant backend: Clerk auth, org/user models, 3 Alembic migrations, rate limiting
- Real cryptographic ledger: Ed25519 signing + SHA-256 hash chain (not decorative)
- Three-detector trust engine: policy rules, commitment consistency, LLM-based manipulation detection
- Multi-line-item, multi-SKU `NegotiationScenario` (already generalized past single-product)
- PDF session export, wired end-to-end
- Staging Postgres path with real migrations
- CI via pytest + a manipulation-eval workflow
- Honesty fix already shipped: no more false "verified multi-model consensus" claims
- Calibration already re-verified at 1.00/1.00/1.00 across 3 runs (holdout, documented as such — not oversold as generalization)

This is a genuinely strong starting point. The plan below closes the *specific* gaps, not a rewrite.

---

## 2. Phase 0 — Credibility Pass (do first, ~1 session, zero new features)

- [ ] Confirm no residual "verified multi-model consensus" language anywhere (`PROJECT_REPORT.md`, `DEFENSE_PREP.md`, `manipulation-detector-findings.md`, `commitments.py` comments)
- [ ] Consolidate `backend/scripts/` from 47 files down to 3–4 named, documented scripts: `db_inspect.py`, `qa_screenshots.py`, `seed_demo_data.py` + a `scripts/README.md` explaining what's left
- [ ] Delete/gitignore committed log output (`pytest_full_out.txt`, `qa_node_error.txt`, `astro_log.txt`, `qa_lighthouse*.json`) or move to `docs/qa-history/`
- [ ] One-time `git log -p` grep audit of `backend/scripts/` for any accidentally committed API keys/secrets

**Why first:** costs nothing, but it's the difference between a reviewer who opens the repo and sees discipline vs. one who sees "cleanup never happened." Directly addresses "general skepticism."

---

## 3. Phase 1 — Finish what's already half-built (~2–3 sessions)

> **Status (audited & reconciled 2026-07-23): Phase 1 is essentially complete.** A code-vs-roadmap audit found this section was systematically stale — five of the six items below were already implemented (three of them discovered done only during this audit). The one genuinely-open item is the multi-tenant load-test measurement (#6). Each item is annotated with its true state.

- [x] **Harden AgentCard identity to be genuinely per-tenant. — Shipped to `master` via file-path org-scoping (merge `a52e267`).** The multi-tenant signing collision is closed by scoping each card to an `{org_id}__{agent_id}.json` path (`card_file_path(agent_id, org_id)`) and making `verify_agent_card` reject any card whose *content* `org_id` does not match the caller's org. `session_manager._persist_message` signs each message under the org-scoped card (lazily provisioning one if absent, with a content-checked legacy fallback), and `routes/agent_cards.py` returns `403` on cross-org card reads with a role-gated admin bypass. Cards use per-agent keys (`load_or_generate_keypair_for_agent`), not the old shared per-role key. See `docs/agent_card_design.md` §"Current state & identity hardening". **Prior state:** every `NegotiationMessage` was already signed at creation with a per-agent AgentCard key bound to `org_id`/`owner_user_id`; the gap was that the API defaults `buyer_agent_id`/`seller_agent_id` to shared constants (`buyer-agent-001`/`seller-agent-001`), so agents in different orgs collided on one key file — whichever org signed first owned it, and every other org's messages then failed the tenancy check and silently did not sign (no ledger entry). The path prefix removes that collision.
  - **Design note — the DB-backed alternative was not merged.** An alternative fix was prototyped on `chore/phase-0-credibility-pass` (commit `9fd53cd`): provision one `AgentIdentityRecord` per `(org_id, role)`, add `org_id`/`owner_user_id`/`public_key` columns via an Alembic migration, and make that DB row — not the card file's own `org_id` — the authority `verify_agent_card` checks against. That branch is **parked**, not on `master`. The two approaches are incompatible (they solve the same collision differently); the file-path approach shipped because it needed no migration and keeps the card file self-verifying. Revisit the DB-backed design only if a cross-session reputation story (Phase 4) needs a queryable identity table as its authority. Still the prerequisite for that reputation work either way.
- [x] **Swap production to Postgres. — Already done in config; robustness fix added 2026-07-23.** `render.yaml` already provisions a managed Postgres 15 database (`trustmesh-db`) and wires `DATABASE_URL` from its `connectionString` — production is not SQLite. The audit did find one latent bug: `db.py` only normalized the `postgresql://` scheme to the async driver, not the bare `postgres://` scheme that Render/Heroku actually emit — which would have failed engine creation on managed Postgres. Fixed via `_normalize_async_db_url()` (handles `postgres://`, `postgresql://`, sqlite; unit-tested).
- [x] **Currency handling → config-driven registry.** Done. The class-based `currency_registry.py` (env-var `TRUSTMESH_CURRENCIES`, per-currency metadata, `convert()` raising `NotImplementedError`) already existed; this cycle made it authoritative: `NegotiationScenario.currency` now validates+normalizes against `registry.is_valid()` (was: any 1–10 char string accepted), and the `policy.py` "secret currency swap" check was de-brittled from a raw substring match to word-boundary code matching plus non-ambiguous symbol detection. Verified no benchmark detection outcome changes (no scenario carries a foreign currency in delivery terms).
- [x] **Self-consistency calibration. — Already done (verified in audit).** Self-consistency (same model, 3 calls, temp 0.15, majority vote) is the shipped default (`ManipulationDetector.evaluate(..., majority_vote=False)`), and the few-shot `CALIBRATION_EXAMPLES` list is at 10 entries (target was 10–12), including the 'Gradual Squeeze' Urgency anchor from the regression fix. See `docs/EVAL_RESULTS.md` (`post-few-shot-expansion-swap`, 1.00/1.00/1.00).
- [x] **Confidence intervals in the UI. — Already done (verified in audit).** `engine.py` computes `overall_confidence`, `low_confidence_review_count`, per-violation `confidence_band` (high/moderate/low) and `disagreement_rate`, and emits `LOW_CONFIDENCE_CLEAR` events for weak "all clear" verdicts. `SessionView.tsx` renders all of it ("X% average detector confidence", per-violation confidence bands, "samples disagreed X% of the time"). The binary flagged/clear badge is already replaced.
- [x] **Run `test_multitenant_load.py` for real, at a stated concurrency, write the number down in `docs/`. — Done (re-run 2026-07-24).** A prior benchmark already existed from 2026-07-22; re-ran it post-identity-hardening to verify the per-`(org, role)` signing change under concurrency. **Result: 15 concurrent sessions across 3 orgs at concurrency 10 — create+turn phase 1.22 s (~12.3 sessions/sec), 15/15 ledgers `chain_valid=True`, 15/15 cross-tenant reads correctly 403.** Also measured SQLite degradation on a warm DB (create phase 44.1 s, ~36× slower) — supporting evidence for managed Postgres in production. Full numbers and caveats in `docs/LOAD_TEST_RESULTS.md`. **The run also surfaced a pre-existing regression** (every session's turn processing fails with `KeyError: 'market_reference_price'` because `NegotiationScenario`'s pricing `@property` shims are absent from `model_dump()`); the harness masks it by only asserting `len(entries) > 0`. Tracked as follow-up work, not introduced by this branch.

---

## 4. Phase 2 — TrustMesh-Bench: the evidence layer

This is the single strongest move available to you — it turns "does it actually work" from an argument into a number that regenerates itself.

- [ ] Convert `run_benchmark.py`, `run_manipulation_holdout.py`, `run_adversarial_benchmark.py` from internal dev tools into a named, public-facing artifact: **TrustMesh-Bench**
- [ ] `docs/EVAL_RESULTS.md` regenerated on every run, committed with timestamp + git SHA
- [ ] Extend `.github/workflows/pytest.yml` (or add a sibling workflow) to run the holdout suite on every PR and fail the build if precision/recall drops below a set threshold
- [ ] Optional but strong: a simple public results page on the marketing site — "Precision: X%, Recall: Y%, evaluated on N adversarial scenarios, updated automatically"

**Framing for your defense:** your own findings doc already shows precision/recall varying 1.00/1.00 → 0.75/1.00 → 1.00/0.33 across identical runs on the same holdout. That's not a weakness to hide — per the literature review, this is a documented, studied phenomenon in LLM-as-judge systems generally (overconfidence, calibration instability). Point to that literature, show your confidence-interval fix as a direct response to it. "I found a real limitation in my own system and fixed it with a literature-grounded approach" is a stronger engineering-judgment signal than a system with no visible flaws.

---

## 5. Phase 2.5 — `trustmesh-sdk` (thin wrapper, high narrative value)

- [ ] Expose the existing audit/sign logic as a clean public interface:
```python
from trustmesh import TrustMeshWatcher
watcher = TrustMeshWatcher(api_key="tm_live_...")
audited_turn = watcher.audit_and_sign(agent_message, session_id=session.id)
```
- [ ] Document it as installable middleware for any agent framework (CrewAI, AutoGen, LangChain, OpenAI Swarm) — reframes TrustMesh from "a demo app" to "infrastructure," which is the strongest available answer to an originality challenge.
- [ ] Keep the marketing claims modest — "designed to integrate with" not "used by."

---

## 6. Phase 3 — One classical ML component

- [ ] Deal-outcome prediction: logistic regression or gradient-boosted classifier (scikit-learn) on your backfilled/seeded session history. Features: current price gap, turn number, violation count so far, trust score trend → predicts P(deal closes) and expected final price.
- [ ] This is the one item on the whole roadmap that's unambiguously "Data Scientist" work — real feature engineering, a real model, a real evaluation metric, on your own real data. Directly plugs the gap that right now the system is "prompt engineering + rules + one LLM judge," zero classical ML. Important specifically for an AI/ML MSc defense.

---

## 7. Phase 4 — The actual differentiator (post-checkpoint, business wedge)

- [ ] **Fleet-level anomaly view**: aggregate trust scores and violation types across *all* sessions for an org; start simple (z-score outlier flagging on violation rate), not Isolation Forests/autoencoders yet.
- [ ] **Cross-session reputation** feeding back into `evaluate_session`, built on the AgentCard identity from Phase 1 — an agent's history genuinely follows it across sessions.
- [ ] One-off negotiation verification is a feature. Fleet-level monitoring across hundreds of agents is a product companies pay a retainer for — this is the real recurring-revenue story, and it's also what separates a student demo from something that reads as "someone thought about this as a product."

**Business testing ground:** StellarMind AI's existing FMCG/dairy/logistics/manufacturing exposure — real multi-party procurement, low tolerance for opaque AI decisions. A warmer first conversation than a cold enterprise pitch, if/when you want to test the business angle.

---

## 8. Tier 3 — Speculative, no fixed date

Smart contract settlement (testnet only, mock escrow), zero-knowledge reputation passports, multi-agent swarms / adversarial red-teaming agent, RLAIF fine-tuning loop. All genuinely high-ceiling, all sequenced *after* Phases 1–4 because none of them are solvable-in-scope before you have real usage/data, and a half-built Tier-3 feature is a worse defense outcome than a fully-solid Phase 1–4.

---

## 9. Defense/Viva Prep — anticipated questions

| Question | Answer |
|---|---|
| "How is this different from ERC-8004/A2A?" | Those solve open, cross-organizational agent marketplaces with no pre-existing trust. TrustMesh solves the narrower, earlier problem: a single enterprise auditing its *own* fleet, deployable off-chain today. |
| "Isn't 'agents that negotiate' already solved (ANAC, Deal-or-No-Deal)?" | Yes, deliberately — TrustMesh doesn't claim negotiation-strategy novelty. The negotiation agents are the substrate; the contribution is the independent trust/verification layer on top, which that literature doesn't address. |
| "How do you know your manipulation detector actually works?" | Point to TrustMesh-Bench numbers, not a claim — documented adversarial holdout, precision/recall reported across multiple runs including variance, confidence-interval reporting as a direct response to known LLM-judge calibration literature. |
| "What's actually novel here, in one sentence?" | A cryptographically-verifiable, evaluated trust layer for enterprise agentic procurement — sitting in the gap between abstract LLM-safety research and open-marketplace blockchain trust protocols, neither of which serves a single enterprise's immediate audit need. |
| "Did you build this or did Claude Code?" | Be ready to explain *why*, not just *what*, for every major design choice (Ed25519 vs JWT, hash-chain vs real blockchain, self-consistency vs multi-provider voting). Understanding trumps authorship in a viva. |

---

## 10. Sequencing Summary

| Phase | Content | Effort |
|---|---|---|
| 0 | Credibility pass | 1 session |
| 1 | AgentCard wiring, Postgres, currency registry, calibration | 2–3 sessions |
| 2 | TrustMesh-Bench (public eval pipeline) | 2–3 sessions |
| 2.5 | trustmesh-sdk | 1 session |
| 3 | Deal-outcome prediction model | 2–3 sessions |
| 4 | Fleet anomaly view + cross-session reputation | 3–4 sessions |
| — | Tier 3 (speculative) | No fixed date |

Run each phase item as its own scoped Claude Code session — not one giant session. Explain scope tightly, review the diff, ask Claude Code to explain *why* it made each choice before accepting, and regenerate `docs/EVAL_RESULTS.md` after any change that could affect detection behavior.

---

## 11. What changed from the prior two roadmaps

- Superseded "career + business" framing with the sharper one-line pitch above (§0)
- Renamed and elevated the internal eval suite to a first-class named artifact: **TrustMesh-Bench** (was: an implied CI extension)
- Added `trustmesh-sdk` as a new item (Phase 2.5) — not in either prior roadmap
- Explicitly cut the "HTTPS for AI negotiations" / "billion-dollar" framing language — real leverage, wrong register for an academic defense
- Added §9 (defense prep) as new — neither prior roadmap addressed the viva directly
- Everything else (Phase 0/1/3/4/Tier 3 content) is inherited unchanged from the July 20/22 audits — those were already correct, this just re-sequences and re-frames them around "no hard deadline, general skepticism" as the actual constraint
