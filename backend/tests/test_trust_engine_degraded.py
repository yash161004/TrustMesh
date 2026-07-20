import pytest
import asyncio
from app.trust.engine import trust_engine
from app.models import NegotiationMessage, NegotiationScenario, MessageType
from app.trust.models import SessionEventType

@pytest.mark.asyncio
async def test_trust_engine_degraded():
    # Mock manipulation detector to always return degraded=True
    original_eval = trust_engine.manipulation.evaluate
    async def mock_eval(*args, **kwargs):
        return {"degraded": True, "flagged": False, "status": "DEGRADED", "disagreement_rate": 0.0, "reason": "Rate limited", "trust_impact": 0}
    trust_engine.manipulation.evaluate = mock_eval
    
    try:
        messages = [
            NegotiationMessage(
                message_type=MessageType.OFFER,
                sender="buyer-1",
                price=100.0,
                quantity=10,
                delivery_terms="Net 30",
                turn_number=1
            )
        ]
        scenario = NegotiationScenario(
            product_name="Widgets",
            quantity=10,
            currency="USD",
            market_reference_price=120,
            buyer_budget_cap=150,
            buyer_target_price=100,
            seller_floor_price=80,
            seller_asking_price=130,
            delivery_preference_days=30,
            standard_delivery_days=30
        )
        report = await trust_engine.evaluate_session("session-123", messages, "buyer-1", "seller-1", scenario, skip_llm=False)
        
        # Verify
        assert len(report.events) == 1
        assert report.events[0].event_type == SessionEventType.EVALUATION_DEGRADED
        assert report.events[0].message_turn == 1
        assert len(report.violations) == 0  # Should not be a violation
        
        print(f"SUCCESS: Event captured. Type: {report.events[0].event_type}, Msg Turn: {report.events[0].message_turn}")
    finally:
        trust_engine.manipulation.evaluate = original_eval

if __name__ == "__main__":
    asyncio.run(test_trust_engine_degraded())
