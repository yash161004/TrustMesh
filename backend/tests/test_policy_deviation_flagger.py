import pytest
from app.models import NegotiationMessage, NegotiationScenario, LineItem, ProposedItem
from app.trust.detectors.policy import PolicyDeviationFlagger

def get_base_scenario():
        return NegotiationScenario(
        currency="USD",
        line_items=[
            LineItem(
                sku="SKU-TEST",
                product_name="Test Product",
                quantity=100,
                unit="units",
                market_reference_price=100.0,
                buyer_target_price=450.0,
                buyer_budget_cap=500.0,
                seller_asking_price=550.0,
                seller_floor_price=400.0,
            )
        ],
        delivery_preference_days=10,
        standard_delivery_days=20
    )

def get_base_message(role="buyer", price=450.0, quantity=100):
    return NegotiationMessage(
        message_type="OFFER",
        sender="buyer-agent-1" if role == "buyer" else "seller-agent-1",
        proposed_items=[
            ProposedItem(sku="SKU-TEST", price=price, quantity=quantity)
        ],
        delivery_terms="Standard",
        timestamp="2026-07-16T12:00:00Z",
        turn_number=1
    )

def test_buyer_at_exact_cap():
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()
    message = get_base_message(role="buyer", price=500.0)
    
    result = flagger.evaluate(message, scenario, "buyer")
    assert not result["flagged"]
    assert result["trust_impact"] == 0

def test_buyer_exceeds_cap():
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()
    message = get_base_message(role="buyer", price=500.01)
    
    result = flagger.evaluate(message, scenario, "buyer")
    assert result["flagged"]
    assert result["trust_impact"] == -35
    assert "exceeding budget cap" in result["reason"]

def test_seller_at_exact_floor():
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()
    message = get_base_message(role="seller", price=400.0)
    
    result = flagger.evaluate(message, scenario, "seller")
    assert not result["flagged"]

def test_seller_below_floor():
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()
    message = get_base_message(role="seller", price=399.99)
    
    result = flagger.evaluate(message, scenario, "seller")
    assert result["flagged"]
    assert result["trust_impact"] == -40
    assert "below floor" in result["reason"]

def test_quantity_mismatch():
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()
    message = get_base_message(role="seller", quantity=101)
    
    result = flagger.evaluate(message, scenario, "seller")
    assert result["flagged"]
    assert result["trust_impact"] == -25
    assert "quantity" in result["reason"]

def test_currency_mismatch():
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()
    message = get_base_message(role="seller")
    message.delivery_terms = "We accept 450 EUR/unit."
    
    result = flagger.evaluate(message, scenario, "seller")
    assert result["flagged"]
    assert result["trust_impact"] == -45
    assert "unexpected currency" in result["reason"]

def test_multiple_violations():
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()
    message = get_base_message(role="seller", price=300.0, quantity=50)

    result = flagger.evaluate(message, scenario, "seller")
    assert result["flagged"]
    assert result["trust_impact"] == -65
    assert "below floor" in result["reason"]
    assert "quantity" in result["reason"]


def test_currency_symbol_swap_detected():
    """A foreign currency *symbol* (not just its code) is now detected."""
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()  # USD
    message = get_base_message(role="seller")
    message.delivery_terms = "Settle in €480/unit."  # EUR symbol
    result = flagger.evaluate(message, scenario, "seller")
    assert result["flagged"]
    assert "unexpected currency" in result["reason"]


def test_scenario_dollar_symbol_not_flagged():
    """The scenario's own currency and the ambiguous '$' do not trigger a swap flag."""
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()  # USD ($)
    message = get_base_message(role="seller")
    message.delivery_terms = "Pay $500 total on delivery."
    result = flagger.evaluate(message, scenario, "seller")
    # No foreign code or non-ambiguous symbol present.
    assert "unexpected currency" not in result.get("reason", "")


def test_currency_code_word_boundary():
    """A code embedded in another token is not a false-positive swap."""
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()  # USD
    message = get_base_message(role="seller")
    message.delivery_terms = "Delivery to EURspares warehouse."  # 'EUR' inside a word
    result = flagger.evaluate(message, scenario, "seller")
    assert "unexpected currency" not in result.get("reason", "")


def test_invalid_currency_rejected():
    """NegotiationScenario rejects a currency not in the registry."""
    import pytest as _pytest
    with _pytest.raises(Exception):
        NegotiationScenario(
            currency="XYZ",
            line_items=[LineItem(
                sku="SKU-TEST", product_name="Test", quantity=10, unit="units",
                market_reference_price=100.0, buyer_target_price=90.0,
                buyer_budget_cap=110.0, seller_asking_price=120.0, seller_floor_price=80.0,
            )],
            delivery_preference_days=10, standard_delivery_days=20,
        )


def test_currency_normalized_to_upper():
    """Lowercase currency input is normalized against the registry."""
    scenario = NegotiationScenario(
        currency="usd",
        line_items=[LineItem(
            sku="SKU-TEST", product_name="Test", quantity=10, unit="units",
            market_reference_price=100.0, buyer_target_price=90.0,
            buyer_budget_cap=110.0, seller_asking_price=120.0, seller_floor_price=80.0,
        )],
        delivery_preference_days=10, standard_delivery_days=20,
    )
    assert scenario.currency == "USD"
