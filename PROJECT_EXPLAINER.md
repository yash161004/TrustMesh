# TrustMesh — One-Page Explainer

*Written to directly address panel feedback: "couldn't explain the project well." Practice saying this out loud, in this order, without skipping to implementation detail.*

## The one-sentence version

**TrustMesh watches AI agents negotiate deals on your behalf, catches it if either one tries to manipulate the other, and produces tamper-proof proof of exactly what happened — so a business can trust an automated negotiation the way it would trust a human one.**

## The problem, in plain terms

Companies are starting to let AI agents negotiate real things for them — prices, delivery terms, contracts — instead of just answering questions. That's genuinely useful, but it creates a new problem: **if an AI agent makes a bad deal, or gets manipulated into one, how would anyone even know?** There's no black box, no audit trail, no way to prove after the fact what was actually said and agreed to.

## What TrustMesh actually does — three parts

1. **Two AI agents negotiate.** One represents a buyer, one represents a seller. They exchange offers back and forth like a real negotiation, in natural language.

2. **A trust engine watches every message as it happens**, using three separate checks:
   - Did either agent break an explicit rule? (policy check)
   - Did either agent contradict something it said earlier? (consistency check)
   - Does anything in the conversation *look* manipulative — pressure tactics, false urgency, misleading framing? (an AI judge trained to spot this)

3. **Everything gets signed and chained together cryptographically**, the same idea used in tamper-proof logs elsewhere: each message is signed with a unique digital key, and each entry links to the one before it, so if anyone tried to alter the record afterward, the chain would visibly break.

## Why this matters (the business case)

This isn't just an academic exercise — it's built with real B2B sectors in mind (through StellarMind AI's contacts in FMCG, dairy, logistics, and manufacturing). Any company using AI agents for procurement or vendor negotiation eventually needs to answer: *"prove to me this deal was made fairly."* TrustMesh is a working answer to that question.

## The one likely follow-up question, answered in advance

**"How is this different from just logging the conversation?"**
A normal log can be edited after the fact with nobody the wiser. TrustMesh's log is cryptographically chained — editing any past entry breaks every entry after it, so tampering is detectable, not just theoretically prevented.

## What to say if asked "what's novel here?"

Be honest and specific: **the novelty isn't any single piece — negotiation agents, manipulation detection, and tamper-proof logs all exist separately in current research. The contribution is combining all three into one working system, evaluated end-to-end, in a domain (AI-to-AI negotiation) where this combination doesn't currently exist together.** That is a real systems contribution and is a stronger, more defensible answer than claiming a new algorithm.

## What NOT to say

- Don't claim the manipulation detector is provably robust — it works at the message/behavior level, not by inspecting the model's internals, and that's a real, current research limitation (state it as a scoping decision, not hide it).
- Don't oversell "multi-model consensus" if that part isn't fully working — say plainly what's shipped vs. what's a documented future direction.
