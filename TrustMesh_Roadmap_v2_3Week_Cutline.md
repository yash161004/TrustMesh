# TrustMesh — Revised Roadmap (Solo, 3-Week Checkpoint)

## Checkpoint: August 9, 2026. Whatever is done by then is what ships. Everything else moves to v2 and stays there.

**Context this plan is built against:**
- Solo builder (you), using Antigravity + Opencode as execution agents
- No external deadline — this checkpoint is self-imposed on purpose, because a serious project with no deadline and fast agents is how scope inflates silently
- Backend (Phases 0–6) is done, tested, verified — not touched in this plan
- One blocking data-integrity issue must close before any content/eval work happens (see Phase 0 below)

**Rule for the next 3 weeks:** no new feature ideas get added to this document. If something new comes up, it goes on a separate "parking lot" list, not into an active phase. This is the single most important rule given the pattern of this project so far — restarting scope is the actual risk, not lack of speed.

---

## Phase 0 — Close the Open Bug (Day 1, blocking everything else)

This is not optional and not parallel with anything else. Nothing in Phase E or F touches ManipulationDetector claims until this is done.

- [ ] Merge the corrections to `PROJECT_REPORT.md`, `DEFENSE_PREP.md`, `manipulation-detector-findings.md`, `calibration_metrics.md`, and the `commitments.py` comment — replace all "verified multi-model consensus" claims with the honest status (single-model classification, multi-vote attempted but invalidated by a caching bug, true parallel voting infeasible on free tier).
- [ ] Decide and document ONE of: (a) ship as single-model detector, cut the consensus claim entirely, or (b) label consensus as a documented future direction, not a shipped feature. Do not leave this ambiguous in any doc.
- [ ] Confirm the corrected docs actually read consistently — have Antigravity do one pass reading all four docs back to you, not just diff the flagged lines.

**Done when:** every doc in the repo tells the same true story about what ManipulationDetector actually does today.

**Effort estimate:** half a day, mostly Antigravity execution + your review.

---

## Phase A — Brand & Design System (Days 1–3)

