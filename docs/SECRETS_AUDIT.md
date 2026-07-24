# Secrets Audit — Git History Scan

**Date**: 2026-07-24
**Branch**: `claude/project-status-remaining-i5aadr`
**Scope**: Full git history (all branches, all commits)

## Methodology

All commands ran against `git log --all -p` with targeted regex patterns:

| Pattern | Target | Hits |
|---|---|---|
| `AIza[0-9A-Za-z_-]{35}` | Google API keys | 0 |
| `sk-[A-Za-z0-9]{20,}` | OpenAI keys | 0 |
| `nvapi-\|gsk_\|sk-or-v1-\|whsec_` | Provider keys (NVIDIA, Groq, etc.) | 0 |
| `ghp_\|gho_\|ghu_\|ghs_\|github_pat` | GitHub tokens | 0 |
| `postgres(ql)?://[^:]+:[^@]+@` | Embedded DB URLs | Found (see below) |
| `Bearer [A-Za-z0-9_\.-]{20,}` | Bearer tokens | 0 |
| `-----BEGIN (RSA \|EC )?PRIVATE KEY-----` | Private keys | 0 |
| `JWT_SECRET\|SECRET_KEY\|SIGNING_KEY\|ENCRYPTION_KEY` | Key references | Found (all code-level, no values) |
| `sha256~` | GitLab CI tokens | 0 |
| `sk_test_` | Clerk test keys | Found (see below) |

## Findings

### 1. Clerk Test Secret Key — `.env` (LOW risk, already rotated)

**Commit introduced**: `02ec05d5` (2026-07-18, "Phase 4 frontend work")
**Commit removed**: `7f581dbe` (2026-07-18, replaced with `sk_test_REPLACE_ME`)
**Value**: `sk_test_M6A...APo` (first/last 6 chars shown)

A Clerk test-mode secret key was committed inside `.env`. The file was later amended to replace the value with `sk_test_REPLACE_ME`, but the original key remains reachable in git history.

**Impact**: Clerk `sk_test_` keys are sandboxed to test instances and carry no production risk. However, anyone with repo access can retrieve the value.

**Recommendation**: Rotate the Clerk test key in the Clerk dashboard (test-mode keys can be regenerated). Ensure `.env` is in `.gitignore` (already is).

### 2. Clerk Test Secret Key — Inlined in frontend build artifact (LOW risk, already rotated)

**Commit introduced**: `aa9a2b4e` (2026-07-22, "Update codebase")
**Value**: `sk_test_lQ0u...55Se` (first/last 6 chars shown)

A different Clerk test-mode key was inlined at build time into a Vite/JS artifact and committed to the repo. The key appears in a `__vite_import_meta_env__` object literal.

**Impact**: Same as above — test-mode key, no production impact.

**Recommendation**: Rotate this Clerk test key as well. Avoid committing frontend build artifacts that contain inlined environment variables, or strip secrets during the build step.

### 3. Placeholder PostgreSQL Credentials (NO risk)

**Commits**: Various (scripts since deleted)
**Value**: `postgresql+asyncpg://myuser:mypassword@localhost:5432/trustmesh_staging`

Deleted scripts (`query_db.py`, `migrate_sqlite_to_postgres.py`, etc.) contained a fallback default URL using `myuser:mypassword@localhost`. These are clearly placeholder values — the username literally reads `myuser` and the host is `localhost`. No real credential was exposed.

**Recommendation**: None needed. These files have been deleted.

### 4. `.gitignore` Compliance

The `.env` file is listed in `.gitignore` and is **not** present in the current tree. The only `.env` content found in history was the Clerk test key discussed above.

## Summary

| Severity | Count | Action needed |
|---|---|---|
| Critical (production key) | 0 | — |
| High (real credential) | 0 | — |
| Low (test key, git history) | 2 | Rotate both Clerk test keys |
| Informational (placeholder) | 1 | None |

## Recommendations

1. **Rotate both Clerk `sk_test_` keys** found in git history via the Clerk dashboard. Even though they are test-mode keys, best practice is to rotate any key that has ever been exposed.
2. **Add pre-commit hook** (e.g., `pre-commit` with `detect-secrets` or `truffleHog`) to prevent future credential leaks.
3. **Verify frontend build pipeline** does not inline secrets into committed artifacts. Use Vite's `import.meta.env.VITE_*` convention (public prefix) for frontend-visible variables; never inline `CLERK_SECRET_KEY` into client bundles.
