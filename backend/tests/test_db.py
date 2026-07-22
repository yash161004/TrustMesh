import pytest
from datetime import datetime, timezone
from app.db import save_session, load_session, save_message, load_messages

@pytest.mark.asyncio
async def test_save_and_load_session():
    session_id = "test-session-123"
    await save_session(
        session_id=session_id,
        buyer_agent_id="buyer1",
        seller_agent_id="seller1",
        status="PENDING",
        created_at=datetime.now(timezone.utc)
    )
    loaded = await load_session(session_id)
    assert loaded is not None
    assert loaded["session_id"] == session_id
    assert loaded["buyer_agent_id"] == "buyer1"

@pytest.mark.asyncio
async def test_save_and_load_message():
    session_id = "test-session-456"
    await save_session(
        session_id=session_id,
        buyer_agent_id="buyer1",
        seller_agent_id="seller1",
        status="PENDING",
        created_at=datetime.now(timezone.utc)
    )
    await save_message(
        session_id=session_id,
        message_type="OFFER",
        sender="buyer1",
        proposed_items=[{"sku": "SKU-001", "price": 100.0, "quantity": 10}],
        delivery_terms="Fast",
        timestamp=datetime.now(timezone.utc),
        turn_number=1
    )
    msgs = await load_messages(session_id)
    assert len(msgs) == 1
    assert "proposed_items" in msgs[0]
    assert msgs[0]["proposed_items"][0]["price"] == 100.0
