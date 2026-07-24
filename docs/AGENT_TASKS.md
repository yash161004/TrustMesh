# TrustMesh — Multi-Agent Task Board

> Coordination doc for parallel work by **Antigravity** and **Opencode** while the
> lead (Claude) session is rate-limited. Everyone works on branch
> `claude/project-status-remaining-i5aadr`. Claude reviews all pushes on reset.

## Ground rules (read first)

1. **Stay in your lane.** Each agent owns the directories listed under its section.
   Do **not** edit files outside your lane — that's how merge conflicts happen.
2. **Before every push:** `git fetch origin claude/project-status-remaining-i5aadr`
   then `git pull --rebase origin claude/project-status-remaining-i5aadr`. Because
   lanes are disjoint, rebases should apply with zero conflicts.
3. **One task = one focused commit** (or a small stack), with a descriptive message.
   End commit messages with a blank line then:
   `Co-Authored-By: <your agent name>`
4. **Do not run the ML training script** (`train_deal_outcome_model.py`) — it's
   data-blocked (see `docs/PARKED_FEATURES.md`), not something to force.
5. **Never commit `backend/data/agent_cards/*.json` churn** — the test suite
   rewrites those with fresh keypairs every run. If they show as modified after
   tests, `git checkout --` them (unless you are Antigravity doing Task E, which
   fixes this properly).
6. If a task turns out to need a live LLM API key (`GEMINI_API_KEY` etc.) and you
   don't have one, **stop and note it in your commit/PR** rather than faking data.
   Several existing tests already fail locally for exactly this reason — that's
   expected, not your regression.

---

## Status snapshot

