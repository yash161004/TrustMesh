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
    agent = BuyerAgent()
    assert agent.should_accept(DEFAULT_SCENARIO.buyer_target_price, DEFAULT_SCENARIO.quantity)
    assert not agent.should_accept(DEFAULT_SCENARIO.buyer_budget_cap + 10, DEFAULT_SCENARIO.quantity)

def test_seller_initial_offer():
    agent = SellerAgent()
    msg = agent.create_initial_offer({})
    # Initial asking should be above floor
    assert msg.price >= DEFAULT_SCENARIO.seller_floor_price
    assert msg.message_type.value == "OFFER"

def test_seller_should_accept():
    agent = SellerAgent()
    assert agent.should_accept(DEFAULT_SCENARIO.seller_asking_price, DEFAULT_SCENARIO.quantity)
    assert not agent.should_accept(DEFAULT_SCENARIO.seller_floor_price - 10, DEFAULT_SCENARIO.quantity)
