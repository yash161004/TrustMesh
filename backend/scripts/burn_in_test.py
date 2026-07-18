import asyncio
import aiohttp
import time
import random
from datetime import datetime

API_BASE = "http://127.0.0.1:8001/api/v1"
DURATION_SECONDS = 30 * 60  # 30 minutes

stats = {
    "requests": 0,
    "errors": 0,
    "latencies": [],
    "ledger_checks": 0,
    "ledger_failures": 0,
    "sessions_created": 0,
    "error_types": {}
}

async def hit_read_sessions(session):
    start = time.time()
    try:
        async with session.get(f"{API_BASE}/sessions") as resp:
            resp.raise_for_status()
            stats["latencies"].append(time.time() - start)
            stats["requests"] += 1
            data = await resp.json()
            return data
    except Exception as e:
        record_error(e)
        return []

async def hit_read_session_details(session, session_id):
    start = time.time()
    try:
        async with session.get(f"{API_BASE}/sessions/{session_id}") as resp:
            resp.raise_for_status()
            stats["latencies"].append(time.time() - start)
            stats["requests"] += 1
    except Exception as e:
        record_error(e)

async def check_ledger(session, session_id):
    start = time.time()
    try:
        async with session.get(f"{API_BASE}/sessions/{session_id}/ledger") as resp:
            resp.raise_for_status()
            stats["latencies"].append(time.time() - start)
            stats["requests"] += 1
            data = await resp.json()
            stats["ledger_checks"] += 1
            if not data.get("is_chain_valid", False):
                stats["ledger_failures"] += 1
    except Exception as e:
        record_error(e)

async def run_write_path(session):
    # 1. Create a session
    start = time.time()
    try:
        payload = {
            "buyer_agent_id": f"buyer-{random.randint(100, 999)}",
            "seller_agent_id": f"seller-{random.randint(100, 999)}",
            "provider": "mock"
        }
        async with session.post(f"{API_BASE}/sessions", json=payload) as resp:
            resp.raise_for_status()
            stats["latencies"].append(time.time() - start)
            stats["requests"] += 1
            data = await resp.json()
            session_id = data["session_id"]
            stats["sessions_created"] += 1
            
            # 2. Run a couple of turns to generate messages and ledger entries
            for _ in range(2):
                turn_start = time.time()
                async with session.post(f"{API_BASE}/sessions/{session_id}/turn", json={"max_turns": 1}) as t_resp:
                    t_resp.raise_for_status()
                    stats["latencies"].append(time.time() - turn_start)
                    stats["requests"] += 1
                    
            # 3. Verify ledger for this new session
            await check_ledger(session, session_id)
            
    except Exception as e:
        record_error(e)

def record_error(e):
    stats["errors"] += 1
    err_type = type(e).__name__
    stats["error_types"][err_type] = stats["error_types"].get(err_type, 0) + 1

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
            
        # Small random sleep to simulate real traffic pacing and prevent completely overwhelming localhost
        await asyncio.sleep(random.uniform(0.1, 0.5))

async def main():
    print(f"Starting burn-in test for {DURATION_SECONDS} seconds...")
    end_time = time.time() + DURATION_SECONDS
    
    # Run 10 concurrent workers
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(worker(session, end_time, i)) for i in range(10)]
        await asyncio.gather(*tasks)
        
    print("\n--- BURN-IN TEST COMPLETE ---")
    print(f"Total Requests: {stats['requests']}")
    print(f"Total Errors: {stats['errors']}")
    for err, count in stats["error_types"].items():
        print(f"  - {err}: {count}")
        
    print(f"\nSessions Created: {stats['sessions_created']}")
    print(f"Ledger Validations: {stats['ledger_checks']}")
    print(f"Ledger Failures: {stats['ledger_failures']}")
    
    if stats["latencies"]:
        latencies = sorted(stats["latencies"])
        print(f"\nLatencies:")
        print(f"  Min: {latencies[0]:.3f}s")
        print(f"  Max: {latencies[-1]:.3f}s")
        print(f"  Avg: {sum(latencies)/len(latencies):.3f}s")
        print(f"  P95: {latencies[int(len(latencies)*0.95)]:.3f}s")

if __name__ == "__main__":
    asyncio.run(main())
