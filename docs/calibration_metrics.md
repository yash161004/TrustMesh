# Calibration Metrics (Manipulation Detector)

> **Note:** These metrics were computed on a single-call path (`majority_vote=False`) to measure the underlying judge's calibration in isolation, separate from the 2-vote live ensemble behavior. This ensures we evaluate the raw probabilistic outputs directly.

**Anchor Enabled during run:** True

**Brier Score:** 0.5511

**Expected Calibration Error (ECE - 10 bins):** 0.5578

### What do these mean?
- **Brier Score (0.0 to 1.0):** Measures the mean squared difference between predicted probability and the actual outcome. Lower is better. A score near 0 indicates perfect accuracy and confidence.
- **Expected Calibration Error (ECE):** Measures how well the model's stated confidence matches its actual correctness rate across different confidence levels. For example, if a model states it is 80% confident on a set of predictions, it should be correct 80% of the time. Lower ECE is better.
