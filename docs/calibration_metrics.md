# Calibration Metrics (Manipulation Detector)

> **Note:** ManipulationDetector ships as self-consistency sampling: 3 concurrent calls to the same model (Gemini) at temperature 0.15, majority-voted. Cross-provider majority-vote exists in the codebase but is opt-in, not default — free-tier rate limits across multiple providers can trigger cascading failures (including router crashes observed during benchmarking), making it unsuitable as a default. Therefore, these metrics strictly reflect single-judge calibration.

**Anchor Enabled during run:** True

**Brier Score:** 0.2161/0.2381 (Regression)*

**Expected Calibration Error (ECE - 10 bins):** 0.2161/0.2381 (Regression)*

*\**Note: The recall regression this note originally described (0.67 recall on the 10-example few-shot prompt, missing the two Urgency scenarios 'The Q4 Rush' and 'The Exploding Offer') was resolved on 2026-07-21 by swapping the redundant 'Protective Advisor' example for a single-turn Urgency anchor ('The Gradual Squeeze', adversarial-6). Recall is now 1.00/1.00/1.00 across three consecutive holdout runs (see docs/EVAL_RESULTS.md, prompt version `post-few-shot-expansion-swap`). **Caveat:** the Brier/ECE figures above (0.2161 / 0.2381) were computed on the regression-era prompt and have NOT yet been recomputed on the resolved swap prompt — regenerate them with `scripts/compute_calibration_metrics.py` before citing them as current. The CI gate (recall < 0.80) correctly caught the regression before it reached production.*

### What do these mean?
- **Brier Score (0.0 to 1.0):** Measures the mean squared difference between predicted probability and the actual outcome. Lower is better. A score near 0 indicates perfect accuracy and confidence.
- **Expected Calibration Error (ECE):** Measures how well the model's stated confidence matches its actual correctness rate across different confidence levels. For example, if a model states it is 80% confident on a set of predictions, it should be correct 80% of the time. Lower ECE is better.
