# TrustMesh — SaaS Architecture & Implementation Plan

## Guiding Principle

TrustMesh's core value is the **negotiation engine**: the Buyer/Seller agent orchestration, the Trust Engine's manipulation detection, and the cryptographic ledger. None of that logic needs to know about users, orgs, billing, or auth. The entire pivot is about wrapping that engine in a **tenancy boundary** — every negotiation session gets an owner, every API call gets an identity, every query gets filtered.

Treat the negotiation engine as an internal service with one new required input: `(user_id, org_id)`. Everything else in this doc is plumbing around that.

---

## 1. Authentication & Authorization

### Recommendation: Clerk

For a B2B/prosumer SaaS with an "Organizations" concept baked into your requirements, **Clerk** is the strongest fit:

- Native **Organizations** primitive (members, roles, invitations) — maps directly to your `Organizations` requirement instead of you building it from scratch.
- Drop-in React components (`<SignIn/>`, `<SignUp/>`, `<OrganizationSwitcher/>`) — fast frontend integration with Vite/React.
- Issues short-lived JWTs verifiable in FastAPI via JWKS — no vendor lock-in on the backend.
- Webhooks (`user.created`, `organization.membership.created`) let you keep a local `users`/`organizations` mirror in Postgres for fast joins with negotiation data.

**Alternative: Supabase Auth** — worth considering *only if* you also move to Supabase Postgres, since you'd get auth + DB + Row-Level Security in one platform with less integration surface. Weaker org/RBAC primitives than Clerk out of the box, but tighter DB story.

**DIY option: `fastapi-users` + JWT** — avoid unless you have a hard reason to self-host identity (e.g., compliance). More work, no material benefit at your stage.

**Decision:** Clerk for identity/session, Postgres as source of truth for domain data (users mirrored via webhook).

### Session Management

- Clerk issues a short-lived access JWT (session token) + handles refresh client-side automatically.
- Frontend attaches the JWT as `Authorization: Bearer <token>` on every API call.
- FastAPI verifies the JWT against Clerk's JWKS endpoint (cached, rotated) using `python-jose` or `pyjwt`.
- No server-side session store needed — auth is stateless; **you only store domain state** (who owns what).

```python
# app/auth/dependencies.py
from fastapi import Depends, HTTPException, Header
from app.auth.clerk import verify_jwt
from app.db.models import User

async def get_current_user(authorization: str = Header(...)) -> User:
    token = authorization.removeprefix("Bearer ").strip()
    claims = verify_jwt(token)  # validates signature, exp, issuer via JWKS
    user = await User.get_or_404(clerk_user_id=claims["sub"])
    return user

def require_role(role: str):
    async def checker(user: User = Depends(get_current_user)):
        if user.role != role and user.role != "admin":
            raise HTTPException(403, "Insufficient permissions")
        return user
    return checker
```

### RBAC Model

Two roles to start — resist adding more until you have a concrete need:

| Role | Scope |
|---|---|
| `standard` | Full CRUD on their **own** org's negotiation sessions only |
| `admin` | Read access across **all** orgs/sessions; platform monitoring; user management |

Store `role` in your local `users` table (synced from Clerk `publicMetadata.role` via webhook), not solely in Clerk metadata — you want it queryable in SQL joins without a round-trip to Clerk on every request.

---

## 2. Database Migration: SQLite → PostgreSQL

### Migration mechanics

