"""
TrustMesh — Deal Outcome Feature Engineering.

Pure functions that turn a (scenario, messages, trust_report) triple for one
COMPLETED session into a flat feature dict. Deliberately has zero DB or async
dependency so it can be unit-tested and reused identically by both the
offline training script and the online inference path.

Label policy
------------
FAILED sessions are infrastructure failures (LLM provider rate limits /
timeouts — see docs/EVAL_RESULTS.md and the v4/v5 batch incident), not a
negotiation outcome. They carry no signal about *whether a deal would have
closed* and must never be trained on as a negative class alongside NO_DEAL.
`load_training_frame` drops them; callers doing single-session inference on
a still-in-progress session should not call this at all (there is no
FAILED/COMPLETED distinction to make there).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from statistics import mean
from typing import Any, Optional

FEATURE_NAMES: list[str] = [
    "num_line_items",
    "num_non_price_terms",
    "avg_initial_gap_pct",
    "avg_market_reference_price_log",
    "total_turns",
    "violation_count",
    "critical_or_high_violation_count",
    "has_manipulation_flag",
    "buyer_trust_score",
    "seller_trust_score",
    "price_convergence_rate",
]


@dataclass
class SessionFeatures:
    session_id: str
    features: dict[str, float]
    label: Optional[int] = None  # 1 = DEAL, 0 = NO_DEAL; None for inference-time
    outcome: Optional[str] = None


def _safe_json(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def _line_items(scenario: dict) -> list[dict]:
    return scenario.get("line_items") or []


def _initial_gap_pct(line_items: list[dict]) -> float:
    """Mean, across line items, of (seller_ask - buyer_target) / market_ref.

    Larger = harder negotiation at the start. Uses buyer_target rather than
    buyer_budget_cap because target reflects the buyer's actual opening
    aspiration, which is what the seller's opening ask is really being
    measured against turn 1.
    """
    gaps = []
    for item in line_items:
        ref = item.get("market_reference_price") or 0.0
        ask = item.get("seller_asking_price")
        target = item.get("buyer_target_price")
        if not ref or ask is None or target is None:
            continue
        gaps.append((ask - target) / ref)
    return mean(gaps) if gaps else 0.0


def _avg_market_ref_log(line_items: list[dict]) -> float:
    import math

    refs = [item.get("market_reference_price") for item in line_items if item.get("market_reference_price")]
    if not refs:
        return 0.0
    return math.log1p(mean(refs))


def _messages_by_sku_price_trend(messages: list[dict], line_items: list[dict]) -> float:
    """Fraction the price gap closed between first and last PROPOSE-type turn.

    1.0 = fully converged to buyer/seller midpoint or better, 0.0 = no
    movement, negative = the gap widened. Averaged across SKUs that appear
    in both the scenario and at least two distinct proposal messages.
    """
    if not messages or not line_items:
        return 0.0

    sku_targets = {
        item.get("sku"): (item.get("seller_asking_price"), item.get("buyer_target_price"))
        for item in line_items
        if item.get("sku")
    }
    if not sku_targets:
        return 0.0

    # sku -> list[(turn_number, price)]
    trajectories: dict[str, list[tuple[int, float]]] = {sku: [] for sku in sku_targets}

    for msg in sorted(messages, key=lambda m: m.get("turn_number", 0)):
        items = _safe_json(msg.get("proposed_items_json")) or msg.get("proposed_items") or []
        turn = msg.get("turn_number", 0)
        for it in items:
            sku = it.get("sku")
            price = it.get("price")
            if sku in trajectories and price is not None:
                trajectories[sku].append((turn, price))

    convergences = []
    for sku, (ask, target) in sku_targets.items():
        traj = trajectories.get(sku, [])
        if len(traj) < 2 or ask is None or target is None or ask == target:
            continue
        initial_gap = abs(ask - target)
        if initial_gap == 0:
            continue
        first_price = traj[0][1]
        last_price = traj[-1][1]
        remaining_gap = abs(last_price - target)
        convergence = 1.0 - (remaining_gap / initial_gap)
        convergences.append(convergence)

    return mean(convergences) if convergences else 0.0


def _trust_report_fields(report: Optional[dict]) -> dict[str, float]:
    if not report:
        return {
            "violation_count": 0.0,
            "critical_or_high_violation_count": 0.0,
            "has_manipulation_flag": 0.0,
            "buyer_trust_score": 75.0,  # neutral prior matching AgentReputationRecord default (0.75 * 100)
            "seller_trust_score": 75.0,
        }

    violations = report.get("violations") or []
    critical_or_high = sum(1 for v in violations if v.get("severity") in ("HIGH", "CRITICAL"))
    manipulation = any(v.get("violation_type") == "MANIPULATION_PATTERN" for v in violations)

    buyer_score = report.get("buyer_score") or {}
    seller_score = report.get("seller_score") or {}

    return {
        "violation_count": float(len(violations)),
        "critical_or_high_violation_count": float(critical_or_high),
        "has_manipulation_flag": 1.0 if manipulation else 0.0,
        "buyer_trust_score": float(buyer_score.get("overall_score", 75.0)),
        "seller_trust_score": float(seller_score.get("overall_score", 75.0)),
    }


def extract_features(
    session_id: str,
    scenario: dict,
    messages: list[dict],
    trust_report: Optional[dict],
    outcome: Optional[str] = None,
) -> SessionFeatures:
    """Build one feature row for a single session.

    Parameters mirror what's already loaded by load_session / load_messages /
    load_trust_report in app/db.py — callers pass those dicts straight
    through, no extra parsing needed beyond JSON fields those loaders leave
    as strings.
    """
    scenario = scenario or {}
    line_items = _line_items(scenario)
    messages = messages or []

    feats: dict[str, float] = {
        "num_line_items": float(len(line_items)),
        "num_non_price_terms": float(len(scenario.get("non_price_terms") or [])),
        "avg_initial_gap_pct": _initial_gap_pct(line_items),
        "avg_market_reference_price_log": _avg_market_ref_log(line_items),
        "total_turns": float(max((m.get("turn_number", 0) for m in messages), default=0)),
        "price_convergence_rate": _messages_by_sku_price_trend(messages, line_items),
    }
    feats.update(_trust_report_fields(trust_report))

    label = None
    if outcome == "DEAL":
        label = 1
    elif outcome in ("NO_DEAL", "MAX_TURNS"):
        label = 0
    # FAILED -> label stays None; caller (build_training_frame) drops these rows

    return SessionFeatures(session_id=session_id, features=feats, label=label, outcome=outcome)


def features_to_vector(feats: dict[str, float]) -> list[float]:
    """Order a feature dict into the fixed FEATURE_NAMES order for the model."""
    return [feats.get(name, 0.0) for name in FEATURE_NAMES]
