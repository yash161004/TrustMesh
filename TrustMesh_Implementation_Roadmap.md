# TrustMesh — Implementation Roadmap

Companion to `TrustMesh_SaaS_Architecture.md`. That doc is the *design*; this is the *build order*. Each phase is safe to ship on its own — the current agent demo keeps running the entire time.

Suggested cadence: each phase is roughly 3–7 days of focused work for a small team/solo dev, but treat the checkpoints as the real unit of progress, not the days.

---

## Phase 0 — Foundations
*Goal: introduce production tooling without touching runtime behavior at all.*

- [ ] Add `SQLAlchemy` (2.0) + `alembic` to the project; write ORM models that mirror your **current** SQLite schema exactly (no new columns yet).
- [ ] Point Alembic at the existing SQLite DB, run `alembic revision --autogenerate` to confirm it produces an empty diff (proves your models match reality).
- [ ] Provision a Postgres instance (Neon or Supabase for fastest start). Keep it empty — don't connect the app yet.
- [ ] Create a Clerk project (dev instance). Do **not** add Clerk components to the app yet — just get keys and confirm you can create a test user from the Clerk dashboard.
- [ ] Add `python-jose` (or `pyjwt`) + a `verify_jwt()` utility that fetches and caches Clerk's JWKS, tested against a manually-generated token from the Clerk dashboard.
- [ ] Scaffold a **new Astro + Tailwind v4** project alongside (not replacing yet) the existing React/Vite dashboard: `npm create astro@latest`, add `@astrojs/react` and `@tailwindcss/vite` integrations, confirm a static placeholder page renders styled with a Tailwind utility class.
- [ ] Confirm the Astro dev server and the existing FastAPI + Vite dashboard can run side by side on different ports with no conflicts — this is purely additive infrastructure at this stage.

**Done when:** app behavior is unchanged; you have Postgres, Clerk, JWT verification, and a working (empty) Astro+Tailwind v4 project, all proven in isolation — nothing wired into FastAPI, and the old React/Vite dashboard untouched.

---

## Phase 1 — Auth, additive only
*Goal: users can sign up and log in; nothing is gated yet.*

