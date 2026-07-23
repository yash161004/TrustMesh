import pytest
from app.agents.buyer import BuyerAgent
from app.agents.seller import SellerAgent
from app.models import DEFAULT_SCENARIO

def test_buyer_initial_offer():
    agent = BuyerAgent()
    msg = agent.create_initial_offer({})
    # Initial offer should be below market ref
    assert msg.price < DEFAULT_SCENARIO.market_reference_price
    assert msg.message_type.value == "OFFER"

def test_buyer_should_accept():
    from app.models import ProposedItem
    agent = BuyerAgent()
    sku = DEFAULT_SCENARIO.line_items[0].sku
    target = DEFAULT_SCENARIO.buyer_target_price
    cap = DEFAULT_SCENARIO.buyer_budget_cap
    assert agent.should_accept([ProposedItem(sku=sku, price=target, quantity=10)])
    assert not agent.should_accept([ProposedItem(sku=sku, price=cap + 10, quantity=10)])

def test_seller_initial_offer():
    agent = SellerAgent()
    msg = agent.create_initial_offer({})
    # Initial asking should be above floor
    assert msg.price >= DEFAULT_SCENARIO.seller_floor_price
    assert msg.message_type.value == "OFFER"

def test_seller_should_accept():
    agent = SellerAgent()
    ask = DEFAULT_SCENARIO.seller_asking_price
    floor = DEFAULT_SCENARIO.seller_floor_price
    assert agent.should_accept(ask, 10)
    assert not agent.should_accept(floor - 10, 10)

@pytest.mark.asyncio
async def test_agent_price_extraction_from_notes():
    class DummyClient:
        async def generate(self, messages, system, temperature=0.7):
            return '{"message_type": "COUNTER_OFFER", "price": 0.0, "quantity": 1, "notes": "Counter-offer at $380.00 is proposed."}'

    agent = BuyerAgent(llm_client=DummyClient())
    msg = await agent.generate_response({"last_price": 400.0})
    assert msg.price == 380.0
    assert msg.message_type.value == "COUNTER_OFFER"

