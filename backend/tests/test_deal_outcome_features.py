import json

from app.ml.deal_outcome_features import extract_features, features_to_vector, FEATURE_NAMES


def _scenario(n_items=1):
    line_items = []
    for i in range(n_items):
        line_items.append({
            "sku": f"SKU-{i}",
            "product_name": "Widget",
            "quantity": 100,
            "unit": "units",
            "market_reference_price": 500.0,
            "buyer_target_price": 440.0,
            "buyer_budget_cap": 500.0,
            "seller_asking_price": 550.0,
            "seller_floor_price": 420.0,
        })
    return {"currency": "USD", "line_items": line_items, "non_price_terms": []}


def _messages(sku="SKU-0", start=550.0, end=460.0, n_turns=4):
    msgs = []
    for t in range(1, n_turns + 1):
        price = start + (end - start) * (t - 1) / (n_turns - 1)
        msgs.append({
            "turn_number": t,
            "proposed_items_json": json.dumps([{"sku": sku, "price": price, "quantity": 100}]),
        })
    return msgs


def test_extract_features_deal_label():
    sf = extract_features("s1", _scenario(), _messages(), trust_report=None, outcome="DEAL")
    assert sf.label == 1
    assert sf.features["num_line_items"] == 1.0


def test_extract_features_no_deal_label():
    sf = extract_features("s2", _scenario(), _messages(), trust_report=None, outcome="NO_DEAL")
    assert sf.label == 0


def test_extract_features_max_turns_label():
    sf = extract_features("s2b", _scenario(), _messages(), trust_report=None, outcome="MAX_TURNS")
    assert sf.label == 0


def test_extract_features_failed_has_no_label():
    """FAILED sessions must never get a binary label — see module docstring:
    they're infra failures, not negotiation outcomes."""
    sf = extract_features("s3", _scenario(), _messages(), trust_report=None, outcome="FAILED")
    assert sf.label is None


def test_price_convergence_toward_target_is_positive():
    # Price moves from ask (550) all the way to target (440) -> full convergence
    sf = extract_features(
        "s4", _scenario(),
        _messages(sku="SKU-0", start=550.0, end=440.0),
        trust_report=None, outcome="DEAL",
    )
    assert sf.features["price_convergence_rate"] > 0.9


def test_price_no_movement_is_near_zero_convergence():
    sf = extract_features(
        "s5", _scenario(),
        _messages(sku="SKU-0", start=550.0, end=550.0),
        trust_report=None, outcome="NO_DEAL",
    )
    assert sf.features["price_convergence_rate"] == 0.0


def test_missing_trust_report_uses_neutral_defaults():
    sf = extract_features("s6", _scenario(), _messages(), trust_report=None, outcome="DEAL")
    assert sf.features["buyer_trust_score"] == 75.0
    assert sf.features["seller_trust_score"] == 75.0
    assert sf.features["violation_count"] == 0.0


def test_manipulation_flag_detected():
    report = {
        "violations": [{"violation_type": "MANIPULATION_PATTERN", "severity": "HIGH"}],
        "buyer_score": {"overall_score": 60.0},
        "seller_score": {"overall_score": 60.0},
    }
    sf = extract_features("s7", _scenario(), _messages(), trust_report=report, outcome="NO_DEAL")
    assert sf.features["has_manipulation_flag"] == 1.0
    assert sf.features["critical_or_high_violation_count"] == 1.0


def test_features_to_vector_matches_feature_names_length():
    sf = extract_features("s8", _scenario(), _messages(), trust_report=None, outcome="DEAL")
    vec = features_to_vector(sf.features)
    assert len(vec) == len(FEATURE_NAMES)


def test_multi_line_item_scenario():
    sf = extract_features("s9", _scenario(n_items=3), _messages(), trust_report=None, outcome="DEAL")
    assert sf.features["num_line_items"] == 3.0
