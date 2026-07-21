# Known Issues

## 1. Production Build Failure (Repo-Wide)
**Issue:** The production build (`npm run build`) currently fails across the entire frontend repository.
**Cause:** A version mismatch between `@tailwindcss/vite` and the version of Vite/Rolldown that Astro v6.4.8 pulls in. The error surfaces on `src/styles/global.css` with: `Missing field tsconfigPaths on BindingViteResolvePluginConfig.resolveOptions`.
**Status:** Confirmed pre-existing as of commit `bc4484a` (prior to the Section 3 UI/CI additions). Not caused by recent changes. 
**Impact:** Blocks any production deployment (including the public eval page). It does **not** affect the local dev server (`npm run dev`), which currently renders all pages correctly.
**Next Steps:** Needs a dependency version audit. Likely requires pinning `@tailwindcss/vite` to a compatible version or downgrading Astro's bundled Vite.
