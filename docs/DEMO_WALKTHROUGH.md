# TrustMesh Live Defense Walkthrough

> **Duration:** 5–7 minutes
> **Goal:** Demonstrate that TrustMesh is a working, tested system that can detect trust violations in A2A negotiations and prove tamper-evidence in a cryptographic ledger.

---

## 0. One-Sentence Pitch

> "TrustMesh is a real-time trust verification layer for AI-to-AI negotiations — it scores every message for policy compliance, flags manipulation, and seals the transcript in a tamper-evident cryptographic ledger."

---

## 1. Show the Dashboard (1.5 min)

**Prerequisite:** Docker containers are running and seeded. Before presenting, confirm the session you want to demo is the first one seeded in the DB, since the tamper script defaults to it when no session ID is passed.

```bash
# From the project root:
docker compose up --build -d

# Wait ~10s for services to start, then seed the demo data:
docker compose exec backend python scripts/seed_demo_data.py
docker compose exec backend python scripts/seed_ledger_entries.py
```

Open **http://localhost:80** in a browser.

**What to point at:**
- The **Price Negotiation chart** — shows buyer offers vs seller counter-offers over 5 turns. This is real data from a seeded session with actual price movement.
- The **Trust Score panel** (left side below the chart) — Buyer 88/100, Seller 50/100. The seller scored lower because of multiple violations.
- The **Ledger panel** (further down) — 5 cryptographically signed entries with `Chain Verified ✓` green badge.
- The **Phase Roadmap** — shows which phases are done vs pending.

**Script:**
> "Here's the live dashboard. We have a completed negotiation between a buyer agent and a seller agent — you can see the price negotiation chart showing how they moved from an initial offer to a final price. Below that, the Trust Engine has evaluated both agents. The buyer scored 88 — one violation for exceeding their budget cap. The seller scored 50 — two violations including a currency swap and a broken commitment."

---

## 2. Trust Scores with a Real Violation (1.5 min)

Scroll to the **Trust Score** section.

**What to point at:**
- **Buyer gauge:** 88/100, stable trend, 1 violation
- **Seller gauge:** 50/100, stable trend, 2 violations (shown as counts below the gauge)
- **Violations list** (right panel): 3 flagged items

**Script:**
> "Let's look at the violations. The first one is **CRITICAL** — the seller used USD currency instead of INR, which violated the policy. The detector flagged this as a `POLICY_VIOLATION` with reason 'Found unexpected currency USD in delivery terms.' The second violation is a budget cap exceeded by the buyer — HIGH severity. And the third is a **BROKEN_COMMITMENT** — the seller committed to INR but then introduced USD, which is both a policy violation and a broken commitment. Each violation shows the detector name, the turn number where it happened, and a plain-English description."

> "These violations were detected by the **CommitmentConsistencyChecker** and **PolicyDeviationFlagger** — both running on rule-based logic without LLM calls, which means they respond instantly."

---

## 3. The Tamper-Detection Moment (2 min)

This is the "watch this" moment.

**Step 1 — Show the verified ledger:**

Scroll to the **Cryptographic Ledger** panel. Point out:
- 5 entries, each with a sequence number and truncated hash
- The green **"Chain Verified"** badge

```bash
# Verify the current state:
docker compose exec backend python scripts/tamper_ledger_demo.py

# Expected output:
#   Chain: [before tamper] VALID
```

**Script:**
> "Every message in this negotiation is digitally signed using Ed25519 and chained with SHA-256 hashes. The green badge says 'Chain Verified' — every hash links correctly to the next one."

**Step 2 — Break the chain (live):**

```bash
docker compose exec backend python scripts/tamper_ledger_demo.py
```

Expected output:
```
Session: e22b6f28-...
Action: TAMPER
  Entries: 5
  Chain: [before tamper] VALID
  Tampered entry sequence=1: price 125.0 -> 999999.99
  Chain: [after tamper] BROKEN (broken at sequence=1)
  TAMPER DETECTED — ledger is tamper-evident
  Run with --restore to revert and re-validate.
```

**Script:**
> "Now watch this. I'm going to simulate a database-level attack — changing the price in the first ledger entry. The script modifies the JSON payload stored in the database."

**Step 3 — Refresh the dashboard:**

Hit **F5** (or Cmd+R) in the browser.

**What to point at:**
- The **"Chain Broken"** badge (red, pulsing)
- The **"Tamper Detected"** alert box: *"Entry #1 has been modified or reordered — hash mismatch with previous entry in chain."*
- The first entry row highlighted in **red** with a "broken" badge

**Script:**
> "I just changed a single number in the database — one price field in one entry. But the SHA-256 hash chain caught it immediately. The dashboard now shows a red pulsing 'Chain Broken' badge, a tamper alert telling us exactly which entry was modified — Entry #1 — and that entry is highlighted in red. The chain is mathematically self-auditing."

**Step 4 — Restore, prove recovery:**

```bash
docker compose exec backend python scripts/tamper_ledger_demo.py --restore
```

Expected output:
```
Session: e22b6f28-...
Action: RESTORE
  Chain: [before restore] BROKEN (broken at sequence=1)
  Restored entry sequence=1
  Chain: [after restore] VALID
```

Refresh the dashboard. The green "Chain Verified" badge is back.

**Script:**
> "And we can restore it from the backup — the green badge comes back. This proves two things: first, our tamper detection works, and second, we can always trace exactly what was changed and restore the authentic state."

---

## 4. Closing (30 sec)

**Script:**
> "What you just saw — real-time trust scoring with specific, actionable violations, plus a cryptographically tamper-evident ledger — is the foundation of trustworthy A2A commerce. As AI agents start negotiating contracts, purchases, and settlements autonomously, they need a neutral referee that can verify every message, flag every violation, and prove that the transcript has not been altered. That's what TrustMesh provides."

> "This is live code, running in Docker, with 37 passing tests — 10 of which specifically verify the tamper detection you just saw."

---

## Reference: Key Commands

| Action | Command |
|---|---|
| Start services | `docker compose up --build -d` |
| Seed demo data | `docker compose exec backend python scripts/seed_demo_data.py` |
| Seed ledger entries | `docker compose exec backend python scripts/seed_ledger_entries.py` |
| Check sessions | `curl http://localhost:80/api/v1/sessions` |
| View trust report | `curl http://localhost:80/api/v1/sessions/{id}/trust` |
| View ledger | `curl http://localhost:80/api/v1/sessions/{id}/ledger` |
| Tamper (break chain) | `docker compose exec backend python scripts/tamper_ledger_demo.py` |
| Restore chain | `docker compose exec backend python scripts/tamper_ledger_demo.py --restore` |
| Run tests | `python -m pytest tests/` |

For the defense, ensure the session you want to demonstrate (e.g., the one with 3 violations and 5 ledger entries) is the first session seeded in the DB, as the tamper script defaults to targeting the first session.
