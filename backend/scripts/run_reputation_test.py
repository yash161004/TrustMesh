import asyncio
import sys
from pathlib import Path

# Add backend dir to path so imports work
sys.path.append(str(Path(__file__).parent.parent))

from app.db import init_db, get_agent_reputation, get_session_factory, AgentReputationRecord, update_agent_reputation_v2
from app.session_manager import session_manager
from app.trust.engine import trust_engine
from app.trust.models import ViolationType
from datetime import datetime, timezone

async def main():
    print("=== Cross-Session Reputation Test ===")
    print("1. Initialising DB to ensure demo agents exist...")
    await init_db()

    print("\n2. Checking seeded reputation...")
    buyer_id = "demo-buyer-bad-actor"
    seller_id = "demo-seller-good"
    
    buyer_rep = await get_agent_reputation(buyer_id)
    seller_rep = await get_agent_reputation(seller_id)
    
    print(f"Buyer ({buyer_id}): trust_score={buyer_rep['trust_score']:.2f}")
    print(f"Seller ({seller_id}): trust_score={seller_rep['trust_score']:.2f}")
    
    assert buyer_rep["trust_score"] == 0.30, f"Expected buyer to have 0.30, got {buyer_rep['trust_score']}"
    assert seller_rep["trust_score"] == 0.75, f"Expected seller to have 0.75, got {seller_rep['trust_score']}"
    
    print("\n3. Creating negotiation session with low-reputation buyer...")
    session = await session_manager.create_session(
        buyer_agent_id=buyer_id,
        seller_agent_id=seller_id,
        provider="mock"
    )
    
    print("Running 1 turn...")
    await session_manager.process_turn(session.session_id, max_turns=1)
    
    print("\n4. Evaluating trust...")
    session_with_msgs = await session_manager.get_session(session.session_id)
    report = await trust_engine.evaluate_session(
        session_id=session.session_id,
        messages=session_with_msgs.messages,
        buyer_agent_id=buyer_id,
        seller_agent_id=seller_id,
        buyer_trust_score=buyer_rep["trust_score"],
        seller_trust_score=seller_rep["trust_score"],
        skip_llm=True
    )
    
    print(f"\nTotal Violations: {len(report.violations)}")
    for v in report.violations:
        print(f" - {v.severity.value} | {v.violation_type.value} | Agent: {v.agent_id} | {v.description}")
        
    # Verify LOW_REPUTATION fired for buyer
    low_rep_flags = [v for v in report.violations if v.violation_type == ViolationType.LOW_REPUTATION and v.agent_id == buyer_id]
    
    assert len(low_rep_flags) > 0, "LOW_REPUTATION violation did not fire for the buyer!"
    print("[SUCCESS] LOW_REPUTATION violation was correctly flagged.")

    # Seed agents for Tests 2 and 3
    factory = get_session_factory()
    async with factory() as db:
        now = datetime.now(timezone.utc)
        agent2 = AgentReputationRecord(agent_id="test-agent-2", trust_score=0.5, total_sessions=0, violations_count=0, last_updated=now)
        agent3 = AgentReputationRecord(agent_id="test-agent-3", trust_score=0.05, total_sessions=0, violations_count=0, last_updated=now)
        # Delete if they exist to make script idempotent
        from sqlalchemy import text
        await db.execute(text("DELETE FROM agent_reputations WHERE agent_id IN ('test-agent-2', 'test-agent-3')"))
        db.add_all([agent2, agent3])
        await db.commit()

    # Test 2: Recovery and threshold
    print("\n=== Test 2: Recovery and Threshold ===")
    await update_agent_reputation_v2("test-agent-2", 0)
    rep2 = await get_agent_reputation("test-agent-2")
    assert abs(rep2["trust_score"] - 0.52) < 0.001, f"Expected 0.52, got {rep2['trust_score']}"
    
    # Verify LOW_REPUTATION does NOT fire for 0.5
    report2 = await trust_engine.evaluate_session(
        session_id="dummy-session-2",
        messages=[],
        buyer_agent_id="test-agent-2",
        seller_agent_id="dummy-seller",
        buyer_trust_score=0.5,
        seller_trust_score=1.0,
        skip_llm=True
    )
    low_rep_flags_2 = [v for v in report2.violations if v.violation_type == ViolationType.LOW_REPUTATION and v.agent_id == "test-agent-2"]
    assert len(low_rep_flags_2) == 0, "LOW_REPUTATION fired for trust_score 0.5, but shouldn't!"
    print("[SUCCESS] Recovery added 0.02 correctly, and LOW_REPUTATION did not fire for 0.5.")

    # Test 3: Floor behavior
    print("\n=== Test 3: Floor Behavior ===")
    await update_agent_reputation_v2("test-agent-3", 1)
    rep3 = await get_agent_reputation("test-agent-3")
    assert rep3["trust_score"] == 0.0, f"Expected 0.0, got {rep3['trust_score']}"
    print("[SUCCESS] Penalty floored at 0.0 correctly.")

if __name__ == "__main__":
    asyncio.run(main())
