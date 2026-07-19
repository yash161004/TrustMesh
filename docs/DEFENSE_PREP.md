# TrustMesh: Viva & Defense Preparation Guide

This document anticipates likely examiner questions regarding the TrustMesh architecture, methodology, and limitations. All answers are grounded strictly in the actual project repository, benchmarks, and known constraints.

---

## 1. ARCHITECTURE & DESIGN CHOICES

**"Why three separate detectors instead of one unified model?"**
A single prompt trying to do math on budget caps, track logical commitments over time, and evaluate subtle psychological pressure simply loses focus and hallucinates. By separating them, I let a deterministic rule engine handle the hard math (`PolicyDeviationFlagger`), while focusing the LLM entirely on semantic understanding (`CommitmentConsistencyChecker` and `ManipulationDetector`). This modularity also allows us to tune or swap models for specific failure modes without breaking the whole system.

**"Why rule-based for PolicyDeviationFlagger but LLM-based for the other two?"**
Policy deviation is fundamentally a math and constraint problem—did the offer exceed the strict $500 budget cap? A deterministic rule engine is 100% accurate, infinitely faster, and much cheaper for numerical bounds checking. In contrast, evaluating if an agent is employing a "Bait and Switch" or a "System Outage Threat" requires deep semantic context and psychological reasoning, which only an LLM can reliably provide.

**"Why SQLite instead of a real production database?"**
For this initial phase, my core research focus was proving the viability of the Trust Engine and the cryptographic ledger, not scaling concurrent reads and writes. SQLite allowed me to rapidly prototype the negotiation session state and hash-chaining logic without the overhead of maintaining a separate database container. Upgrading to PostgreSQL would be a straightforward migration once we need horizontal scaling or high concurrency.

---

## 2. METHODOLOGY & RIGOR

**"Your benchmark shows 1.00 precision/recall — isn't that suspiciously perfect?"**
The perfect 1.00 precision and recall only applies to the `PolicyDeviationFlagger`, which evaluates rigid numerical constraints like budget caps; since it uses deterministic math, a perfect score is exactly what we should expect. For the harder semantic tasks, we actually struggled: the `CommitmentConsistencyChecker` originally used a regex approach that scored a dismal 0.33 recall on our held-out data. That failure proved the benchmark was rigorous enough to catch weak methodologies, directly motivating our successful pivot to an LLM-based verification approach.

**"How do you know your benchmark isn't just testing itself / overfit to your own scenarios?"**
I mitigated overfitting by strictly separating our test scenarios into training and holdout sets. The strongest evidence against overfitting is our two-round Adversarial testing phase. After hitting 0.88 recall on the Tier 1 baseline (n=27 scenarios) with a 3-example prompt, we built a separate Adversarial Round 1 suite (n=18) targeting structural blind spots, where the detector maintained a strong 0.92 F1. When Round 1 revealed a weakness in detecting trust-exploitation, we developed a prompt fix independently (adding a 4th example), then validated it against a completely fresh Adversarial Round 2 holdout set (n=12). On that held-out set, recall improved from 0.20 to 0.50. We honestly report that adding this 4th example caused a regression on the original Tier 1 baseline down to 0.62 due to context dilution—proving we are tracking real generalization trade-offs rather than just cherry-picking the best numbers.

**"57 total scenarios is a small sample — how confident are you in these numbers?"**
I am confident that these 57 unique scenarios (27 Tier 1 integrated + 18 Adversarial Round 1 + 12 Adversarial Round 2) map correctly to the specific structural and psychological failure modes we designed them to catch, like the "Volume Discount Trick" or the "Rapport Exploit." However, I fully acknowledge that a total n=57 across targeted subsets is absolutely not statistically powered to make broad claims about general industry readiness. It is a proof-of-concept taxonomy meant to rigorously demonstrate the engine's mechanics and limits, and generating a statistically significant dataset is a primary goal for future work.

---

## 3. THE MANIPULATION DETECTOR

**"Why does ManipulationDetector show inconsistent results across runs?"**
Evaluating subtle psychological pressure is inherently subjective, and earlier single-call LLM runs exhibited severe binomial variance — swinging from overly aggressive (2 False Positives) to overly cautious (4 False Negatives) across identical holdout runs. The final stabilization was achieved after targeted fixes: (1) expanding the calibration anchor iteratively—first to a 3-example set which raised Tier 1 recall from 0.25 to 0.88, and later adding a 4th example (trust-exploitation) which raised recall on the Round 2 subset from 0.20 to 0.50 (though we honestly document this caused a context-dilution regression on Tier 1 back to 0.62); (2) fixing a silent bug where provider exceptions were counted as "not manipulative" votes rather than being excluded; and (3) migrating to LiteLLM for standardized provider routing and retry handling.

