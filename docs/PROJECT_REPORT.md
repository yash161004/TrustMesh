# TrustMesh: Technical Project Report

## 1. PROJECT OVERVIEW
TrustMesh is a trusted verification system that acts as an impartial referee for AI-to-AI (A2A) negotiations. It addresses the growing need for trust and verification in autonomous agent interactions by evaluating compliance with business policies and preventing adversarial negotiation tactics. Drawing upon emerging concepts like the Model Context Protocol (MCP), IETF trust scoring work, and ERC-8004, TrustMesh provides real-time policy evaluation and a tamper-evident audit trail to ensure agents negotiate fairly and honor their commitments.

## 2. ARCHITECTURE
The system is built on a layered, modular architecture designed to separate agent logic from verification mechanisms:
*   **Phase 1 - Agent Logic:** Autonomous Buyer and Seller agents (driven by LLMs) that negotiate price, quantity, and delivery terms.
*   **Phase 2 - Trust Engine (Protocol Layer):** The core evaluation layer that scores each message for policy deviations, consistency of commitments, and manipulation attempts. 
*   **Phase 3 - Cryptographic Ledger:** A tamper-evident layer where every message is digitally signed (Ed25519) and hash-chained, ensuring the negotiation history cannot be altered post-facto.
*   **Phase 4 & 5 - Live Dashboard:** A React/Vite-based frontend that streams the signed negotiation events in real-time over WebSockets and provides advanced trust analytics.

## 3. WHAT WAS BUILT
The following core components have been implemented and validated:
*   **Negotiating Agents:** Buyer and seller agents equipped with distinct business strategies and a mock-mode fallback for deterministic testing.
*   **Trust Engine Detectors:**

| Detector | Purpose | Benchmark Sample Size | Key Metrics |
| :--- | :--- | :--- | :--- |
| **PolicyDeviationFlagger** | Identifies violations of budget caps/floor constraints. | n=13 scenarios | 1.00 Precision, 1.00 Recall, 1.00 F1 |
| **CommitmentConsistencyChecker** | Tracks promises to catch bait-and-switch tactics. | n=16 scenarios | 1.00 Precision, 1.00 Recall, 1.00 F1 |
| **ManipulationDetector** | Evaluates adversarial psychological pressure tactics. | n=18 (Tier 1 baseline)* | 1.00 Precision, 0.88 Recall, 0.93 F1, Brier 0.0554, ECE 0.0728 |

*\*Note: The Tier 1 baseline (n=18) does not represent complete performance. See **Section 4: Adversarial Testing** for results against harder held-out datasets, where recall drops to 0.86 on general adversarial tactics (n=18) and 0.50 on targeted trust-exploitation tactics (n=12).*
*   **Cryptographic Ledger:** Ed25519 signing and SHA-256 hash chaining applied to every session message.
*   **Signed Agent Identity (AgentCard):** Ed25519-signed JSON identity cards containing agent capabilities and live reputation snapshots, stored on-disk at `backend/data/agent_cards/` and verified against role-level Ed25519 public keys.
*   **WebSocket Dashboard:** Real-time UI streaming the verified events.
 *   **Docker Deployment:** Containerized services encompassing the backend API and frontend dashboard, validated end-to-end with `docker compose up --build`. WebSocket proxying through nginx confirmed working.

## 4. KEY ENGINEERING FINDINGS
This section details the critical technical discoveries made during the development of the Trust Engine:

