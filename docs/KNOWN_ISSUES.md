# Known Issues

## 1. Production Build Failure (Repo-Wide)
**Issue:** The production build (`npm run build`) currently fails across the entire frontend repository.
**Cause:** A version mismatch between `@tailwindcss/vite` and the version of Vite/Rolldown that Astro v6.4.8 pulls in. The error surfaces on `src/styles/global.css` with: `Missing field tsconfigPaths on BindingViteResolvePluginConfig.resolveOptions`.
**Status:** Confirmed pre-existing as of commit `bc4484a` (prior to the Section 3 UI/CI additions). Not caused by recent changes. 
**Impact:** Blocks any production deployment (including the public eval page). It does **not** affect the local dev server (`npm run dev`), which currently renders all pages correctly.
**Next Steps:** Needs a dependency version audit. Likely requires pinning `@tailwindcss/vite` to a compatible version or downgrading Astro's bundled Vite.

## 2. ManipulationDetector Recall Regression (Urgency Context Dilution)
**Issue:** The ManipulationDetector's recall dropped to 0.67 on the 8-scenario holdout under the current self-consistency + 10-example few-shot architecture (down from 1.00 pre-expansion). This was observed across 3 pre-fix runs: two full runs at 0.67 recall, and one partial run cut short by API rate limits at 0.33 recall. Across all three, the only scenarios ever missed were the same two Urgency cases.
**Cause (Hypothesis):** The few-shot prompt was rebalanced to fix contamination, swapping out two compliance-based examples for two leak-free compliance/authority examples. In doing so, it left the prompt with no Urgency-category anchor examples, likely diluting the model's attention away from urgency tactics. The two false negatives driving the regression were both explicitly Urgency scenarios ("The Q4 Rush" and "The Exploding Offer").
**Status:** RESOLVED (2026-07-21). Fix applied and verified; see `docs/EVAL_RESULTS.md` for the confirmed 1.00/1.00 runs.
**Next Steps:** None. Issue is closed.
