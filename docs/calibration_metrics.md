# Calibration Metrics (Manipulation Detector)

> **Note:** ManipulationDetector ships as self-consistency sampling: 3 concurrent calls to the same model (Gemini) at temperature 0.15, majority-voted. Cross-provider majority-vote exists in the codebase but is opt-in, not default — free-tier rate limits across multiple providers can trigger cascading failures (including router crashes observed during benchmarking), making it unsuitable as a default. Therefore, these metrics strictly reflect single-judge calibration.

**Anchor Enabled during run:** True

**Brier Score:** [Pending re-validation post-architecture-fix, see /eval]*

**Expected Calibration Error (ECE - 10 bins):** [Pending re-validation post-architecture-fix, see /eval]*

*\*Note: Earlier prompt versions achieved strong binary verdicts and well-calibrated confidence scores (Brier 0.0554, ECE 0.0728) after correcting a scoring methodology bug. However, these figures were measured against a 27-scenario Tier 1 baseline using a retired prompt architecture. The current detector uses a 10-example, contamination-checked few-shot set combined with self-consistency sampling. Performance is being re-validated against the 8-scenario adversarial holdout; see the live results at /eval. The old 0.0554/0.0728 figures describe a retired prompt version and should not be read as current.*

### What do these mean?
- **Brier Score (0.0 to 1.0):** Measures the mean squared difference between predicted probability and the actual outcome. Lower is better. A score near 0 indicates perfect accuracy and confidence.
- **Expected Calibration Error (ECE):** Measures how well the model's stated confidence matches its actual correctness rate across different confidence levels. For example, if a model states it is 80% confident on a set of predictions, it should be correct 80% of the time. Lower ECE is better.