| Task | Owner | Lane | Status |
|------|-------|------|--------|
| A — Prod frontend build fix | Antigravity | `web-astro/` | ✅ Done |
| D — Reputation severity + decay | Claude | `backend/app/` | ✅ Done |
| Ledger-tamper alert on reads | Claude | `backend/app/routes/` | ✅ Done |
| C — ML deal-outcome model | (blocked) | — | ⏸️ Parked: needs ≥30 real sessions (have 15) |
| **B — Consolidate backend/scripts/** | **Antigravity** | `backend/scripts/` | 🔧 In progress |
| **E — Agent-card test-artifact hygiene** | **Antigravity** | `backend/data/`, `backend/tests/conftest.py`, `.gitignore`, `app/identity/`, `app/config.py` | 📋 Assigned |
| **F — Deploy-on-merge CI + green-check gate** | **Opencode** | `.github/workflows/` | 📋 Assigned |
| **G — Structured logging / observability** | **Opencode** | `backend/app/logging_config.py`, `backend/app/main.py`, `backend/app/routes/metrics.py` | 📋 Assigned |
| **H — Load-test evidence** | **Opencode** | `docs/LOAD_TEST_RESULTS.md` (+ read-only run of the existing load test) | 📋 Assigned |

---

# ANTIGRAVITY

**Lane:** `backend/scripts/`, `backend/data/`, `backend/tests/conftest.py`,
`app/identity/agent_card.py`, `app/config.py`, `.gitignore`. Do not touch
`web-astro/`, `.github/`, `backend/app/routes/`, `backend/app/main.py`,
`backend/app/logging_config.py`.

## Task B — Consolidate `backend/scripts/` (finish this first)

**Context:** TrustMesh's `backend/scripts/` has ~36 files, many one-off debris
(`run_auth_test.py`, `run_auth_test_2.py`, `insert_test_user.py`,
`insert_dummy_user.py`, `inspect_real_rows.py`, etc.). A reviewer reads this as
"cleanup never happened."

**Steps:**
1. List every file in `backend/scripts/` and classify KEEP vs DELETE.
2. **KEEP (verify by grepping the repo for each filename first):**
   `seed_demo_data.py`, `run_benchmark.py`, `run_manipulation_holdout.py`,
   `train_deal_outcome_model.py`, `check_ngrok.py`, and anything referenced by
   `.github/workflows/`, `README.md`, or `docs/`. If a filename appears in a live
   workflow or doc, keep it.
3. Consolidate ad-hoc DB-inspection scripts into a single `scripts/db_inspect.py`
   and screenshot scripts into `scripts/qa_screenshots.py`; delete the redundant
   one-offs.
4. Add `backend/scripts/README.md` documenting every surviving script and how to
   run it.
5. **Acceptance:** `pytest` in `backend/` still collects & passes (modulo the
   known `GEMINI_API_KEY` failures); no doc or workflow references a deleted file
   (grep to confirm); `git status` clean after a test run.
6. Commit: `chore(scripts): consolidate backend/scripts to a documented set`.

## Task E — Agent-card test-artifact hygiene

**Problem:** `backend/data/agent_cards/*.json` are tracked files, but the test
suite calls `generate_agent_card(...)` which rewrites them with a fresh Ed25519
keypair + timestamp on **every** `pytest` run. Result: `git status` is dirty after
any test run, producing meaningless signature diffs (this actually tripped the
lead's stop-hook this session).

**Fix (proper, not a bandaid):**
1. Find where cards are written — `app/identity/agent_card.py` (look for the
   `backend/data/agent_cards` path). Make the storage directory configurable, e.g.
   an `AGENT_CARD_DIR` setting in `app/config.py` defaulting to the current path.
2. In `backend/tests/conftest.py`, point the card dir at a per-run temp dir (pytest
   `tmp_path_factory`) so tests never touch the tracked files.
3. `git rm --cached backend/data/agent_cards/*.json` for the **test-fixture** cards
   (e.g. `agent-org-test.json`, `cross-org-agent-001.json`) and add a
   `backend/data/agent_cards/*.json` ignore rule to `.gitignore` — BUT keep any
   card that is a genuine runtime seed (check whether app startup or a seed script
   expects specific files to exist; if so, keep those and only ignore the rest).
4. **Acceptance:** run `pytest backend/tests/` twice; `git status` is clean both
   times (no `backend/data/agent_cards/` churn). All previously-passing tests still
   pass.
5. Commit: `test(identity): isolate agent-card writes to a temp dir, stop tracking test cards`.

---

# OPENCODE

**Lane:** `.github/workflows/`, `backend/app/logging_config.py`,
`backend/app/main.py`, `backend/app/routes/metrics.py`, `docs/LOAD_TEST_RESULTS.md`.
Do not touch `backend/scripts/`, `backend/data/`, `web-astro/`,
`backend/app/routes/sessions.py`, `backend/app/db.py`.

## Task F — Deploy-on-merge CI + required green-check gate

**Context:** The repo already has `.github/workflows/pytest.yml` and
`manipulation_eval.yml`. Production deploys via `render.yaml` (Render, Docker,
managed Postgres). There is currently **no** deploy-on-merge automation and no
enforced status-check gate.

**Steps:**
1. Inspect the existing workflows to match style/Python version/caching.
2. Add `.github/workflows/deploy.yml`:
   - Trigger: `push` to `master`.
   - Job 1: run the backend test suite (reuse the pattern from `pytest.yml`); the
     deploy job must `needs:` this job so a red test blocks deploy.
   - Job 2: trigger a Render deploy by `curl`-ing a deploy hook stored in a repo
     secret `RENDER_DEPLOY_HOOK_URL` (do **not** hardcode any URL/token). If the
     secret is absent, the step should no-op with a clear log line, not fail.
3. Document in the workflow header comment (and a short note in `README.md`'s
   deploy section **only if** README is otherwise untouched by others — otherwise
   skip README to avoid collisions) how to: (a) create the Render deploy hook,
   (b) enable branch protection on `master` requiring the `pytest` check.
4. **Acceptance:** `deploy.yml` is valid YAML, the deploy job `needs:` the test
   job, and no secrets/URLs are hardcoded. (You cannot actually merge to master to
   prove it fires — that's fine; correctness is structural.)
5. Commit: `ci: add deploy-on-merge workflow gated on green tests`.

## Task G — Structured logging / observability

**Context:** `app/logging_config.py` already uses `structlog` (logs render as JSON
in test output). `app/routes/metrics.py` exists but is thin. The roadmap's Phase B
wants: structured JSON logs shippable to a queryable sink, a real `/metrics`
endpoint, and (already done by Claude) a ledger-tamper alert — make sure a tamper
event also emits a **structured** log event, not just a plain string.

**Steps:**
1. Confirm `logging_config.py` emits JSON in production (`APP_ENV=production`) and
   human-readable in dev. Make the log sink/level configurable via env
   (`LOG_LEVEL` already exists; add an optional `LOG_JSON` or reuse `APP_ENV`).
2. Expand `app/routes/metrics.py` to expose meaningful counters, e.g.: total
   sessions, sessions by outcome, total violations by severity, ledger
   `chain_valid` failures seen, tamper alerts fired. Pull from the DB (read-only).
   Keep it a plain JSON endpoint (no Prometheus dep required unless already present).
3. Ensure the tamper-alert path (`app/crypto/ledger_alerts.py`) logs a structured
   event — if it currently uses `logger.error("...")` with a plain string, add
   structured fields (`event=LEDGER_TAMPER_DETECTED`, `session_id`, `org_id`,
   `broken_at`, `reason`). **Read** `ledger_alerts.py` but if you must edit it,
   note it in your commit (it's borderline between lanes — prefer leaving it and
   only touching `metrics.py`/`logging_config.py`/`main.py`).
4. Add a couple of focused tests in a **new** file `backend/tests/test_metrics.py`
   (new file = no collision) asserting the metrics endpoint returns the expected
   shape.
5. **Acceptance:** `/api/v1/metrics` (or wherever it's mounted) returns real
   numbers against a seeded DB; `pytest backend/tests/test_metrics.py` passes.
6. Commit: `feat(observability): structured logging config + expanded /metrics counters`.

## Task H — Load-test evidence

**Context:** `backend/tests/test_multitenant_load.py` exists but there's no written
capacity number anywhere. `docs/LOAD_TEST_RESULTS.md` exists as the home for it.

**Steps:**
1. Read `test_multitenant_load.py` to see how it drives concurrency and whether it
   needs a live LLM key. If it can run in **mock** mode (`provider: "mock"`, no real
   LLM calls), run it at a stated concurrency (e.g. 50 concurrent sessions).
2. If it **requires** a real API key you don't have, do **not** fabricate numbers —
   instead update `docs/LOAD_TEST_RESULTS.md` to state precisely what the test
   measures, how to run it, and that a real run is pending a key, then stop.
3. If it runs: record in `docs/LOAD_TEST_RESULTS.md` — date, concurrency level,
   throughput/latency observed, pass/fail, environment. Keep the same honest-caveat
   tone as `docs/EVAL_RESULTS.md`.
4. **Acceptance:** `docs/LOAD_TEST_RESULTS.md` contains either a real, dated
   capacity number or an explicit "pending live key" note with repro steps — never
   an invented figure.
5. Commit: `docs: record multitenant load-test results` (or `...test procedure pending key`).

---

# Review checklist for Claude (on reset)

- [ ] `git fetch` + read new commits from Antigravity & Opencode on the branch.
- [ ] **B:** scripts folder trimmed; no live doc/workflow references a deleted file; README added.
- [ ] **E:** `pytest` run leaves `git status` clean (no agent-card churn); tests green.
- [ ] **F:** `deploy.yml` valid, deploy `needs:` tests, no hardcoded secrets.
- [ ] **G:** `/metrics` returns real counters; `test_metrics.py` passes; tamper log is structured.
- [ ] **H:** load-test doc has a real number OR an honest pending-key note (no fabricated figures).
- [ ] Run the full `backend/` test suite; confirm the only failures are the known
      `GEMINI_API_KEY`-dependent ones (pre-existing).
- [ ] Update the Status snapshot table above; move completed rows to ✅.
- [ ] Decide with the user whether to open a PR from `claude/project-status-remaining-i5aadr`.
