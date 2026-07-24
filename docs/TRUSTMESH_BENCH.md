# TrustMesh-Bench

**TrustMesh-Bench is the named evaluation artifact for the TrustMesh trust engine.**
It turns "does the detector actually work?" from an argument into a number that
regenerates itself, with git-SHA + timestamp provenance and a CI gate.

It is not a new detector or a new dataset — it is a single front door over the
suite of evaluation runners that already exist, plus the discipline around how
their results are recorded.

## Run it

One entrypoint (from `backend/`):

```bash
python scripts/run_trustmesh_bench.py all                 # full suite
python scripts/run_trustmesh_bench.py holdout --limit 8   # one benchmark
python scripts/run_trustmesh_bench.py all --dry-run       # show commands, run nothing
```

The runners call a live LLM and abort cleanly if no real API key is configured
(mock mode). `--dry-run` needs no key — it prints the resolved commands and exits.

## What it measures

| Benchmark | Runner | Measures |
|---|---|---|
| `holdout` | `run_manipulation_holdout.py` | ManipulationDetector precision / recall / F1 on a held-out adversarial set. **CI-gated.** |
| `negotiation` | `run_benchmark.py` | Primary negotiation benchmark across the policy and commitment detectors. |
| `adversarial` | `run_adversarial_benchmark.py` | Robustness to adversarial / prompt-injection scenarios. |
| `calibration` | `compute_calibration_metrics.py` | Brier score + Expected Calibration Error (how well confidence matches reality). |

## Provenance — results are never hand-written

`run_manipulation_holdout.py` appends a row to [`EVAL_RESULTS.md`](EVAL_RESULTS.md)
on every run, stamped with a UTC timestamp and the short git SHA
(`git rev-parse HEAD`). Each number is the output of an actual run against the
holdout set — the file is committed with those rows, not edited by hand.

## CI gate

`.github/workflows/manipulation_eval.yml` runs the holdout on CI with:

```
--fail-below-precision 0.95 --fail-below-recall 0.95
```

so a regression that drops precision or recall below 0.95 fails the build. When
`GEMINI_API_KEY` is not configured, the workflow skips the holdout gracefully and
says so in the log (documented behaviour — it does not silently pass).

## Honest caveats (state these in a defense)

- **Small holdout.** The holdout set is modest; a perfect 1.00/1.00 on a small
  set is evidence, not proof of generalization. The 5-percentage-point CI
  tolerance below the 1.00 baseline exists precisely because run-to-run variance
  is real.
- **LLM-judge calibration instability is a known, studied phenomenon.** Prior
  runs on the *same* holdout have varied (1.00/1.00 → 0.75/1.00 → 1.00/0.33).
  That is why TrustMesh reports confidence intervals and disagreement rate rather
  than a single flagged/clear verdict — a direct, literature-grounded response to
  the limitation, not a flaw hidden behind a headline number.

See [`EVAL_RESULTS.md`](EVAL_RESULTS.md) for the current committed numbers.
