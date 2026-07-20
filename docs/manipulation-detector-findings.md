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

## 2. Mitigation via Self-Consistency Sampling
To combat the variance seen in the single-call baseline, the detector implements **Self-Consistency Sampling** as its default path. For every evaluation, the detector fires 3 concurrent calls to Gemini Flash Lite at `temperature=0.15`, takes a majority-vote of the `flagged` verdict, and averages the confidence scores of the agreeing subset. 

*(Note: Multi-provider cross-voting exists in the codebase but is strictly opt-in. Free-tier rate limits across multiple providers can trigger cascading failures — including router crashes observed during benchmarking — making cross-provider voting unsuitable as a default).*

### Guarding Against Silent Degradation
A critical architectural lesson learned during benchmarking: multiplying API calls by 3x puts heavy pressure on free-tier rate limits (Gemini caps at 15 Requests Per Minute). During un-throttled batch testing, this burst traffic rapidly triggers `429 Too Many Requests` errors. 

To prevent these infrastructure failures from corrupting accuracy metrics with fake confidence scores, the detector implements a strict **hard guard**: if any of the 3 concurrent calls fail or time out, the system explicitly aborts the vote and returns `degraded=True`. 

**Current Production Gap:** While the benchmark scripts correctly intercept `degraded=True` and exclude those scenarios from accuracy scoring, the live `TrustEngine` path currently treats a degraded result as a simple `flagged: False`. This means if a live negotiation session hits a rate limit, the message silently passes through as "unflagged" without blocking, retrying, or surfacing the degraded state to the UI. This is a known gap that needs to be addressed in future UI/engine updates.

### Re-Validation Results
After implementing a 15-second throttle between scenarios to sustain a safe ~12 RPM, we ran 5 uncorrupted benchmark runs against the 8-scenario holdout (40 total scenarios, 120 independent LLM calls). 

**The results were identical across all 5 runs:**
* **Precision**: 1.00 
* **Recall**: 1.00
* **F1 Score**: 1.00
* **Disagreement Rate**: 0.00
* **Degraded**: 0 (all 120 calls successfully completed)

**Conclusion:** 
Self-consistency sampling is shipped, functional, and successfully eliminated the variance gap seen in the baseline. However, the most notable finding is the `0.00` disagreement rate across 120 independent, un-cached calls (verified via trace logs showing varying payload hashes and token counts). At `temperature=0.15`, Gemini proved highly deterministic. 

*(Caveat: This zero-disagreement stability was measured strictly on the same 8-scenario holdout used throughout validation; it demonstrates that Gemini is highly consistent on these specific edge cases, but does not necessarily guarantee the same determinism generalizing to novel, untested scenarios).*
