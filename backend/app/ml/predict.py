"""
TrustMesh — Deal Outcome Prediction: inference.

Loads the model trained by scripts/train_deal_outcome_model.py and scores a
session's *current* state (used mid-negotiation, so no outcome/label yet).

Not wired into any route yet — this is the integration point for a future
`GET /sessions/{id}/prediction` endpoint (Tier 1 #1's natural next step,
listed but not committed to in the roadmap docs). Kept separate from the
training script on purpose: routes should import this thin module, not the
training script's DB/sklearn-heavy import surface.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.ml.deal_outcome_features import extract_features, features_to_vector

_ARTIFACT_PATH = Path(__file__).resolve().parent / "artifacts" / "deal_outcome_model.joblib"

_cached_bundle: Optional[dict] = None


def _load_bundle() -> Optional[dict]:
    global _cached_bundle
    if _cached_bundle is not None:
        return _cached_bundle
    if not _ARTIFACT_PATH.exists():
        return None
    import joblib

    _cached_bundle = joblib.load(_ARTIFACT_PATH)
    return _cached_bundle


def model_available() -> bool:
    return _load_bundle() is not None


def predict_deal_probability(
    scenario: dict,
    messages: list[dict],
    trust_report: Optional[dict],
) -> Optional[dict]:
    """Return {"p_deal": float, "model_name": str, "trained_at": str} or None
    if no model has been trained yet (caller should degrade gracefully, e.g.
    hide the prediction UI rather than error).
    """
    bundle = _load_bundle()
    if bundle is None:
        return None

    sf = extract_features(
        session_id="__inference__",
        scenario=scenario,
        messages=messages,
        trust_report=trust_report,
        outcome=None,
    )
    vector = [features_to_vector(sf.features)]
    model = bundle["model"]

    try:
        proba = model.predict_proba(vector)[0][1]
    except AttributeError:
        # Fallback for any estimator without predict_proba
        proba = float(model.predict(vector)[0])

    return {
        "p_deal": float(proba),
        "model_name": bundle["model_name"],
        "trained_at": bundle["trained_at"],
    }
