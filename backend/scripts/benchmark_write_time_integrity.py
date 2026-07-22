"""
Benchmark script measuring write-time ledger integrity check overhead.
Measures DB read latency (load_ledger_entries) and verify_chain compute time
at various sequence lengths (N = 1, 10, 25, 50, 100).
"""
import asyncio
import time
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import init_db, save_session, save_ledger_entry, load_ledger_entries
from app.crypto.ledger import build_entry, verify_chain, _GENESIS_HASH

SAMPLE_MSG = {
    "message_type": "OFFER",
    "sender": "buyer-agent-001",
    "price": 149.99,
    "quantity": 500,
    "delivery_terms": "Net-30, FOB destination",
    "turn_number": 1,
}

async def benchmark():
    await init_db()
    session_id = "benchmark-latency-session"
    now = datetime.now(timezone.utc)
    
    await save_session(
        session_id=session_id,
        user_id="bench-user",
        org_id="bench-org",
        buyer_agent_id="buyer-1",
        seller_agent_id="seller-1",
        status="ACTIVE",
        created_at=now,
    )
    
    prev_hash = _GENESIS_HASH
    sequence_milestones = [1, 10, 25, 50, 100]
    
    print("=" * 65)
    print(f"{'Sequence (N)':<15} | {'DB Load (ms)':<15} | {'Verify Chain (ms)':<18} | {'Total (ms)':<10}")
    print("=" * 65)
    
    for seq in range(1, 101):
        msg = {**SAMPLE_MSG, "turn_number": seq}
        entry = build_entry(msg, f"sig_{seq}", f"pub_{seq}", prev_hash, seq, now, session_id=session_id)
        await save_ledger_entry(**entry)
        prev_hash = entry["entry_hash"]
        
        if seq in sequence_milestones:
            # Benchmark load_ledger_entries
            t0 = time.perf_counter()
            entries = await load_ledger_entries(session_id)
            t1 = time.perf_counter()
            db_load_ms = (t1 - t0) * 1000.0
            
            # Benchmark verify_chain
            t2 = time.perf_counter()
            is_valid, _ = verify_chain(entries)
            t3 = time.perf_counter()
            verify_ms = (t3 - t2) * 1000.0
            
            total_ms = db_load_ms + verify_ms
            print(f"{seq:<15} | {db_load_ms:<15.3f} | {verify_ms:<18.3f} | {total_ms:<10.3f}")
            
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(benchmark())