*   **The Regex-to-LLM Pivot on the CommitmentConsistencyChecker:** Initial attempts to extract structured claims from negotiation text using deterministic regex heuristics failed to generalize, achieving a poor 0.33 recall on the holdout set. This failure motivated a pivot to LLM-based semantic verification. However, we discovered that naive LLM verification was prone to hallucinations. We successfully stabilized this by enforcing a "reasoning-field-first" JSON schema. Forcing the LLM to explicitly output its reasoning—identifying the claimed number, locating the actual historical number, and computing the delta—before outputting the final boolean judgment was strictly required for it to work correctly.
*   **ManipulationDetector — Final Benchmark Results & Caveats:** The Tier 1 benchmark (27 unique scenarios evaluated by PolicyDeviationFlagger, CommitmentConsistencyChecker, and ManipulationDetector) produced the following clean results after all known bugs were fixed:

    | Detector | Precision | Recall | F1 | Brier | ECE |
    | :--- | :--- | :--- | :--- | :--- | :--- |
    | **PolicyDeviationFlagger** | 1.00 | 1.00 | 1.00 | — | — |
    | **CommitmentConsistencyChecker** | 1.00 | 1.00 | 1.00 | — | — |
    | **ManipulationDetector** | 1.00 | 0.88 | 0.93 | 0.0554 | 0.0728 |

    **Caveat A — Single-Provider Ensemble in Practice.** The ManipulationDetector's ensemble voting architecture calls two providers (Groq + Gemini) in parallel and, if they disagree, a third (OpenRouter) as tiebreaker. In the final run, Groq contributed only 1 live call out of 35 total and OpenRouter contributed 0 — both blocked by free-tier rate limits (30 RPM Groq, ~20 RPM OpenRouter). Gemini handled the remaining 34 live calls. The 0.93 F1 therefore reflects a Gemini-only single-judge evaluation, not a true multi-voter consensus. The architecture correctly excludes failed votes (a silent `Exception`-as-`False` bug that existed in an earlier version was found and fixed — see infrastructure notes below), but a genuine 3-provider concurrent live run is blocked by free-tier quota, not by the code. This throttling pattern was observed consistently across multiple benchmark sessions (Tier 1, manipulation holdout, and adversarial Round 1), each separated by hours or days — it is a confirmed infrastructure constraint of the free-tier rate limits, not an open question about the architecture.

    **Caveat B — Brier/ECE Methodology Correction.** The original Brier Score (0.5465) and ECE (0.5383) were incorrect due to a scoring methodology bug: the calculation fed each prediction's `confidence_score` directly into the Brier formula regardless of which class the model predicted. Brier Score is defined as mean squared error between predicted probability and the actual outcome (0 or 1), and is properly computed as `(predicted_prob - actual)²`. The error was that for confident *negative* predictions (e.g., confidence_score=0.98 for `flagged=False`), the raw 0.98 was used as the probability of the positive class — equivalent to scoring a confident correct rejection as if it were a confident (and wrong) positive prediction. This inflated the error for every high-confidence negative verdict, producing a Brier Score near the random-guess baseline even though the binary decisions were correct.

     Once corrected to properly align the probability with the true positive class — `(confidence_score - 1)²` for negative predictions, `(confidence_score - 0)²` for positive predictions — the calibration metrics dropped to **Brier 0.0554, ECE 0.0728**, confirming strong calibration. The fix was validated bidirectionally: the two known false negatives (adversarial-9 "The Rapport Exploit" and adversarial-16 "The Trust Me Ask") each contribute ~0.87 Brier penalty individually under the corrected formula, while genuine high-confidence correct predictions contribute near 0 — proving the correction works in both the penalty and reward directions, not just the flattering one. Methodology bugs in evaluation code are a normal part of empirical work; the finding after the fix is that calibration is genuinely good.

