# Calibration Metrics (Manipulation Detector)

> **Note:** ManipulationDetector ships as self-consistency sampling: 3 concurrent calls to the same model (Gemini) at temperature 0.15, majority-voted. Cross-provider majority-vote exists in the codebase but is opt-in, not default — free-tier rate limits across multiple providers can trigger cascading failures (including router crashes observed during benchmarking), making it unsuitable as a default. Therefore, these metrics strictly reflect single-judge calibration.

**Anchor Enabled during run:** True

**Brier Score:** 0.2161/0.2381 (Regression)*

**Expected Calibration Error (ECE - 10 bins):** 0.2161/0.2381 (Regression)*

*\**Note: Current architecture (self-consistency sampling + 10-example contamination-checked few-shot prompt) shows a recall regression to 0.67 (2 consistent runs, identical false negatives both times: 'The Q4 Rush' and 'The Exploding Offer', both Urgency-tactic scenarios) versus the pre-expansion self-consistency baseline of 1.00/1.00 (5 runs). Working hypothesis: the 10-example prompt, rebalanced during a contamination fix, no longer includes an Urgency-category anchor example, which may be diluting the model's attention away from that tactic category. This is under active investigation, not yet confirmed. The CI gate (recall < 0.80) correctly caught this regression before it reached production — see docs/EVAL_RESULTS.md for the full run history.*

### What do these mean?
- **Brier Score (0.0 to 1.0):** Measures the mean squared difference between predicted probability and the actual outcome. Lower is better. A score near 0 indicates perfect accuracy and confidence.
- **Expected Calibration Error (ECE):** Measures how well the model's stated confidence matches its actual correctness rate across different confidence levels. For example, if a model states it is 80% confident on a set of predictions, it should be correct 80% of the time. Lower ECE is better.
