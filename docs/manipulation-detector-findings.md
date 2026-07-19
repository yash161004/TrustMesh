# Manipulation Detector Variance Findings

## 1. Initial Single-Call Variance
During the Phase B validation, we ran the 8-scenario `manipulation_holdout.json` dataset three separate times against the Groq LLM (with caching disabled) to measure variance. 

The results exposed extreme instability in the model's judgements for manipulation detection:

* **Run 1**: The LLM skewed overly aggressive, flagging 2 of our Category 0 benign scenarios ("The Legitimate Hard Deadline" and "The Industry Practice Reference") as manipulation. 
  * *Result: 0.75 Precision (2 False Positives), 1.00 Recall*
* **Run 2**: The LLM scored perfectly, identifying all attacks and passing all benign controls, though one call failed JSON parsing entirely and triggered our fallback.
  * *Result: 1.00 Precision (0 FPs), 1.00 Recall*
* **Run 3**: The LLM skewed overly cautious and missed all four of the most difficult attacks (The Q4 Rush, The Exploding Offer, The Legal Audit, and The Green Energy Mandate).
  * *Result: 1.00 Precision (0 FPs), 0.33 Recall (4 False Negatives)*

**Conclusion on Single-Call**: The LLM struggles to consistently differentiate between standard, slightly aggressive business negotiation tactics and actual adversarial manipulation. It is highly sensitive to slight temperature variations in inference.

## 2. Majority-Vote Mitigation Attempt
ManipulationDetector ships as documented single-model classification. Multi-provider majority-vote was attempted, invalidated by the cache-key bug (fixed), and true parallel voting is infeasible on free-tier rate limits — so it's a documented future direction, not a shipped feature.

## 3. Re-Validation Results & Viability Conclusion

When attempting to re-validate the holdout dataset (8 scenarios) with the majority-vote system (3 runs of 3 inner calls per scenario = 72 API calls), we encountered a critical architectural limitation: **Provider Rate Limits**.

Groq's free tier imposes strict rate limits, specifically a 7,000 Tokens Per Minute (TPM) limit for models like `llama3-70b-8192`. 
* A single negotiation history evaluation consumes ~500-800 tokens. 
* A 3-vote evaluation consumes ~1,500-2,400 tokens per message turn.
* Evaluating just a few scenarios back-to-back instantly exhausts the 7,000 TPM limit, resulting in cascading `429 Too Many Requests` errors.

**Honest Conclusion**: 
ManipulationDetector ships as documented single-model classification. Multi-provider majority-vote was attempted, invalidated by the cache-key bug (fixed), and true parallel voting is infeasible on free-tier rate limits — so it's a documented future direction, not a shipped feature.

To isolate whether burst-traffic was the culprit, we ran a final, highly conservative test: a single pass of the 8 scenarios with history aggressively trimmed to 5 turns, paced with a generous 15 seconds between every single internal vote, and 20 seconds between scenarios. 

Even under this extremely slow pacing (which took over 12 minutes of wall-clock time just attempting to execute), the script encountered endless 15-second exponential backoff loops (`429 Too Many Requests`). This indicates that we haven't just hit a transient "Requests Per Minute" (RPM) limit—we have entirely exhausted Groq's daily free-tier quota (Tokens Per Day) simply by running our validation benchmarks a few times.

This is a valid and critical production finding: a 3-vote system multiplies the API token overhead so aggressively that it is fundamentally incompatible with free-tier APIs, regardless of realistic pacing or prompt minimization. 

If we intend to use majority-voting in production, we MUST:
1. Upgrade to a paid tier with substantially higher TPM/TPD limits (e.g., OpenAI or Groq paid tiers).
2. Alternatively, accept the single-call variance and attempt to solve the stability issue entirely through prompt engineering and model tuning.
