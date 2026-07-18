import asyncio
import aiohttp
import time
import random
import json
from datetime import datetime

API_BASE = "http://127.0.0.1:8001/api/v1"
DURATION_SECONDS = 15 * 60  # 15 minutes

latencies = []
errors = []

async def record_request(session, method, url, **kwargs):
    start = time.time()
    try:
        if method == "GET":
            resp = await session.get(url, **kwargs)
        else:
            resp = await session.post(url, **kwargs)
            
        resp.raise_for_status()
        latencies.append((time.time() - start))
        return await resp.json()
    except Exception as e:
        errors.append({
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": url,
            "method": method,
            "error_type": type(e).__name__,
            "details": str(e)
        })
        raise e

async def hit_read_sessions(session):
    try:
        return await record_request(session, "GET", f"{API_BASE}/sessions")
    except:
        return []

async def hit_read_session_details(session, session_id):
    try:
        await record_request(session, "GET", f"{API_BASE}/sessions/{session_id}")
    except:
        pass

async def check_ledger(session, session_id):
    try:
        await record_request(session, "GET", f"{API_BASE}/sessions/{session_id}/ledger")
    except:
        pass

async def run_write_path(session):
    try:
        payload = {
            "buyer_agent_id": f"buyer-{random.randint(100, 999)}",
            "seller_agent_id": f"seller-{random.randint(100, 999)}",
            "provider": "mock"
        }
        data = await record_request(session, "POST", f"{API_BASE}/sessions", json=payload)
        session_id = data["session_id"]
        
        for _ in range(2):
            await record_request(session, "POST", f"{API_BASE}/sessions/{session_id}/turn", json={"max_turns": 1})
                
        await check_ledger(session, session_id)
    except:
        pass

async def worker(session, end_time, worker_id):
    while time.time() < end_time:
        action = random.choices(
            ["read_all", "read_one", "write_path"],
            weights=[3, 4, 1]
        )[0]
        
        if action == "read_all":
            await hit_read_sessions(session)
        elif action == "read_one":
            sessions = await hit_read_sessions(session)
            if sessions:
                sess_id = random.choice(sessions)["session_id"]
                await hit_read_session_details(session, sess_id)
                await check_ledger(session, sess_id)
        elif action == "write_path":
            await run_write_path(session)
            
        await asyncio.sleep(random.uniform(0.1, 0.5))

async def main():
    print(f"Starting V2 burn-in test for {DURATION_SECONDS} seconds...")
    end_time = time.time() + DURATION_SECONDS
    
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(worker(session, end_time, i)) for i in range(10)]
        await asyncio.gather(*tasks)
        
    print("\n--- BURN-IN V2 COMPLETE ---")
    
    # Analyze Latencies
    lat_count = len(latencies)
    gt_5s = sum(1 for l in latencies if l > 5.0)
    gt_30s = sum(1 for l in latencies if l > 30.0)
    
    print(f"Total Requests: {lat_count}")
    if lat_count > 0:
        latencies.sort()
        print(f"  Min: {latencies[0]:.3f}s")
        print(f"  Avg: {sum(latencies)/lat_count:.3f}s")
        print(f"  P95: {latencies[int(lat_count*0.95)]:.3f}s")
        print(f"  Max: {latencies[-1]:.3f}s")
        print(f"  > 5s: {gt_5s} requests")
        print(f"  > 30s: {gt_30s} requests")
        if gt_5s > 0:
            print(f"  Top 10 highest latencies: {[round(l, 3) for l in latencies[-10:]]}")
            
    print(f"\nTotal Errors: {len(errors)}")
    for e in errors:
        print(json.dumps(e, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
