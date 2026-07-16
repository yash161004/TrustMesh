import pytest
from app.models import NegotiationMessage, NegotiationScenario
from app.trust.detectors.policy import PolicyDeviationFlagger

def get_base_scenario():
    return NegotiationScenario(
        product_name="Test Product",
        quantity=100,
        currency="USD",
        market_reference_price=100.0,
        buyer_budget_cap=500.0,
        buyer_target_price=450.0,
        seller_floor_price=400.0,
        seller_asking_price=550.0,
        delivery_preference_days=10,
        standard_delivery_days=20
    )

def get_base_message(role="buyer"):
    return NegotiationMessage(
        message_type="OFFER",
        sender="buyer-agent-1" if role == "buyer" else "seller-agent-1",
        price=450.0,
        quantity=100,
        delivery_terms="Standard",
        timestamp="2026-07-16T12:00:00Z",
        turn_number=1
    )

def test_buyer_at_exact_cap():
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()
    message = get_base_message(role="buyer")
    message.price = 500.0
    
    result = flagger.evaluate(message, scenario, "buyer")
    assert not result["flagged"]
    assert result["trust_impact"] == 0

def test_buyer_exceeds_cap():
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()
    message = get_base_message(role="buyer")
    message.price = 500.01
    
    result = flagger.evaluate(message, scenario, "buyer")
    assert result["flagged"]
    assert result["trust_impact"] == -35
    assert "exceeding budget cap" in result["reason"]

def test_seller_at_exact_floor():
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()
    message = get_base_message(role="seller")
    message.price = 400.0
    
    result = flagger.evaluate(message, scenario, "seller")
    assert not result["flagged"]

def test_seller_below_floor():
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()
    message = get_base_message(role="seller")
    message.price = 399.99
    
    result = flagger.evaluate(message, scenario, "seller")
    assert result["flagged"]
    assert result["trust_impact"] == -40
    assert "below floor" in result["reason"]

def test_quantity_mismatch():
    flagger = PolicyDeviationFlagger()
    scenario = get_base_scenario()
    message = get_base_message(role="seller")
    message.quantity = 101
    
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
    message = get_base_message(role="seller")
    message.price = 300.0
    message.quantity = 50
    
    result = flagger.evaluate(message, scenario, "seller")
    assert result["flagged"]
    assert result["trust_impact"] == -65
    assert "below floor" in result["reason"]
    assert "quantity" in result["reason"]