**"You proposed majority voting — does it work?"**
ManipulationDetector ships as documented single-model classification. Multi-provider majority-vote was attempted, invalidated by the cache-key bug (fixed), and true parallel voting is infeasible on free-tier rate limits — so it's a documented future direction, not a shipped feature.

**"Isn't an LLM judging another LLM's manipulation attempts circular / unreliable?"**
Yes, it is a valid and significant concern. An LLM acting as a judge shares the same latent biases and blind spots as the LLM generating the attacks, meaning it might systematically fail to recognize novel adversarial strategies it wasn't trained on. While I forced structural rigor by using a "reasoning-field-first" JSON schema to ground the judge's logic, a truly robust production system would likely need a smaller, specially fine-tuned classification model rather than relying entirely on a general-purpose LLM to police its peers.

---

## 4. SECURITY & CRYPTOGRAPHY

**"How do you know the tamper-evident ledger actually detects tampering?"**
Verified. 37/37 tests pass, including 10 dedicated tamper-detection tests (`test_ledger_tamper_detection.py`). These cover tampering via `message_json`, `entry_hash`, `signature`, and `prev_hash`; correct localization of the broken entry (including a middle-of-chain test where entry 3 of 5 was altered); and confirmed restore-to-valid behavior. Every tamper scenario is verified through both the internal `verify_chain()` function and the live `GET /{session_id}/ledger` API response (`chain_valid`, `broken_at`).

**"What happens if a private key is compromised?"**
Currently, a compromised private key would allow an attacker to forge messages masquerading as that specific agent role. Because we currently use a single shared keypair per role rather than dynamic, per-session identity keys, the blast radius of a compromised key would affect all active sessions for that agent type. Implementing ephemeral session keys or integrating a decentralized identity standard like AgentCard is required to fully mitigate this.

**"Why Ed25519 specifically?"**
I chose Ed25519 because it offers high security with very small signature sizes (64 bytes) and extremely fast signing and verification speeds. Given that our protocol requires digitally signing every single message in a real-time WebSocket stream, the performance efficiency of Ed25519 was critical to ensure the cryptographic layer didn't introduce latency into the negotiation pipeline.

---

## 5. SCOPE & LIMITATIONS

**"What would you do differently if you started over?"**
I would have skipped the attempt to use deterministic regex for claim extraction entirely and started immediately with an LLM structured-output approach. I also would have built the system around a paid-tier LLM from day one, because ManipulationDetector ships as documented single-model classification. Multi-provider majority-vote was attempted, invalidated by the cache-key bug (fixed), and true parallel voting is infeasible on free-tier rate limits — so it's a documented future direction, not a shipped feature.

**"What's NOT implemented yet, and why?"**
I have not yet implemented Phase D, the actual commerce and payments settlement layer, because my core research question was solving the trust and verification problem during the negotiation itself. Additionally, we are currently using static keypairs rather than a robust A2A identity protocol like AgentCard, simply to keep the scope strictly focused on the Trust Engine's core evaluation mechanics.

**"Is this production-ready?"**
Not yet. The PolicyDeviationFlagger and CommitmentConsistencyChecker both achieve 1.00 F1 and are structurally solid. The ManipulationDetector reaches 0.93 F1 on binary verdicts, and its confidence scores are well-calibrated (Brier 0.0554, ECE 0.0728) — an earlier report of poor calibration was due to a Brier/ECE scoring methodology bug (confident negative predictions were incorrectly scored as if they were confident positive predictions), which was found and fixed. The current multi-provider ensemble cannot be validated under real concurrency because free-tier rate limits prevent live 3-provider runs. The total benchmark sample size (n=57 unique scenarios across all suites) is too small for general industry-readiness claims, and the system lacks per-session cryptographic identity for real-world financial stakes.

---

## 6. BUSINESS/REAL-WORLD RELEVANCE

**"Who would actually use this?"**
This system is designed for enterprise procurement teams and B2B supply chain networks that are increasingly deploying autonomous agents to handle routine vendor negotiations. Companies want the efficiency of AI-to-AI dealmaking, but they need an impartial, verifiable audit trail to ensure their agents aren't being exploited by adversarial tactics or quietly violating compliance policies to close a deal.

**"How does this relate to real industry efforts (A2A, MCP, ERC-8004, IETF trust scoring)?"**
TrustMesh is a practical implementation of the exact challenges these standards are trying to solve. It uses the tooling concepts of the Model Context Protocol (MCP) for agent interaction, aligns with the IETF's emerging work on trust scoring by quantifying agent behavior, and anticipates the decentralized asset transfer goals of ERC-8004 by providing the necessary verifiable pre-settlement negotiation ledger. It bridges the gap between theoretical agent standards and a working compliance engine.