1. Introduce **SQLAlchemy 2.0 ORM models** mirroring your current SQLite schema (if you're on raw `sqlite3`, this is the first real refactor — worth doing regardless of the SaaS pivot).
2. Add **Alembic** for versioned migrations.
3. Stand up a hosted Postgres instance (Neon, Supabase, or RDS — Neon/Supabase for fast start, RDS if you're already AWS-committed).
4. Write a one-time data migration script: read existing SQLite rows → bulk insert into Postgres via `COPY` or SQLAlchemy bulk operations. Assign all pre-existing (pre-auth) sessions to a `system` organization so nothing is orphaned.
5. Cut the app's DB connection string over; keep SQLite path available in a feature-flagged dev mode only.

### New Schema

```
organizations
  id (uuid, pk)
  name
  clerk_org_id (unique)
  plan_tier            -- free / pro / enterprise
  created_at

users
  id (uuid, pk)
  clerk_user_id (unique)
  email
  org_id (fk -> organizations.id)
  role                  -- standard | admin
  created_at

negotiation_sessions
  id (uuid, pk)
  user_id (fk -> users.id)          -- owner
  org_id (fk -> organizations.id)   -- tenant boundary
  buyer_config (jsonb)              -- agent params user defined
  seller_config (jsonb)
  status                            -- pending | running | completed | failed
  ledger_root_hash
  created_at, completed_at

messages
  id (uuid, pk)
  session_id (fk -> negotiation_sessions.id)
  sender                            -- buyer | seller
  content
  trust_score
  sequence_num
  signature
  created_at

trust_engine_flags
  id (uuid, pk)
  message_id (fk -> messages.id)
  tactic_type                       -- e.g. anchoring, false_urgency
  severity
  detected_at

ledger_entries                      -- your existing crypto ledger, unchanged internally
  id (uuid, pk)
  session_id (fk -> negotiation_sessions.id)
  prev_hash
  entry_hash
  payload
  signature
  created_at

api_keys                            -- optional, for programmatic/org-level access
  id (uuid, pk)
  org_id (fk -> organizations.id)
  key_hash
  scopes
  created_at

audit_logs                          -- admin visibility
  id (uuid, pk)
  user_id (fk -> users.id)
  action
  resource_type, resource_id
  created_at
```

**Indexes to add immediately:** `negotiation_sessions(user_id)`, `negotiation_sessions(org_id, created_at)`, `messages(session_id, sequence_num)`.

**Defense in depth:** if you land on Supabase, enable **Row-Level Security** on `negotiation_sessions`/`messages` keyed to `org_id` so tenant isolation holds even if an application-layer filter is ever missed. If you go RDS/Neon, enforce isolation purely at the query/service layer (see §4) — just be disciplined about it, since there's no DB-level backstop.

---

## 3. Frontend Architecture

**Stack: Astro + Tailwind v4**, with React used only as *islands* for the genuinely interactive pieces. This is a better fit than a pure React/Vite SPA for TrustMesh specifically:

- The landing page, pricing, and docs are static content — Astro ships **zero JS** for these by default, which a pure React app can't do without extra work.
- The dashboard's interactive parts (launch form, live transcript, admin tables) become React islands via `@astrojs/react`, hydrated with `client:load`/`client:visible` — so you still get real React state/hooks exactly where you need them, without paying the SPA-bundle cost on pages that don't need it.
- Auth via `@clerk/astro` (Clerk's official Astro SDK) — middleware-based route protection at the Astro routing layer, which is a cleaner mechanism than client-side redirect guards.
- Tailwind v4 config is CSS-first (`@import "tailwindcss"` + `@theme` block, no `tailwind.config.js` needed for the common case), wired in via the `@tailwindcss/vite` plugin in `astro.config.mjs`.

Your **existing React/Vite monitoring dashboard doesn't need to be thrown away on day one** — it can keep running standalone until Phase 4, when its logic gets ported into Astro's admin routes (mostly a lift-and-shift of the table/chart components as islands, not a rewrite).

### Route structure

```
src/pages/
  index.astro              public landing page (static)
  pricing.astro             public (static)
  sign-in.astro, sign-up.astro   Clerk <SignIn/>/<SignUp/> components as islands

  dashboard/
    index.astro             (protected) list of user's sessions — island: SessionList.tsx
    new.astro                (protected) form: define buyer/seller params, launch — island: LaunchForm.tsx
    sessions/[id].astro      (protected) live transcript, trust flags, ledger check — island: SessionView.tsx
  settings.astro             (protected) org settings, members, API keys

  admin/
    index.astro              (admin-only) cross-org platform monitor
    users.astro                 (admin-only) user/org management
    trust-engine.astro          (admin-only) aggregate tactic analytics
```

### Route protection

Astro middleware is the right layer for this — it runs before the page even starts rendering, so protected pages never begin building for an unauthenticated request:

```ts
// src/middleware.ts
import { clerkMiddleware, createRouteMatcher } from "@clerk/astro/server";

const isProtectedRoute = createRouteMatcher(["/dashboard(.*)", "/settings"]);
const isAdminRoute = createRouteMatcher(["/admin(.*)"]);

export const onRequest = clerkMiddleware((auth, context) => {
  const { userId, sessionClaims, redirectToSignIn } = auth();

  if (isProtectedRoute(context.request) && !userId) {
    return redirectToSignIn();
  }
  if (isAdminRoute(context.request) && sessionClaims?.publicMetadata?.role !== "admin") {
    return context.redirect("/dashboard");
  }
});
```

### Other structural changes

- **Islands, not a full SPA:** `SessionList.tsx`, `LaunchForm.tsx`, `SessionView.tsx` are React components hydrated with `client:load` inside otherwise-static `.astro` pages. Astro owns routing/layout; React only owns the stateful widget it's mounted in.
- **State:** TanStack Query still fits well inside the islands for server state (session polling, mutations). No client-side router needed — Astro's file-based routing replaces React Router entirely.
- **Real-time transcript view:** the `SessionView.tsx` island subscribes via WebSocket/SSE rather than polling (see §4).
- **Existing read-only dashboard:** its component logic (tables, charts) gets ported into the `/admin` islands in Phase 4 — structurally the same "watch negotiations happen" UI, just scoped to `admin` instead of `org_id`, now living inside Astro instead of standalone Vite.
- **Tailwind v4 setup:** `astro.config.mjs` adds the `@tailwindcss/vite` plugin; `src/styles/global.css` does `@import "tailwindcss";` plus an `@theme` block for design tokens — no separate `tailwind.config.js` needed for the standard case.

---

## 4. Backend (FastAPI) Modifications

### Core change: every session-touching endpoint requires identity + ownership check

```python
@router.get("/api/v1/sessions/{session_id}")
async def get_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
):
    session = await NegotiationSession.get_or_404(session_id)
    if session.user_id != user.id and user.role != "admin":
        raise HTTPException(403, "Not your session")
    return session

@router.get("/api/v1/sessions")
async def list_sessions(user: User = Depends(get_current_user)):
    # non-admins only ever see their own org's sessions — enforce in the query, not after fetching
    return await NegotiationSession.filter(org_id=user.org_id)

@router.get("/api/v1/admin/sessions")
async def admin_list_all(user: User = Depends(require_role("admin"))):
    return await NegotiationSession.all()
```

**Rule of thumb:** never fetch-then-check-then-return for lists — filter at the query itself (`WHERE org_id = :org_id`), so there's no code path that can accidentally leak cross-tenant rows. Reserve the fetch-then-check pattern for single-resource lookups by ID, as above.

### Launching a negotiation (user-defined parameters)

Currently your Buyer/Seller agents are presumably hardcoded or config-file driven. Now:

- New endpoint `POST /api/v1/sessions` accepts user-supplied `buyer_config`/`seller_config` (persona, constraints, negotiation goals, max rounds).
- Validate configs against a Pydantic schema with sane bounds (max negotiation rounds, allowed model choices) — this is now **user input reaching your agent orchestration**, so treat it with the same care as any external input (prompt injection surface, cost control on LLM calls, runaway loops).
- Kick off the negotiation as a **background job**, not inline in the request/response cycle — agent negotiations can run for many turns/seconds:
  - MVP: FastAPI `BackgroundTasks`.
  - At scale: Celery or RQ + Redis, so job execution is decoupled from the API process and retryable.
- The job writes to `messages`/`ledger_entries` as it runs; the frontend subscribes via WebSocket to watch it happen live.

```python
@router.websocket("/ws/sessions/{session_id}")
async def session_stream(websocket: WebSocket, session_id: UUID, token: str = Query(...)):
    user = await verify_jwt_and_get_user(token)
    session = await NegotiationSession.get_or_404(session_id)
    if session.user_id != user.id and user.role != "admin":
        await websocket.close(code=4403)
        return
    await websocket.accept()
    async for event in subscribe_to_session(session_id):  # pub/sub, e.g. Redis
        await websocket.send_json(event)
```

### Other backend changes

- **API versioning:** prefix everything `/api/v1/` now, before external consumers exist — cheap now, expensive later.
- **Rate limiting:** per-user/per-org via `slowapi` or a Redis token bucket — you're now paying for LLM calls on behalf of arbitrary signed-up users, so this isn't optional.
- **Config/secrets:** move DB URL, Clerk keys, LLM API keys out of `.env`-committed files into a real secrets manager (even just your host's env var injection) per environment (dev/staging/prod).
- **Trust Engine & Ledger code:** should require **zero changes** to their internal logic — only their call sites change, to pass through `session.id` and pull config from the user-supplied `buyer_config`/`seller_config` instead of hardcoded values. If you find yourself editing Trust Engine internals for this migration, stop — that's a sign tenancy logic is leaking into the engine.

---

## 5. Phased Roadmap

Ordered so the current core AI logic keeps working at every step — nothing is a big-bang cutover.

**Phase 0 — Foundations (no user-facing change)**
- Add SQLAlchemy models + Alembic, even if still pointed at SQLite initially.
- Stand up Postgres instance; stand up Clerk project. Nothing wired in yet.

**Phase 1 — Auth, additive only**
- Integrate Clerk on the frontend (sign-in/sign-up pages exist, but nothing is gated yet).
- Add JWT verification middleware + `users`/`organizations` tables; Clerk webhook syncs new signups into Postgres.
- Existing endpoints remain open (feature-flagged) so the current agent demo keeps functioning.

**Phase 2 — Data migration**
- Add nullable `user_id`/`org_id` columns to existing session tables.
- Backfill existing/demo data into a `system` organization.
- Migrate all data from SQLite → Postgres; switch the connection string.

**Phase 3 — Enforce authorization**
- Make `user_id`/`org_id` required on new sessions.
- Add ownership checks and org-scoped queries to every endpoint (§4).
- Introduce the background job runner for negotiation execution.

**Phase 4 — Frontend restructure**
- Build the protected dashboard shell + route guards.
- Build the "launch negotiation" form (user-defined buyer/seller params) wired to the new authenticated API.
- Repurpose the existing read-only dashboard into the admin cross-org view.

**Phase 5 — Real-time & hardening**
- Add WebSocket/SSE live transcript streaming.
- Add rate limiting, usage-based plan tiers if monetizing.
- Add structured logging + error tracking (Sentry) + basic metrics/dashboards.

**Phase 6 — Launch readiness**
- Audit tenant isolation end-to-end (try to access another org's session ID as a standard user — should always 403).
- Load test the negotiation job pipeline; verify ledger integrity survives concurrent multi-tenant load.
- Containerize (Docker), set up CI/CD, deploy (Fly.io/Render for simplicity, AWS/ECS if you need more control).

---

## What stays untouched

- Buyer/Seller agent orchestration logic.
- Trust Engine's tactic-detection heuristics/models.
- The cryptographic ledger's hashing/signing scheme.

These only gain one new dependency: a `session_id` that's now foreign-keyed to a `user_id`/`org_id` instead of floating free. That's the entire blast radius on your hardest-won code.
