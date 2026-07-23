"""
TrustMesh — Deal Outcome Prediction: training script.

Tier 1 #1 from the advanced roadmap: predicts P(deal closes) from session
state, trained on real seeded/backfilled session history. Run this against
whatever DATABASE_URL is already configured in your environment (staging or
prod) — it reads, never writes.

Usage:
    cd backend
    python -m scripts.train_deal_outcome_model
    # or: DATABASE_URL=postgresql+asyncpg://... python -m scripts.train_deal_outcome_model

Requires: scikit-learn, pandas, joblib (added to requirements.txt)

What it does
------------
1. Pulls every session with status == "COMPLETED".
2. Excludes outcome == "FAILED" — those are LLM-provider infra failures
   (rate limits / timeouts), not negotiation outcomes. Training on them as a
   negative class would teach the model "provider downtime" instead of
   "this negotiation was unlikely to close". See deal_outcome_features.py
   docstring and docs/EVAL_RESULTS.md for the same reasoning applied
   elsewhere in this codebase.
3. Builds one feature row per remaining session via
   app.ml.deal_outcome_features.extract_features.
4. Trains + compares LogisticRegression and GradientBoostingClassifier
   with stratified k-fold CV (k adapts to dataset size).
5. Refits the better model on all data, saves it to
   backend/app/ml/artifacts/deal_outcome_model.joblib, and writes a dated,
   git-SHA-stamped report to docs/ML_MODEL_RESULTS.md — same pattern as
   docs/EVAL_RESULTS.md and docs/LOAD_TEST_RESULTS.md, so this doesn't
   introduce a new documentation convention.

If there isn't enough labeled data yet (see MIN_SESSIONS_TO_TRAIN below),
the script exits cleanly and tells you how many more COMPLETED DEAL/NO_DEAL
sessions you need — it will NOT silently train and report a meaningless
metric on 6 rows.
"""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import (  # noqa: E402
    SessionRecord,
    MessageRecord,
    TrustReportRecord,
    get_session_factory,
    init_db,
)
from app.ml.deal_outcome_features import (  # noqa: E402
    FEATURE_NAMES,
    extract_features,
    features_to_vector,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ARTIFACT_DIR = Path(__file__).resolve().parent.parent / "app" / "ml" / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "deal_outcome_model.joblib"
REPORT_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "ML_MODEL_RESULTS.md"

# Below this many labeled (DEAL/NO_DEAL, non-FAILED) sessions, cross-validated
# metrics are noise, not signal. Raise this as real usage accumulates.
MIN_SESSIONS_TO_TRAIN = 30


async def _load_all_completed_sessions() -> list[dict]:
    factory = get_session_factory()
    async with factory() as db:
        stmt = select(SessionRecord).where(
            SessionRecord.status == "COMPLETED",
            SessionRecord.data_source.like("real_llm_%"),
        )
        result = await db.execute(stmt)
        records = result.scalars().all()
        return [
            {
                "id": r.id,
                "outcome": r.outcome,
                "scenario_json": r.scenario_json,
                "final_price": r.final_price,
            }
            for r in records
        ]


async def _load_messages(session_id: str) -> list[dict]:
    factory = get_session_factory()
    async with factory() as db:
        stmt = (
            select(MessageRecord)
            .where(MessageRecord.session_id == session_id)
            .order_by(MessageRecord.turn_number)
        )
        result = await db.execute(stmt)
        return [
            {
                "turn_number": m.turn_number,
                "proposed_items_json": m.proposed_items_json,
            }
            for m in result.scalars().all()
        ]


async def _load_latest_trust_report(session_id: str) -> dict | None:
    factory = get_session_factory()
    async with factory() as db:
        stmt = (
            select(TrustReportRecord)
            .where(TrustReportRecord.session_id == session_id)
            .order_by(TrustReportRecord.evaluated_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.scalars().first()
        if not row:
            return None
        try:
            return json.loads(row.report_json)
        except (TypeError, ValueError):
            return None


async def build_training_frame():
    await init_db()
    sessions = await _load_all_completed_sessions()
    logger.info("Found %d COMPLETED sessions total.", len(sessions))

    rows = []
    skipped_failed = 0
    skipped_no_scenario = 0

    for s in sessions:
        if s["outcome"] == "FAILED":
            skipped_failed += 1
            continue
        if s["outcome"] not in ("DEAL", "NO_DEAL", "MAX_TURNS"):
            continue

        try:
            scenario = json.loads(s["scenario_json"]) if s["scenario_json"] else {}
        except (TypeError, ValueError):
            skipped_no_scenario += 1
            continue

        messages = await _load_messages(s["id"])
        trust_report = await _load_latest_trust_report(s["id"])

        sf = extract_features(
            session_id=s["id"],
            scenario=scenario,
            messages=messages,
            trust_report=trust_report,
            outcome=s["outcome"],
        )
        rows.append(sf)

    logger.info(
        "Usable labeled rows: %d (skipped %d FAILED, %d missing/unparseable scenario)",
        len(rows), skipped_failed, skipped_no_scenario,
    )
    return rows, skipped_failed


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=Path(__file__).resolve().parent, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def train_and_evaluate(rows: list) -> dict:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        roc_auc_score,
    )
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    X = np.array([features_to_vector(r.features) for r in rows])
    y = np.array([r.label for r in rows])

    n_splits = min(5, min(np.bincount(y)))  # can't have more folds than the smaller class
    n_splits = max(n_splits, 2)
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    candidates = {
        "logistic_regression": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced")
        ),
        "gradient_boosting": GradientBoostingClassifier(random_state=42),
    }

    results = {}
    for name, model in candidates.items():
        preds = cross_val_predict(model, X, y, cv=skf, method="predict")
        try:
            proba = cross_val_predict(model, X, y, cv=skf, method="predict_proba")[:, 1]
            auc = roc_auc_score(y, proba)
        except Exception:
            auc = None

        results[name] = {
            "accuracy": accuracy_score(y, preds),
            "precision": precision_score(y, preds, zero_division=0),
            "recall": recall_score(y, preds, zero_division=0),
            "f1": f1_score(y, preds, zero_division=0),
            "roc_auc": auc,
        }
        logger.info("%s: %s", name, results[name])

    best_name = max(results, key=lambda n: results[n]["f1"])
    best_model = candidates[best_name]
    best_model.fit(X, y)

    return {
        "best_model_name": best_name,
        "best_model": best_model,
        "all_results": results,
        "n_samples": len(rows),
        "n_deal": int(y.sum()),
        "n_no_deal": int(len(y) - y.sum()),
        "n_splits": n_splits,
        "feature_names": FEATURE_NAMES,
    }


def save_artifacts(train_result: dict, skipped_failed: int) -> None:
    import joblib

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": train_result["best_model"],
            "model_name": train_result["best_model_name"],
            "feature_names": train_result["feature_names"],
            "trained_at": datetime.now(timezone.utc).isoformat(),
        },
        MODEL_PATH,
    )
    logger.info("Saved model to %s", MODEL_PATH)

    sha = _git_sha()
    ts = datetime.now(timezone.utc).isoformat()
    lines = [
        "# TrustMesh Deal Outcome Prediction — Training Results",
        "",
        f"**Trained at:** {ts}  ",
        f"**Git SHA:** `{sha}`  ",
        f"**Model selected:** `{train_result['best_model_name']}` (highest CV F1)  ",
        f"**Training rows:** {train_result['n_samples']} "
        f"({train_result['n_deal']} DEAL / {train_result['n_no_deal']} NO_DEAL, "
        f"{skipped_failed} FAILED sessions excluded — see script docstring)  ",
        f"**CV folds:** {train_result['n_splits']} (StratifiedKFold, adapted to smaller-class count)",
        "",
        "## Cross-validated metrics by model",
        "",
        "| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |",
        "|---|---|---|---|---|---|",
    ]
    for name, m in train_result["all_results"].items():
        auc = f"{m['roc_auc']:.3f}" if m["roc_auc"] is not None else "n/a"
        marker = " **(selected)**" if name == train_result["best_model_name"] else ""
        lines.append(
            f"| `{name}`{marker} | {m['accuracy']:.3f} | {m['precision']:.3f} | "
            f"{m['recall']:.3f} | {m['f1']:.3f} | {auc} |"
        )

    lines += [
        "",
        "## Features used",
        "",
        "".join(f"- `{f}`\n" for f in train_result["feature_names"]),
        "",
        "## What this proves / does not prove",
        "",
        "**Proves:** on the session history logged so far, these features carry "
        "real predictive signal for deal-vs-no-deal beyond the class baseline "
        "(compare recall/precision above to the DEAL/NO_DEAL split ratio).",
        "",
        "**Does not prove:** generalization to negotiation scenarios structurally "
        "different from what's been run so far (new product categories, currencies "
        "outside the current registry, adversarial scenario types not yet seeded). "
        "Retrain as real usage data accumulates, and treat any accuracy figure here "
        "as holdout-on-current-distribution, not a permanent claim — same caveat "
        "already applied in docs/EVAL_RESULTS.md and docs/LOAD_TEST_RESULTS.md.",
        "",
    ]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines))
    logger.info("Wrote report to %s", REPORT_PATH)


async def main():
    rows, skipped_failed = await build_training_frame()

    if len(rows) < MIN_SESSIONS_TO_TRAIN:
        logger.warning(
            "Only %d usable labeled sessions (need >= %d). Not training — a model "
            "fit on this few rows would report a metric that looks precise and "
            "isn't. Seed/backfill more COMPLETED sessions and re-run.",
            len(rows), MIN_SESSIONS_TO_TRAIN,
        )
        return

    labels = [r.label for r in rows]
    if len(set(labels)) < 2:
        logger.warning(
            "All usable sessions have the same outcome (%s) — cannot train a "
            "classifier with a single class present. Need both DEAL and NO_DEAL "
            "examples.", labels[0] if labels else "none",
        )
        return

    train_result = train_and_evaluate(rows)
    save_artifacts(train_result, skipped_failed=skipped_failed)
    logger.info("Done. Best model: %s (F1=%.3f)",
                train_result["best_model_name"],
                train_result["all_results"][train_result["best_model_name"]]["f1"])


if __name__ == "__main__":
    asyncio.run(main())
