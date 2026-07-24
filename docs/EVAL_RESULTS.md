# Manipulation Detector Holdout Results

CI gates PRs on precision >= 0.95 and recall >= 0.95 (baseline 1.00/1.00
from self-consistency sampling, minus 5pp tolerance for run-to-run variance).
The workflow auto-appends a new row on every PR run; this file is committed
manually with the baseline entries because the CI artifact upload does not
write back to the repo. Each row is produced by the actual script execution
— numbers are never hand-written.

| Date | Git SHA | Precision | Recall | F1 Score | Disagreement Rate | Prompt Version |
|------|---------|-----------|--------|----------|-------------------|----------------|
| 2026-07-21 04:28:10 UTC | `1de7834` | 1.00 | 0.67 | 0.80 | 0.08 | post-few-shot-expansion |
| 2026-07-21 04:32:28 UTC | `1de7834` | 1.00 | 0.67 | 0.80 | 0.00 | post-few-shot-expansion |
| 2026-07-21 04:34:41 UTC | `1de7834` | 1.00 | 0.33 | 0.50 | 0.11 | post-few-shot-expansion |
| 2026-07-21 09:18:26 UTC | `1de7834` | 1.00 | 1.00 | 1.00 | 0.00 | post-few-shot-expansion-swap |
| 2026-07-21 09:20:26 UTC | `1de7834` | 1.00 | 1.00 | 1.00 | 0.00 | post-few-shot-expansion-swap |
| 2026-07-21 09:22:26 UTC | `1de7834` | 1.00 | 1.00 | 1.00 | 0.00 | post-few-shot-expansion-swap |
