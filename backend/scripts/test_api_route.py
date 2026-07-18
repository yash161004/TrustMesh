import asyncio
import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).parent.parent))

from app.main import app
from app.db import init_db, get_agent_reputation, get_session_factory
from sqlalchemy import text

def run_test():
    with TestClient(app) as client:
        print("\n1. Creating Session via API...")
        res = client.post("/api/v1/sessions", json={
            "buyer_agent_id": "api-buyer",
            "seller_agent_id": "api-seller",
            "provider": "mock"
        })
        if res.status_code != 200:
            print("Failed to create session:", res.text)
            return None, None
        session_id = res.json()["session_id"]
        print(f"Created Session: {session_id}")
        
        print("\n2. Running 1 turn via API...")
        res = client.post(f"/api/v1/sessions/{session_id}/turn", json={"max_turns": 1})
        if res.status_code != 200:
            print("Failed to run turn:", res.text)
            return None, None
            
        print("\n3. Hitting /trust endpoint...")
        trust_res = client.get(f"/api/v1/sessions/{session_id}/trust")
        if trust_res.status_code != 200:
            print("Failed to get trust report:", trust_res.text)
            return None, None
        report = trust_res.json()
        print(f"Trust Report Summary: {report['summary']}")
        
        buyer_violations = report["buyer_score"]["violation_count"]
        seller_violations = report["seller_score"]["violation_count"]
        print(f"Buyer Violations in Report: {buyer_violations}")
        print(f"Seller Violations in Report: {seller_violations}")
        return buyer_violations, seller_violations

async def main():
    print("Initialising DB...")
    await init_db()
    
    # Clean up any previous runs
    factory = get_session_factory()
    async with factory() as db:
        await db.execute(text("DELETE FROM agent_reputations WHERE agent_id IN ('api-buyer', 'api-seller')"))
        await db.commit()
    
    # Run the sync TestClient wrapper inside a thread to avoid loop conflicts
    buyer_violations, seller_violations = await asyncio.to_thread(run_test)
    
    if buyer_violations is None:
        return
        
    print("\n4. Verifying DB Counters...")
    buyer_rep = await get_agent_reputation("api-buyer")
    seller_rep = await get_agent_reputation("api-seller")
    
    print(f"api-buyer: total_sessions={buyer_rep['total_sessions']}, violations_count={buyer_rep['violations_count']}, trust_score={buyer_rep['trust_score']:.2f}")
    print(f"api-seller: total_sessions={seller_rep['total_sessions']}, violations_count={seller_rep['violations_count']}, trust_score={seller_rep['trust_score']:.2f}")
    
    assert buyer_rep['total_sessions'] == 1, "Buyer total_sessions should be 1"
    assert buyer_rep['violations_count'] == buyer_violations, "Buyer violations_count mismatch"
    assert seller_rep['total_sessions'] == 1, "Seller total_sessions should be 1"
    assert seller_rep['violations_count'] == seller_violations, "Seller violations_count mismatch"
    print("\n[SUCCESS] End-to-end API route correctly calls update_agent_reputation_v2!")

if __name__ == "__main__":
    asyncio.run(main())
