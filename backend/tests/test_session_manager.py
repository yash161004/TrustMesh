import pytest
from app.session_manager import session_manager
from app.models import NegotiationSessionStatus

@pytest.mark.asyncio
async def test_session_lifecycle():
    # Create session
    session = await session_manager.create_session(provider="mock")
    assert session.status == NegotiationSessionStatus.PENDING
    assert session.session_id is not None

    # Start session
    msg = await session_manager.start_session(session.session_id)
    assert msg.message_type.value == "OFFER"
    
    # Process turn
    msgs = await session_manager.process_turn(session.session_id, max_turns=1)
    assert len(msgs) > 0

    # Test reaches completed state
    await session_manager.process_turn(session.session_id, max_turns=10)
    updated_session = await session_manager.get_session(session.session_id)
    assert updated_session.status in [NegotiationSessionStatus.COMPLETED, NegotiationSessionStatus.FAILED]
