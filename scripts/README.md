# TrustMesh — Scripts

This directory intentionally contains no one-off debug scripts.

The following ad-hoc scripts were removed on 2026-07-20 as part of a repo cleanup (Section 1):

- `backend/run_auth_test.py`, `run_auth_test_2.py`, `run_auth_test_3.py` — auth smoke checks that printed status codes instead of asserting. Replaced by `backend/tests/test_auth_smoke.py`, a proper pytest test with real assertions (401 for unauthenticated/invalid-token requests, 200 when auth is disabled).
- `backend/query_db.py`, `backend/query_event.py`, `backend/query_latest.py` — one-shot DB inspection scripts; patterns already covered in `backend/tests/`.
- `backend/test_standard_uvicorn.py` — trivial uvicorn boot test; no reusable logic.

QA output files (`pytest_full_out.txt`, `qa_node_error.txt`, `qa_lighthouse.json`, `qa_lighthouse_prod.json`, `web-astro/astro_log.txt`) moved to `docs/qa-history/` for archival reference. Matching patterns are gitignored to prevent re-commit.

**Policy:** Auth checks live in `backend/tests/test_auth_smoke.py`. DB inspection should use the existing `backend/tests/` patterns rather than ad-hoc scripts. Do not recreate the one-off debug-script pattern — if it's a genuine test, put it under `backend/tests/` with pytest assertions; if it's a one-time inspection, run it inline.
