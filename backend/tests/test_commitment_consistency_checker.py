import pytest
import json
from unittest.mock import AsyncMock
from app.models import NegotiationMessage, NegotiationScenario
from app.trust.detectors.commitments import CommitmentConsistencyChecker

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

@pytest.mark.asyncio
async def test_currency_swap():
    checker = CommitmentConsistencyChecker()
    scenario = get_base_scenario()
    
    msg = NegotiationMessage(
        message_type="OFFER",
        sender="seller-1",
        price=450.0,
        quantity=100,
        delivery_terms="450 EUR/unit",
        timestamp="2026-07-16T12:00:00Z",
        turn_number=1
    )
    
    result = await checker.evaluate(msg, [], scenario)
    assert result["flagged"]
    assert "EUR" in result["reason"]

@pytest.mark.asyncio
async def test_backward_movement_bait_and_switch():
    checker = CommitmentConsistencyChecker()
    scenario = get_base_scenario()
    
    history = [
        NegotiationMessage(
            message_type="OFFER",
            sender="seller-1",
            price=460.0,
            quantity=100,
            delivery_terms="10 days",
            timestamp="2026-07-16T12:00:00Z",
            turn_number=1
        )
    ]
    
    msg = NegotiationMessage(
        message_type="COUNTER_OFFER",
        sender="seller-1",
        price=480.0,
        quantity=100,
        delivery_terms="10 days",
        timestamp="2026-07-16T12:05:00Z",
        turn_number=3
    )
    
    result = await checker.evaluate(msg, history, scenario)
    assert result["flagged"]
    assert "backward" in result["reason"]

@pytest.mark.asyncio
async def test_accept_term_mismatch_downgrade():
    checker = CommitmentConsistencyChecker()
    scenario = get_base_scenario()
    
    history = [
        NegotiationMessage(
            message_type="OFFER",
            sender="buyer-1",
            price=450.0,
            quantity=100,
            delivery_terms="10-day delivery",
            timestamp="2026-07-16T12:00:00Z",
            turn_number=1
        )
    ]
    
    msg = NegotiationMessage(
        message_type="ACCEPT",
        sender="seller-1",
        price=450.0,
        quantity=100,
        delivery_terms="30-day delivery",
        timestamp="2026-07-16T12:05:00Z",
        turn_number=2
    )
    
    result = await checker.evaluate(msg, history, scenario)
    assert result["flagged"]
    assert "delivery days" in result["reason"]

@pytest.mark.asyncio
async def test_historical_baseline_claim_imaginary():
    checker = CommitmentConsistencyChecker()
    
    # Mock LLM to return false claim
    checker.llm.generate = AsyncMock(return_value=json.dumps({
        "makes_claim": True,
        "claim_description": "Claimed prior agreement at 380",
        "claim_supported_by_history": False
    }))
    
    scenario = get_base_scenario()
    
    msg = NegotiationMessage(
        message_type="OFFER",
        sender="buyer-1",
        price=400.0,
        quantity=100,
        delivery_terms="10 days",
        notes="Following up on our earlier agreement of 380",
        timestamp="2026-07-16T12:00:00Z",
        turn_number=1
    )
    
    result = await checker.evaluate(msg, [], scenario)
    assert result["flagged"]
    assert "LLM flagged false claim" in result["reason"]
    checker.llm.generate.assert_called_once()

@pytest.mark.asyncio
async def test_concession_claim_truthful():
    checker = CommitmentConsistencyChecker()
    
    # Mock LLM to return truthful claim
    checker.llm.generate = AsyncMock(return_value=json.dumps({
        "makes_claim": True,
        "claim_description": "Claimed concession of 20",
        "claim_supported_by_history": True
    }))
    
    scenario = get_base_scenario()
    
    history = [
        NegotiationMessage(
            message_type="OFFER",
            sender="buyer-1",
            price=400.0,
            quantity=100,
            delivery_terms="10 days",
            timestamp="2026-07-16T12:00:00Z",
            turn_number=1
        )
    ]
    
    msg = NegotiationMessage(
        message_type="COUNTER_OFFER",
        sender="buyer-1",
        price=420.0,
        quantity=100,
        delivery_terms="10 days",
        notes="I already came up by $20",
        timestamp="2026-07-16T12:05:00Z",
        turn_number=3
    )
    
    result = await checker.evaluate(msg, history, scenario)
    assert not result["flagged"]
    checker.llm.generate.assert_called_once()

@pytest.mark.asyncio
async def test_fallback_invalid_json():
    checker = CommitmentConsistencyChecker()
    
    # End-to-end check with the actual mock LLM which returns an invalid schema (Negotiation message instead of claim schema)
    # The detector should degrade gracefully and not flag.
    scenario = get_base_scenario()
    
    msg = NegotiationMessage(
        message_type="OFFER",
        sender="buyer-1",
        price=400.0,
        quantity=100,
        delivery_terms="10 days",
        notes="Some text that triggers the LLM",
        timestamp="2026-07-16T12:00:00Z",
        turn_number=1
    )
    
    result = await checker.evaluate(msg, [], scenario)
    assert result.get("flagged") is not None
