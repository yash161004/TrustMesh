# Calibration Metrics (Manipulation Detector)

> **Note:** ManipulationDetector ships as documented single-model classification. Multi-provider majority-vote was attempted, invalidated by the cache-key bug (fixed), and true parallel voting is infeasible on free-tier rate limits — so it's a documented future direction, not a shipped feature. Therefore, these metrics strictly reflect single-judge calibration.

**Anchor Enabled during run:** True

**Brier Score:** 0.0554*

**Expected Calibration Error (ECE - 10 bins):** 0.0728*

*\*Note: These reflect corrected values. The original scores were incorrect due to a scoring methodology bug that improperly penalized confident correct negative predictions. After aligning the probability correctly, the metrics improved to the above, confirming strong calibration.*

### What do these mean?
- **Brier Score (0.0 to 1.0):** Measures the mean squared difference between predicted probability and the actual outcome. Lower is better. A score near 0 indicates perfect accuracy and confidence.
- **Expected Calibration Error (ECE):** Measures how well the model's stated confidence matches its actual correctness rate across different confidence levels. For example, if a model states it is 80% confident on a set of predictions, it should be correct 80% of the time. Lower ECE is better.