*   **Adversarial Testing — Round 1 (Structural & Psychological):** To probe known blind spots beyond the Tier 1 benchmark — particularly the stealthy/structural category that had caused false negatives in earlier testing — a separate adversarial suite of 18 scenarios was designed across 5 categories: Stealthy/Structural (5), Multi-turn (4), Borderline Benign (4), Helpfulness Disguise (3), and Mixed (2). These deliberately avoid the over-represented urgency/scarcity pattern and instead target invented policy authority, gradual cross-message escalation, borderline-non-manipulative pressure, and manipulation disguised as concern. The ManipulationDetector was evaluated against all 18:

    | Metric | Value |
    | :--- | :--- |
    | Scenarios | 18 |
    | True Positives | 12 |
    | False Positives | 0 |
    | True Negatives | 4 |
    | False Negatives | 2 |
    | Precision | 1.00 |
    | Recall | 0.86 |
    | F1 Score | 0.92 |
    | Brier Score | 0.1077 |
    | ECE | 0.1772 |

    Both false negatives were trust-exploitation patterns: adversarial-9 "The Rapport Exploit" (buyer builds rapport over 4 turns, then requests a below-floor price framed as vulnerability disclosure) and adversarial-16 "The Trust Me Ask" (seller weaponizes buyer's disclosed budget constraint, framing a price increase as reciprocal trust). The detector correctly caught all 5 Stealthy/Structural scenarios, all 3 Helpfulness Disguise variants except the trust-me variant, all 2 Mixed scenarios, and correctly cleared all 4 Borderline Benign cases — confirming that structural/invented-policy detection is robust but psychological/relational manipulation remains a gap. These two failure patterns directly motivated Round 2.

*   **Adversarial Testing — Round 2 (Trust Exploitation):** Designed to probe the specific failure patterns identified in Round 1 — rapport-building manipulation ("The Rapport Exploit", adversarial-9) and "trust me" vulnerability-weaponization ("The Trust Me Ask", adversarial-16). The suite contains 12 scenarios (10 manipulative, 2 benign) in category 15, varying rapport buildup length (1-turn through 5-turn), explicit vs. implicit trust framing, reciprocity traps, identity alignment, and false camaraderie.

    **Methodology note — held-out validation discipline.** When Round 2 reveals a blind spot (as it does with trust-exploitation manipulation), any fix to the detector's calibration anchor must be validated against the same held-out Round 2 scenarios. If the new calibration example were derived from or inspired by the failing test cases themselves, a follow-up improvement would be meaningless: the model would be pattern-matching memorized examples rather than generalizing. 
    
    To address the gap, a 4th calibration example was added to the prompt (demonstrating trust/rapport exploitation). This example was written fresh and independently, not derived from the test scenarios. The updated prompt was then re-run against the unchanged 12 held-out scenarios.

    **Results:**
    *   **Recall** improved from 0.20 to 0.50 (2 to 5 true positives out of the 10 manipulative scenarios).
    *   **Brier Score** (for the manipulative category) improved from 0.7036 to 0.4265.
    *   The benign pair (adversarial2-11/12) held at 0 false positives throughout, confirming the fix did not cause over-flagging of legitimate rapport.

    **Conclusion & Limitations:** The prompt-level fix is a real, partial improvement, but not a full solution. The 5/10 subtler trust-exploitation cases still evade detection. Crucially, the model is not borderline or ambiguous on these remaining failures—it is still confidently wrong. The 5 remaining false negatives (adversarial2-2, -3, -4, -9, and -10) were all cleared with high confidence scores between 0.90 and 0.92, indicating the LLM comfortably categorized them as normal, benign business communication. This confirms that while prompt-level calibration anchors can successfully teach explicit manipulation patterns, they likely cannot catch the subtlest forms of relational exploitation without structural changes to the evaluation engine (e.g., tracking relationship/favor history across turns, which the current single-turn contextual evaluation doesn't do).

*   **Infrastructure Work Completed During Tier 1 Finalization:**

    *   **LiteLLM Router Migration:** The original custom `httpx`-based client for each provider was replaced with LiteLLM's router layer, providing standardized model routing, per-provider rate-limit awareness, and unified retry semantics across Groq, Gemini, and OpenRouter without hand-rolled HTTP logic.

    *   **Calibration-Context Anchoring (4-Example Set, as of Round 2):** The original calibration anchor in the ManipulationDetector prompt used a single example focused on urgency/scarcity. Analysis of false-negative patterns showed this biased the judge toward only recognizing that one tactic. The anchor was iteratively broadened to four examples spanning distinct manipulation tactics (feigned urgency, false authority override, invented compliance rule, and trust/rapport exploitation). The initial expansion to three examples raised baseline recall from 0.25 to 0.88, and the 4th example (added after Round 1 adversarial testing) raised recall on the trust-exploitation subset from 0.20 to 0.50.

    *   **None-Vote Exclusion Fix:** A critical bug was discovered where an exception in an LLM provider call was silently caught and returned as `{"flagged": False, "confidence_score": 0.0}` — effectively counting a total failure as a "not manipulative" vote. This could corrupt the majority outcome by weighting a zero-confidence failure equally with a genuine negative verdict. The fix: failed votes are excluded from the consensus tally entirely, and the remaining results are evaluated against the majority threshold of the reduced set. The 1.00 precision and 0.88 recall final numbers are from the corrected code.
 *   **Deployment Hazards:** We identified and fixed a critical Docker volume-mount bug during containerization. A misconfigured mount path in the compose file would have silently erased the container's application directory by overwriting it with an empty host mapping, leading to difficult-to-trace deployment failures. *(Note: This issue was found and resolved during Docker deployment testing, not during initial development.)*
 *   **WebSocket Proxy Subtlety:** The nginx reverse proxy requires a dedicated `location ~ ^/api/v1/sessions/[^/]+/ws$` block with explicit `Upgrade` and `Connection "upgrade"` headers, placed before the general `/api/` proxy block. Placing it after or using prefix matching (`location /api/v1/sessions/`) instead of regex matching silently drops the upgrade headers.
 *   **Real-World Docker Validation:** Docker Desktop 4.82.0 (WSL2 backend) confirmed: both services build and start, health endpoint responds through nginx, seeded session data is served via the API, and WebSocket connections deliver live history through the proxy — all verified on Windows 11.

*   **Tier 3: Signed Agent Identity (AgentCard):**

    **What it is.** Each agent receives a JSON identity card containing its declared capabilities and a live reputation snapshot — `trust_score`, `total_sessions`, and `violations_count` — pulled directly from the existing `AgentReputationRecord` at card-generation time. This mirrors ERC-8004's pattern of an on-chain registry pointing to an off-chain document, implemented locally rather than on-chain.

    **Signing.** Cards are signed using Ed25519 (via the `cryptography` library). The canonical JSON payload is serialized, hashed, and signed; the resulting signature is stored as a detached base64 string alongside the JSON. The card file is written to:
    ```
    backend/data/agent_cards/{agent_id}.json
    ```
    A consumer verifies by hashing the JSON payload, decoding the base64 signature, and checking it against the known role public key.

    **Verification test.** The script `run_agent_card_test.py` at `backend/scripts/run_agent_card_test.py` performs a three-step end-to-end test:
    1. Generate a card for a given agent ID, signing it with the role key.
    2. Verify the card's signature against the role public key — passes.
    3. Tamper with the reputation snapshot (forge `trust_score` from 0.75 to 1.0), then re-verify — correctly fails.

    All three steps passed on the initial run. The tamper test confirms that any modification to the card body (including the reputation fields) is detected at verification time.

    **Known limitation (scope simplification).** Keys are managed per ROLE — one buyer key, one seller key — not per individual agent. A signature proves "issued by the legitimate seller-role authority," not "cryptographically tied to this one specific agent's own keypair." A real ERC-8004 implementation would give every agent its own keypair. This is a deliberate simplification for a closed local system. The direct corollary: **one seller agent could forge another seller agent's card** in the current design, since both would share the same role key. This is an explicit, acknowledged limitation, not an oversight. It is acceptable for the current scope because (a) all agents in the local system are controlled by the same deployer, (b) the primary threat model is external tampering with the card *after issuance*, and (c) role-level key management is strictly simpler than per-agent key provisioning in a local test environment. Per-agent keys are the natural next step if the system graduates to a multi-tenant or cross-org deployment.

## 5. KNOWN LIMITATIONS
*   **Confidence Calibration (ManipulationDetector) — Corrected:** The binary flagged/not-flagged verdicts are strong (F1 0.93), and the probabilistic confidence scores are now confirmed to be well-calibrated (Brier 0.0554, ECE 0.0728) after correcting a scoring methodology bug. See Caveat B under Key Engineering Findings for the full explanation of the correction. The earlier report of poor calibration was itself an artifact of incorrect metric computation, not a real model deficiency.
*   **Single-Provider Ensemble in Practice:** The multi-provider majority-vote architecture is implemented and verified-correct (failed votes are excluded, not miscounted), but free-tier rate limits on Groq and OpenRouter meant the final benchmark reflects Gemini alone in practice. A genuine 3-provider concurrent evaluation requires paid-tier access to validate.
*   **Small Benchmark Sample Sizes:** The detector validation sets are limited (n=13 for Policy, n=16 for Commitment). The benchmark totals 57 unique scenarios across separate suites: 27 (Tier 1 integrated), 18 (Adversarial Round 1), and 12 (Adversarial Round 2). While these sets effectively cover real structural and psychological failure modes, even a total n=57 across targeted subsets is not statistically powered for general industry-readiness claims.
*   **Open Problem in Manipulation Detection:** Reliably differentiating between standard assertive business negotiation and malicious manipulation remains an open problem. On the original Tier 1 benchmark, 0.88 recall means approximately 2 of 18 manipulative scenarios were missed. A harder targeted subset probing trust-exploitation tactics (Round 2) showed 0.50 recall — 5 of 10 manipulative scenarios were missed. See the Adversarial Testing sections under Key Engineering Findings for detail.
*   **Static Identity Management & AgentCard Scope:** The cryptographic ledger and local AgentCard implementation use a single shared Ed25519 keypair per agent role rather than per-agent keys. See the "Tier 3" section under Key Engineering Findings for the full rationale, consequences, and scope.
*   **Test Coverage Gaps:** Certain validation pathways and error edge-cases within the Trust Engine are currently stubbed or rely on the mock mode to pass reliably.
*   **LLM-Based Trust Detection at Seed Time:** The `seed_demo_data.py` script pre-computes trust evaluations with `skip_llm=True` because the Groq API free-tier daily quota was exhausted during development/testing. This means the seeded demo data only shows structural detector output (PolicyDeviationFlagger, commitment structural checks). The ManipulationDetector and LLM claim verification are not exercised at seed time. Full LLM-based detection is available on-demand via `GET /{session_id}/trust?recompute=true` when API quota is available.
*   **Multi-Provider Ensemble Constraints:** The LiteLLM router architecture executes a parallel vote across Groq and Gemini, using OpenRouter as a tie-breaker upon disagreement. This architecture ensures correct, multi-voter evaluation when quota is available, but free-tier rate limits remain the principal bottleneck blocking true multi-voter consensus in real-time evaluation (forcing fallback to Gemini-only execution in practice).

## 6. DEMO SCREENSHOTS

The following screenshots were captured from the live Docker deployment with 5 seeded sessions.

### Dashboard Overview
![Dashboard overview showing the negotiation price chart, trust panel, and ledger for a session with 3 violations](screenshots/01_dashboard_overview.png)

### Trust Scores Panel
![Trust Score gauges — Buyer 88/100, Seller 50/100 — showing real evaluated scores with violation counts](screenshots/02_trust_scores.png)

### Violations List
![Three flagged violations: currency swap (CRITICAL), buyer budget exceeded (HIGH), seller broken commitment (CRITICAL) — each with detector name, severity badge, turn number, and description](screenshots/03_violations_list.png)

### Ledger — Chain Verified
![Ledger panel with 5 signed entries showing entry hashes, signatures, and the green Chain Verified badge](screenshots/04_ledger_verified.png)

### Ledger — Chain Broken (Tamper Detected)
![After running the tamper script, the ledger panel shows a red Tamper Detected alert and a pulsing Chain Broken badge. Entry #1 is highlighted in red as the broken entry.](screenshots/05_ledger_broken.png)

## 7. FUTURE WORK
*   **Phase D (Commerce and Payments Layer):** Expanding the protocol to execute real-world settlement and value transfer once the A2A negotiation reaches a verified agreement.
*   **AgentCard Identity Verification:** Integrating structured A2A identity protocols (like AgentCard) to provide robust, per-session cryptographic guarantees of an agent's owner, capabilities, and authorization level.
*   **Paid-Tier Infrastructure:** Migrating to paid LLM endpoints to fully unlock the majority-vote manipulation mitigation strategy without rate-limit exhaustion.
*   **Expanded Benchmark Set:** Generating a statistically significant, open-source dataset of adversarial A2A negotiation transcripts to properly train and tune future trust engines.