**Frontend (in the new Astro project)**
- [ ] Install `@clerk/astro`, add the integration in `astro.config.mjs`.
- [ ] Add `src/middleware.ts` with `clerkMiddleware()` — present but not yet enforcing any redirects (log matched routes only, to confirm it's wired correctly).
- [ ] Add `/sign-in`, `/sign-up` pages using Clerk's Astro components (`<SignIn />`/`<SignUp />` as islands).
- [ ] Add a header/nav auth state (logged-in vs logged-out, via `<SignedIn>`/`<SignedOut>`) — cosmetic only, no route protection yet.

**Backend**
- [ ] Add `users` and `organizations` tables via Alembic migration (still on SQLite is fine here, or jump straight to Postgres if Phase 2 is imminent).
- [ ] Add a Clerk webhook endpoint (`POST /api/v1/webhooks/clerk`) handling `user.created` and `organization.membership.created` → upserts into local `users`/`organizations`.
- [ ] Verify webhook signature (Clerk provides a signing secret — don't skip this, it's an open endpoint).
- [ ] Add `get_current_user` FastAPI dependency (from the architecture doc) but **don't apply it to any route yet** — just unit test it against a real token.

**Done when:** you can sign up via the UI, see the user appear in your local `users` table via webhook, and manually call a test endpoint with a Bearer token that correctly resolves to that user. Existing negotiation endpoints remain fully open and functional.

---

## Phase 2 — Data migration to Postgres
*Goal: production-grade DB, still single-tenant in behavior.*

- [ ] Add `user_id` (nullable) and `org_id` (nullable) columns to `negotiation_sessions` via Alembic migration.
- [ ] Write a one-off migration script: read all rows from SQLite → bulk insert into Postgres (via `COPY` or SQLAlchemy `bulk_insert_mappings`). Run it against a Postgres **staging** DB first.
- [ ] Create a `system` organization row; backfill all existing session rows with `org_id = system.id`, `user_id = NULL`.
- [ ] Diff row counts and spot-check a few sessions (including their `messages` and `ledger_entries`) between SQLite and Postgres before cutting over.
- [ ] Switch `DATABASE_URL` to Postgres in a staging environment; run the app there for a burn-in period.
- [ ] Cut production over. Keep the SQLite file as a cold backup, don't delete it yet.

**Done when:** the app runs entirely on Postgres, all historical data is present and verified, and nothing in the frontend/API contract has changed.

---

## Phase 3 — Enforce authorization
*Goal: this is the phase where TrustMesh actually becomes multi-tenant.*

- [ ] Make `user_id`/`org_id` **required** (NOT NULL) on new `negotiation_sessions` rows going forward (existing `system`-org rows stay as-is).
- [ ] Apply `get_current_user` to every session-related route. Start with read endpoints (`GET /sessions`, `GET /sessions/{id}`) — lower risk than write paths.
- [ ] Rewrite list endpoints to filter at the query level: `WHERE org_id = :org_id`, never fetch-all-then-filter-in-Python.
- [ ] Add the ownership check pattern to single-resource endpoints (`GET/POST/DELETE /sessions/{id}`): 403 if `session.user_id != user.id and user.role != "admin"`.
- [ ] Add `role` column usage: implement `require_role("admin")` dependency; add one real admin-only endpoint (`GET /api/v1/admin/sessions`) to prove the pattern end-to-end.
- [ ] Write an authorization test suite: as User A, attempt to read/write User B's session by ID → must always 403. This is the single most important test suite in the whole migration — don't skip it.
- [ ] Introduce the negotiation launch flow as a background job:
  - [ ] `POST /api/v1/sessions` accepts `buyer_config`/`seller_config`, validated via Pydantic with bounds (max rounds, allowed models).
  - [ ] Move agent negotiation execution off the request/response cycle — start with FastAPI `BackgroundTasks`; only reach for Celery/RQ + Redis once you actually see request timeouts or need retries.
  - [ ] Confirm the Trust Engine and ledger code required **zero internal changes** — only their call sites now pass `session.id` and user-supplied config instead of hardcoded values.

**Done when:** a standard user can only ever see/act on their own org's sessions (proven by the test suite above), an admin can see everything, and launching a negotiation runs asynchronously without blocking the API.

---

## Phase 4 — Frontend restructure
*Goal: the actual interactive product experience.*

- [ ] Flip `src/middleware.ts` from log-only to actually enforcing: redirect unauthenticated users on `/dashboard(.*)` and `/settings`, redirect non-admins on `/admin(.*)`.
- [ ] Build `dashboard/index.astro` + `SessionList.tsx` island — list of the user's own sessions (status, created date, quick trust-score summary), backed by TanStack Query against the now-authenticated API.
- [ ] Build `dashboard/new.astro` + `LaunchForm.tsx` island — form to define `buyer_config`/`seller_config` (persona, constraints, goals, round limits) → calls `POST /api/v1/sessions`.
- [ ] Build `dashboard/sessions/[id].astro` + `SessionView.tsx` island — transcript view + Trust Engine flags + ledger verification badge, polling initially (upgrade to real-time in Phase 5).
- [ ] Port your existing read-only monitoring dashboard's components into `admin/index.astro` (cross-org view) — this is the phase where the old React/Vite dashboard gets retired.
- [ ] Add `settings.astro` for basic org info (read-only display at first — org switching/invites can come later via Clerk's `<OrganizationSwitcher/>` island).
- [ ] Style pass using Tailwind v4 `@theme` tokens — establish a real design system (palette, type scale) rather than default utility soup, per the frontend-design guidance: this is a good moment to give the product an actual visual identity now that it has real UI surface.

**Done when:** a brand-new user can sign up, land on an empty dashboard, configure and launch a negotiation, and watch it complete — entirely through the UI, with zero manual DB/API intervention.

---

## Phase 5 — Real-time & hardening
*Goal: production polish.*

- [ ] Add a pub/sub layer (Redis pub/sub is enough at this scale) that the background negotiation job publishes events to as messages/ledger entries are written.
- [ ] Add `WS /ws/sessions/{session_id}` — authenticated via token, ownership-checked before `accept()`, streaming events to the frontend.
- [ ] Swap `/dashboard/sessions/:id` from polling to WebSocket subscription.
- [ ] Add rate limiting (`slowapi` or Redis token bucket) per user/org on session-creation endpoints — this is your cost control on LLM spend.
- [ ] Add structured logging (JSON logs) and wire up error tracking (Sentry) on both frontend and backend.
- [ ] Add basic usage metrics: sessions per org, average trust score, tactic-detection frequency — feeds both the admin panel and, later, billing.

**Done when:** negotiations feel live in the UI, a runaway user can't blow your LLM budget unnoticed, and you'd actually find out about a production error before a user reports it.

---

## Phase 6 — Launch readiness
*Goal: confident external launch.*

- [ ] Full tenant-isolation audit: attempt cross-org access on every single endpoint, not just the ones you remembered to test in Phase 3.
- [ ] Load test the negotiation pipeline under concurrent multi-tenant load — confirm the ledger's hash-chaining stays correct under concurrency (this is the one place a race condition could be genuinely dangerous, since it's your integrity guarantee).
- [ ] Containerize (Dockerfile for FastAPI, Dockerfile or static build for the Vite frontend).
- [ ] Set up CI/CD (GitHub Actions is fine): run the auth test suite on every PR, block merges on failure.
- [ ] Choose and configure hosting (Fly.io/Render for simplicity; AWS/ECS if you need more infra control) plus managed Postgres and Redis.
- [ ] Set environment-specific secrets (Clerk keys, DB URL, LLM API keys) via your host's secret manager — confirm nothing sensitive is in a committed `.env`.
- [ ] Soft launch to a handful of real users; watch the admin panel and error tracking closely for the first week before wider release.

**Done when:** you'd be comfortable posting a public signup link.

---

## Sequencing notes

- **Phases 0–2 are invisible to users** — safe to do at your own pace without any launch pressure.
- **Phase 3 is the one true point of no return** — once authorization is enforced, the old "anyone can hit any endpoint" demo mode is gone. Do the authorization test suite *before* removing the open-access fallback, not after.
- **Phases 4–6 can partially overlap** — e.g., start real-time WebSocket work while still polishing the dashboard form, since they touch different files.