- [ ] Lock two-register design language: Stripe-style gradient for public pages, Linear/Vercel dark precision for the dashboard (already partially built — extend, don't discard).
- [ ] Color ramp (success/warning/danger + gradient stops), type scale, logo/wordmark, favicon.
- [ ] One-page brand brief: tone of voice, 3 taglines, the one-sentence pitch (locked below).
- [ ] Deliverable: a living style-guide page in the Astro app itself, not a separate design tool.

**Locked pitch (do not re-litigate this mid-build):**
> TrustMesh is a platform where AI negotiation agents transact on your behalf, and every message, tactic, and outcome is cryptographically verified and scored for manipulation — so you can trust an automated deal the way you'd trust a human one.

**Done when:** anyone can look at the style guide page and know what "on-brand" means.

**Effort estimate:** 2–3 days. No backend dependency — start immediately.

---

## Phase B — Public Marketing Site (Days 3–8)

- [ ] Hero (headline + subheadline + CTA)
- [ ] Problem/solution section
- [ ] "How it works" (3–4 step flow)
- [ ] Feature bento grid
- [ ] Trust/security section (ledger + Ed25519 — your real differentiator)
- [ ] Pricing page (Free/Pro/Enterprise, matches existing `plan_tier` schema field)
- [ ] Footer with real nav
- [ ] Social proof slot — structure only, leave empty, do not fake testimonials or logos

**Cut if behind schedule:** social proof slot, pricing page can be a single simple table instead of full designed cards.

**Done when:** a stranger can read the URL and explain back what TrustMesh does.

**Effort estimate:** 4–5 days including copywriting.

---

## Phase C — Onboarding & Empty States (Days 8–10)

- [ ] "Create your first negotiation" first-run flow with real pre-filled example values
- [ ] "Load demo data" action using your already-backfilled historical sessions — this is high leverage for near-zero cost, since the data already exists
- [ ] Extend existing SessionList empty state (don't rebuild from zero)

**Cut if behind schedule: the product tour.** Skip it entirely — "Load demo data" does more work for less effort and is the item to protect if time gets tight.

**Effort estimate:** 1–2 days. "Load demo data" alone is worth prioritizing even if nothing else in this phase lands.

---

## Phase D — Dashboard Visual Overhaul (Days 8–15, overlaps with C and F)

- [ ] `LaunchForm.tsx` — icons, validation states, preview panel
- [ ] `SessionList.tsx` — sparkline trust trend, card layout
- [ ] `SessionView.tsx` — chat-bubble transcript styling, ledger-verified badge, trust score as a real gauge
- [ ] Admin panels — tables → recharts (bar for tactic frequency, line for trust trend) using metrics endpoints you already have live data for
- [ ] Settings/org pages visual pass

**Cut if behind schedule, in this order:** settings page polish first, then admin chart upgrades (tables are fine, functional, already true), then LaunchForm preview panel. **Do not cut** SessionView's ledger-verified badge and trust gauge — that's the single highest-impact visual for demonstrating the actual trust story, keep it even if everything else in this phase gets trimmed.

**Effort estimate:** 5–7 days. This is the largest phase — budget accordingly.

---

## Phase E — Feature Expansion (Days 12–18, only if Phases A–D are on track)

**Re-scoped effort estimates — the original plan understated these. Use these numbers, not the old ones.**

**Tier 1 — do these first, cut nothing here if at all possible:**
1. **Analytics/Insights dashboard** — trend charts using metrics endpoints + backfilled data. **Estimate: 1–2 days.** Genuinely cheap, do this first in the phase.
2. **Session export/report (PDF)** — uses the existing PDF skill. **Estimate: 1 day.**
3. **AgentCard directory page** — REVISED estimate: **3–5 days, not "just surface it."** This requires unparking code untouched since Phase 0, a real spec review, and a new public page built from scratch. Only start this if Phases A–D finished on or ahead of schedule. If you're behind at Day 12, skip this entirely for the 3-week checkpoint and put it at the top of the v2 list — it's genuinely your best differentiator, but "best differentiator" doesn't mean "cheap," and shipping it half-built with 17 stale tests is worse than not shipping it.

**Tier 2/3 (templates, notifications, API keys page, comments, leaderboard):** explicitly **not in the 3-week checkpoint.** Parking lot only. Do not start any of these before Aug 9 even if there's spare time — spare time goes to QA (Phase G) and content (Phase F) instead, both of which directly affect whether the checkpoint deliverable is actually presentable.

**Done when:** the story is "negotiation + analytics + reporting" at minimum, "+ verifiable identity" only if genuinely on schedule.

---

## Phase F — Content & Storytelling (Days 10–19, runs parallel to D/E, not after)

- [ ] Real copy pass, no placeholder text anywhere
- [ ] 90-second demo script — written and rehearsed, not improvised. This matters more than any single feature: a well-told story about a smaller product beats an untold story about a bigger one.
- [ ] README overhaul — architecture, trust/verification story, link to demo
- [ ] Screenshots/GIFs from the finished dashboard

**Do not cut this phase for extra features.** A working demo script is worth more at the checkpoint than an unfinished Tier 2 feature.

**Effort estimate:** 2–3 days spread across the parallel window.

---

## Phase G — QA (Days 18–20)

- [ ] Full click-through, Chrome + one other browser
- [ ] Responsive check at 375px / 768px / 1440px on everything new
- [ ] Accessibility pass on new components
- [ ] Lighthouse on the public landing page

**Do not skip this to add features.** An unpolished but functional product with no visible bugs beats a feature-rich product that breaks on click-through in front of someone.

---

## Phase H — Deployment (Days 20–21)

- [ ] Frontend → Vercel, backend → Fly.io/Render
- [ ] Secrets into platform secret managers
- [ ] Live smoke test on production URLs: sign up, launch a real session, watch it complete, check the ledger

**This happens regardless of what got cut above.** A checkpoint with nothing deployed is not a checkpoint.

---

## The Cutline, Stated Plainly

If August 9 arrives and you're behind, this is the order things get dropped, already decided now so you don't have to decide it under time pressure later:

1. AgentCard directory (Phase E, item 3) — first cut
2. Tier 2/3 features — never in scope for this checkpoint anyway
3. Admin chart upgrades — tables still work, not broken, just less pretty
4. Onboarding product tour — never started if time's tight
5. Pricing page polish — simple table is fine

**Never cut:** Phase 0 (the bug correction), the SessionView trust gauge/ledger badge, the demo script, and deployment. These four are the actual minimum for a defensible, honest, working product on August 9.

---

## What Changed From the Original Roadmap

- Added Phase 0 as a hard blocker — the original plan didn't exist yet when the consensus bug was found
- Real effort estimates in days, not vague checkboxes
- Explicit cutline instead of implying everything gets built
- AgentCard reclassified from "cheap, already built" to "3–5 days, cut first if behind" — the original estimate was optimistic
- Tier 2/3 features explicitly excluded from this checkpoint, not just deprioritized
- One rule added that wasn't in the original: no new ideas get added to this document for the next 3 weeks
