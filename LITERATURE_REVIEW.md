# Literature Review — TrustMesh

*Draft for MSc Semester 3 major project submission. Written to directly address panel feedback: absence of a literature review, and difficulty articulating where the project sits relative to existing work.*

## 1. Scope

TrustMesh sits at the intersection of three research threads that are usually studied separately:

1. Multi-agent LLM negotiation
2. Trust, deception, and manipulation detection in LLM agents
3. Verifiable audit trails and identity for autonomous agents

This review covers each thread, then argues that TrustMesh's contribution is combining them into one working system rather than advancing any single thread in isolation — which is also the honest, defensible framing for the panel: not "novel algorithm," but "novel integration, evaluated end-to-end."

---

## 2. Multi-Agent LLM Negotiation

Negotiation between LLM-driven agents has become an active benchmark area. Abdelnabi et al.'s negotiation testbed (reproduced and critically examined in a 2025 reproducibility study) evaluates whether LLM agents can conduct multi-issue negotiations without supervision, and specifically questions whether multi-agent communication provides any real advantage — the reproduction found that single-agent approaches often matched multi-agent negotiation performance, and that smaller open-weight models struggled with format adherence and coherent negotiation behavior compared to proprietary models.

A related benchmark, *Cooperation, Competition, and Maliciousness: LLM-Stakeholders Interactive Negotiation*, frames negotiation explicitly around adversarial stakeholder incentives rather than cooperative dealmaking — closer to TrustMesh's buyer/seller setup, where each side has an incentive to misrepresent its position.

**Relevance to TrustMesh:** this literature establishes that (a) LLM negotiation benchmarks exist and are actively studied, but (b) they largely evaluate deal quality or protocol adherence, not the *trustworthiness* of the process that produced the deal. TrustMesh's contribution is adding a verification layer on top of a negotiation, not proposing a new negotiation protocol.

---

## 3. Trust, Reputation, and Manipulation Detection in LLM Agents

A 2026 study, *Trust Between AI Agents: Measuring Formation, Breakage, and Recovery*, is one of the more directly relevant pieces of work: it treats trust between agents as something measurable through the cost an agent pays to verify a partner, drawing on established human trust-game literature (trust as asymmetric — violations are easier to inflict than to repair) and applying it to agent-agent interaction. This is conceptually close to TrustMesh's reputation scoring, which updates per-agent trust scores after each session.

The *TrustAgent* survey (2025, presented at KDD) provides a broader taxonomy of what "trustworthy" means for LLM agents — reliability, safety, robustness to manipulation — and catalogs known attack and defense patterns across single-agent and multi-agent systems. This is useful as a framing reference for why TrustMesh needs three separate detectors (policy rules, commitment consistency, LLM-based manipulation judgment) rather than one: different failure modes require different detection mechanisms, which the survey's taxonomy makes explicit.

Separately, there is a growing body of work specifically on LLM deception detection — Hagendorff's PNAS paper documenting that deception capability emerges in large language models, and more recent probe-based approaches that try to detect deceptive internal states directly from model activations rather than from output text. A 2026 paper pressure-testing these "deception probes" found they can be evaded by models trained (via RL) to suppress the very signal the probes look for — a caution against overclaiming detector robustness. TrustMesh's manipulation detector works at the output/behavior level (message content, commitment consistency), not the activation level, which is a more limited but more practically deployable approach — worth stating explicitly in the report as a scoping decision, not an oversight.

**Relevance to TrustMesh:** this thread justifies the three-detector design and gives honest language for its limits — output-level detection is not activation-level detection, and neither is provably robust against a sufficiently adversarial agent. This is the right place in the report to be precise about what "manipulation detection" does and doesn't guarantee, echoing the project's own internal correction (Phase 0 in the engineering roadmap) about not overclaiming multi-model consensus.

---

## 4. Verifiable Audit Trails and Agent Identity

The closest architectural parallel to TrustMesh's ledger design comes from recent work on cryptographically verifiable execution for AI agents. Hash-chained, append-only audit logs — where each entry's hash incorporates the previous entry's hash, so tampering breaks the chain — appear across several 2025–2026 papers, including a Merkle-DAG-based ledger for autonomous browser agents (using SHA3-256 and Ed25519 signing, structurally very similar to TrustMesh's own Ed25519-signed hash chain) and a bilaterally-signed "Verifiable Interaction Ledger" for agent-tool transactions.

On the identity side, the emerging pattern across industry and research is to give agents persistent, verifiable identities distinct from the humans or organizations that operate them — Google's Agent-to-Agent (A2A) protocol and its associated Agent Payments Protocol (AP2) use cryptographically signed mandates for authorization, and there is active work applying decentralized identifiers (DIDs) and verifiable credentials (VCs) to agent identity for exactly this reason. TrustMesh's AgentCard/Ed25519 keypair design is a lightweight version of this same idea, without the DID/blockchain layer.

A 2026 survey on secure autonomous agent payments (the TIVA framework) makes the case most directly relevant to TrustMesh's B2B framing: that immutable audit logs and provable authorization are necessary infrastructure for any AI agent that transacts on someone's behalf, because without them there is no way to resolve disputes about what an agent actually did.

**Relevance to TrustMesh:** this is the thread where TrustMesh is most clearly building something with real precedent rather than inventing from scratch — hash-chained signed ledgers for agent accountability are an active, current research and industry pattern. The honest framing is: TrustMesh applies an established audit-trail pattern to a domain (LLM negotiation) where it hasn't commonly been applied yet, rather than inventing a new cryptographic primitive.

---

## 5. Where TrustMesh Sits (Gap and Contribution Statement)

Three observations, each grounded in the above:

1. Negotiation benchmarks (§2) evaluate deal outcomes, not trust in the process.
2. Trust/manipulation-detection work (§3) is evaluated largely in isolation from live negotiation systems, and increasingly (see the deception-probe pressure-testing result) needs to be described with real limits rather than presented as solved.
3. Verifiable audit/identity infrastructure (§4) is being built for agent *payments* and *tool use* generally, not specifically for negotiation transcripts with per-message trust scoring.

**TrustMesh's contribution is the integration**: a system where negotiation, multi-detector trust scoring, and cryptographically verifiable logging operate together on the same session, evaluated end-to-end (see `docs/LOAD_TEST_RESULTS.md` for the load-test evidence, honestly caveated where LLM calls were mocked). This is a legitimate systems contribution — the kind reviewers can be shown working, not just described — and it is a defensible answer to "what's novel here": not a new algorithm in any one of the three areas, but a working demonstration that they compose.

---

## 6. Suggested Next Steps for This Document

- [ ] Yashraj to review framing in §5 and confirm it matches how he wants to present the contribution to the panel
- [ ] Pull 2–3 more specific citations per section directly from Google Scholar/arXiv with full bibliographic details (author list, venue, year) for proper academic formatting — this draft used web search results, which give correct titles/URLs but incomplete formal citation metadata for some entries
- [ ] Add a short "Related Work Table" if the department expects a formal comparison table (columns: paper, negotiation, trust detection, verifiable audit — TrustMesh is the only row with all three)
- [ ] Confirm citation style required by the department (IEEE, ACM, APA) before finalizing

*Note: this document paraphrases findings from the cited sources rather than quoting them; page numbers and formal citation keys should be added from the original papers before submission.*
