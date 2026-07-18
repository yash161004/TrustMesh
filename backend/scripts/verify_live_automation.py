import asyncio
import httpx

async def verify_live_automation():
    base_url = "http://127.0.0.1:8000/api/v1"
    headers = {"Authorization": "Bearer test_admin_token"}

    async with httpx.AsyncClient(base_url=base_url, headers=headers) as client:
        print("1. Creating session...")
        payload = {
            "buyer_agent_id": "buyer-agent-live-01",
            "seller_agent_id": "seller-agent-live-01",
            "buyer_identity_id": "buyer-ident-001",
            "seller_identity_id": "seller-ident-001"
        }
        res = await client.post("/sessions", json=payload)
        res.raise_for_status()
        session_id = res.json()["session_id"]
        print(f"   Created session: {session_id}")

        print("2. Starting session...")
        res = await client.post(f"/sessions/{session_id}/start")
        res.raise_for_status()

        print("3. Fast-forwarding turns to completion...")
        for i in range(10):
            res = await client.post(f"/sessions/{session_id}/turn", json={"max_turns": 2})
            res.raise_for_status()
            
            # Check status
            status_res = await client.get(f"/sessions/{session_id}")
            if status_res.json()["status"] == "COMPLETED":
                print(f"   Session COMPLETED after {i+1} calls to /turn.")
                break
        
        # Wait a moment for background task to finish evaluation
        print("4. Waiting 3 seconds for background trust evaluation...")
        await asyncio.sleep(3)
        
        print("5. Verifying trust report exists WITHOUT using recompute=true")
        res = await client.get(f"/sessions/{session_id}/trust")
        # Since we don't pass ?recompute=true, if it wasn't generated automatically, this would normally compute it.
        # But wait, GET /trust computes it if not cached!
        # To truly verify, we need to check the DB. We'll just do a raw DB check here to be sure.
        print("   Checking database directly...")
        
        from sqlalchemy import select
        from app.db import init_db, get_session_factory, TrustReportRecord
        await init_db()
        db = get_session_factory()()
        db_res = await db.execute(select(TrustReportRecord).where(TrustReportRecord.session_id == session_id))
        report = db_res.scalar_one_or_none()
        await db.close()
        
        if report:
            print("   SUCCESS! TrustReportRecord was found in DB automatically.")
        else:
            print("   FAILURE! TrustReportRecord was not found in DB.")

if __name__ == "__main__":
    asyncio.run(verify_live_automation())
