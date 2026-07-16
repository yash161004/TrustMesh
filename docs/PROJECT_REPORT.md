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
    | **PolicyDeviationFlagger** | Identifies violations of budget caps/floor constraints. | n=13 scenarios | 1.00 Precision, 1.00 Recall |
    | **CommitmentConsistencyChecker** | Tracks promises to catch bait-and-switch tactics. | n=16 scenarios | LLM-based (legacy regex: 0.33 recall) |
    | **ManipulationDetector** | Evaluates adversarial psychological pressure tactics. | n=18 total (n=8 holdout) | Variable (Majority-vote required) |
*   **Cryptographic Ledger:** Ed25519 signing and SHA-256 hash chaining applied to every session message.
*   **WebSocket Dashboard:** Real-time UI streaming the verified events.
 *   **Docker Deployment:** Containerized services encompassing the backend API and frontend dashboard, validated end-to-end with `docker compose up --build`. WebSocket proxying through nginx confirmed working.

## 4. KEY ENGINEERING FINDINGS
This section details the critical technical discoveries made during the development of the Trust Engine:

*   **The Regex-to-LLM Pivot on the CommitmentConsistencyChecker:** Initial attempts to extract structured claims from negotiation text using deterministic regex heuristics failed to generalize, achieving a poor 0.33 recall on the holdout set. This failure motivated a pivot to LLM-based semantic verification. However, we discovered that naive LLM verification was prone to hallucinations. We successfully stabilized this by enforcing a "reasoning-field-first" JSON schema. Forcing the LLM to explicitly output its reasoning—identifying the claimed number, locating the actual historical number, and computing the delta—before outputting the final boolean judgment was strictly required for it to work correctly.
*   **ManipulationDetector Variance & Rate Limits:** Evaluating the n=8 holdout set for psychological manipulation exposed extreme instability in single-call LLM judgments. Across three identical validation runs, we observed severe variance:
    *   **Run 1:** Overly aggressive (0.75 Precision with 2 False Positives, 1.00 Recall).
    *   **Run 2:** Perfect scoring (1.00 Precision, 1.00 Recall).
    *   **Run 3:** Overly cautious (1.00 Precision, 0.33 Recall, missing 4 critical False Negatives).
    To mitigate this, we implemented a 3-vote majority consensus system. However, this revealed a hard infrastructure constraint: running 3 evaluations per message instantly exhausted the 7,000 Tokens Per Minute (TPM) limit on our free-tier LLM provider. This proved that majority voting for real-time stream evaluation is fundamentally unviable without a paid-tier architecture.
 *   **Deployment Hazards:** We identified and fixed a critical Docker volume-mount bug during containerization. A misconfigured mount path in the compose file would have silently erased the container's application directory by overwriting it with an empty host mapping, leading to difficult-to-trace deployment failures. *(Note: This issue was found and resolved during Docker deployment testing, not during initial development.)*
 *   **WebSocket Proxy Subtlety:** The nginx reverse proxy requires a dedicated `location ~ ^/api/v1/sessions/[^/]+/ws$` block with explicit `Upgrade` and `Connection "upgrade"` headers, placed before the general `/api/` proxy block. Placing it after or using prefix matching (`location /api/v1/sessions/`) instead of regex matching silently drops the upgrade headers.
 *   **Real-World Docker Validation:** Docker Desktop 4.82.0 (WSL2 backend) confirmed: both services build and start, health endpoint responds through nginx, seeded session data is served via the API, and WebSocket connections deliver live history through the proxy — all verified on Windows 11.

## 5. KNOWN LIMITATIONS
*   **Small Benchmark Sample Sizes:** The detector validation sets are extremely limited (n=13 to 17 per detector, n=8 for the holdout set). While these represent real structural tests, they are not statistically powered.
*   **Open Problem in Manipulation Detection:** Reliably differentiating between standard assertive business negotiation and malicious manipulation remains an open problem due to the single-call variance of current models.
*   **Static Identity Management:** The cryptographic ledger currently utilizes a single shared Ed25519 keypair per agent role, rather than provisioning dynamic, per-session identity keys.
*   **Test Coverage Gaps:** Certain validation pathways and error edge-cases within the Trust Engine are currently stubbed or rely on the mock mode to pass reliably.
*   **LLM-Based Trust Detection at Seed Time:** The `seed_demo_data.py` script pre-computes trust evaluations with `skip_llm=True` because the Groq API free-tier daily quota was exhausted during development/testing. This means the seeded demo data only shows structural detector output (PolicyDeviationFlagger, commitment structural checks). The ManipulationDetector and LLM claim verification are not exercised at seed time. Full LLM-based detection is available on-demand via `GET /{session_id}/trust?recompute=true` when API quota is available.
*   **Multi-Provider Fallback:** To combat the strict free-tier rate limits encountered during evaluation and testing, an automatic LLM failover chain (Groq -> Gemini -> Mock) was introduced. This ensures that the system gracefully handles quota exhaustion, though it highlights the ongoing challenge of relying on free-tier APIs for complex, multi-call evaluation features like majority voting.

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
