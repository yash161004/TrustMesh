"""
Public, read-only endpoint exposing the latest manipulation-detector
holdout results from docs/EVAL_RESULTS.md.

Parses the markdown table format established by Task K:

    | Date | Git SHA | Precision | Recall | F1 Score | Disagreement Rate | Prompt Version |
    |------|---------|-----------|--------|----------|-------------------|----------------|
    | ... | `abc1234` | 1.00 | 0.95 | 0.97 | 0.02 | prompt-version |

Format assumptions (update this comment if EVAL_RESULTS.md changes):
- The table is the first pipe-delimited block after the preamble.
- Column order is fixed: Date, Git SHA, Precision, Recall, F1, Disagreement, Prompt.
- Numeric columns use '.' as decimal separator (locale-independent).
- Git SHA is optionally wrapped in backticks.
- No cell contains escaped pipes.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

router = APIRouter()

_EVAL_RESULTS_PATH = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "EVAL_RESULTS.md"

CI_GATE_PRECISION = 0.95
CI_GATE_RECALL = 0.95


def _parse_table(text: str) -> list[dict[str, Any]]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    table_start = -1
    for i, line in enumerate(lines):
        if line.startswith("|") and line.endswith("|"):
            table_start = i
            break

    if table_start < 0:
        return []

    table_lines = []
    for line in lines[table_start:]:
        if not line.startswith("|"):
            break
        table_lines.append(line)

    if len(table_lines) < 3:
        return []

    raw_headers = [h.strip() for h in table_lines[0].strip("|").split("|")]
    raw_headers_lower = [h.lower() for h in raw_headers]

    rows = []
    for raw_row in table_lines[2:]:
        cells = [c.strip() for c in raw_row.strip("|").split("|")]
        if len(cells) != len(raw_headers):
            continue
        row: dict[str, Any] = {}
        for j, cell in enumerate(cells):
            col = raw_headers_lower[j]
            cleaned = cell.strip("`")
            if col in ("precision", "recall", "f1 score", "disagreement rate"):
                try:
                    row[col.replace(" ", "_")] = float(cleaned)
                except ValueError:
                    row[col.replace(" ", "_")] = None
            else:
                row[col.replace(" ", "_")] = cleaned
        rows.append(row)

    return rows


@router.get("/latest", summary="Latest eval results", response_description="Most recent holdout result row")
async def latest_eval_result() -> Response:
    try:
        text = _EVAL_RESULTS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return JSONResponse(
            status_code=503,
            content={"error": "Eval results file not found", "detail": "docs/EVAL_RESULTS.md is missing"},
        )

    rows = _parse_table(text)

    if not rows:
        return JSONResponse(
            status_code=503,
            content={"error": "Eval results not parseable",
                     "detail": "No data rows found in docs/EVAL_RESULTS.md"},
        )

    latest = rows[-1]
    return JSONResponse(content={
        "latest": latest,
        "threshold": {
            "precision": CI_GATE_PRECISION,
            "recall": CI_GATE_RECALL,
            "note": "CI gates PRs on these minimums (documented baseline minus 5pp tolerance)",
        },
    })
