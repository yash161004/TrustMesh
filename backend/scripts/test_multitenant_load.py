import asyncio
import httpx
import hashlib
import logging
import sys
from fastapi import Request, HTTPException

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Import the FastAPI app
from app.main import app
from app.auth.dependencies import get_current_user, User
from app.db import get_session_db

# Mock dependency that reads org_id from the Bearer token
async def mock_get_current_user(request: Request) -> User:
    auth = request.headers.get("Authorization", "")
    prefix = "Bearer test-user-"
    if auth.startswith(prefix):
        org_id = auth[len(prefix):]
        user = User(id=f"test-user-{org_id}", clerk_user_id=f"clerk_{org_id}", email=f"user@{org_id}.test", role="standard", org_id=org_id)
        return user
    raise HTTPException(status_code=401, detail="Missing or invalid token")

# Apply global overrides
from app.auth.dependencies import get_current_user as auth_get_user
from app.routes.sessions import get_current_user as sessions_get_user

app.dependency_overrides[auth_get_user] = mock_get_current_user
app.dependency_overrides[sessions_get_user] = mock_get_current_user

from app.limiter import limiter
limiter.enabled = False

# Mock Trust Engine to avoid LLM rate limits during load testing
from app.trust.engine import trust_engine
from app.trust.models import TrustReport, TrustScore
async def mock_evaluate_session(*args, **kwargs):
    from datetime import datetime, timezone
    return TrustReport(
        session_id=kwargs.get("session_id", "test"),
        buyer_score=TrustScore(agent_id="buyer", overall_score=90.0, violation_count=0),
        seller_score=TrustScore(agent_id="seller", overall_score=90.0, violation_count=0),
        evaluated_at=datetime.now(timezone.utc)
    )
trust_engine.evaluate_session = mock_evaluate_session

import os

ORGS_ENV = os.environ.get("LOAD_TEST_ORGS")
if ORGS_ENV:
    ORGS = [o.strip() for o in ORGS_ENV.split(",") if o.strip()]
else:
    ORGS = ["orgA", "orgB", "orgC"]

SESSIONS_PER_ORG = int(os.environ.get("LOAD_TEST_SESSIONS_PER_ORG", "5"))
CONCURRENCY_LIMIT = int(os.environ.get("LOAD_TEST_CONCURRENCY", "10"))

async def run_session(client: httpx.AsyncClient, org_id: str, session_index: int) -> dict:
    headers = {"Authorization": f"Bearer test-user-{org_id}"}
    
    # 1. Create Session with mock provider to avoid LLM rate limits
    create_payload = {
        "buyer_agent_id": f"buyer-{session_index}",
        "seller_agent_id": f"seller-{session_index}",
        "provider": "mock",
        "context": {"product": "Enterprise Software", "volume": "100 licenses"}
    }
    resp = await client.post(f"{BASE_URL}/sessions", json=create_payload, headers=headers)
    resp.raise_for_status()
    session_id = resp.json()["session_id"]
    
    # 2. Trigger a single Turn Request which will process up to 4 turns in the background
    turn_payload = {
        "max_turns": 4,
        "context": {"priority": "speed"}
    }
    resp = await client.post(f"{BASE_URL}/sessions/{session_id}/turn", json=turn_payload, headers=headers)
    resp.raise_for_status()
    
    logging.info(f"[{org_id}] Triggered turn for session {session_id}")
    return {"session_id": session_id, "org_id": org_id}

async def verify_ledger(client: httpx.AsyncClient, session_info: dict):
    session_id = session_info["session_id"]
    org_id = session_info["org_id"]
    headers = {"Authorization": f"Bearer test-user-{org_id}"}
    
    ledger_entries = []
    ledger_data = {}
    for _ in range(20):
        resp = await client.get(f"{BASE_URL}/sessions/{session_id}/ledger", headers=headers)
        resp.raise_for_status()
        ledger_data = resp.json()
        ledger_entries = ledger_data.get("entries", [])
        if len(ledger_entries) > 0:
            break
        await asyncio.sleep(0.5)
        
    chain_valid = ledger_data.get("chain_valid", False)
    
    if len(ledger_entries) == 0:
        logging.error(f"[{org_id}] Expected ledger entries, got 0 for {session_id}")
        return False

    # Use the server-side chain verification (verify_chain in crypto/ledger.py)
    if not chain_valid:
        broken_at = ledger_data.get("broken_at")
        logging.error(f"[{org_id}] Ledger chain invalid for {session_id}, broken at entry {broken_at}")
        return False
        
    logging.info(f"[{org_id}] Ledger verified: chain_valid=True, {len(ledger_entries)} entries for {session_id}")
    return True

async def check_isolation(client: httpx.AsyncClient, session_info: dict):
    session_id = session_info["session_id"]
    owner_org = session_info["org_id"]
    
    # Try to access with a different org's token
    other_org = "orgA" if owner_org != "orgA" else "orgB"
    bad_headers = {"Authorization": f"Bearer test-user-{other_org}"}
    
    resp = await client.get(f"{BASE_URL}/sessions/{session_id}", headers=bad_headers)
    if resp.status_code != 403:
        logging.error(f"Isolation failure! {other_org} accessed session {session_id} owned by {owner_org}")
        return False
        
    return True

async def run_session_limited(client: httpx.AsyncClient, org_id: str, session_index: int, sem: asyncio.Semaphore) -> dict:
    async with sem:
        return await run_session(client, org_id, session_index)

BASE_URL = "http://test/api/v1"

async def main():
    # Insert dummy users into the database
    from app.db import init_db, Organization, User
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy import select
    await init_db()
    async for db in get_session_db():
        for org in ORGS:
            try:
                # Check if org exists
                result = await db.execute(select(Organization).where(Organization.id == org))
                if not result.scalar_one_or_none():
                    new_org = Organization(id=org, clerk_org_id=f"clerk_org_{org}", name=f"Org {org}", plan_tier="test")
                    db.add(new_org)
                    await db.commit()
                
                user_id = f"test-user-{org}"
                result = await db.execute(select(User).where(User.id == user_id))
                if not result.scalar_one_or_none():
                    new_user = User(id=user_id, clerk_user_id=f"clerk_{org}", email=f"user@{org}.test", role="standard", org_id=org)
                    db.add(new_user)
                    await db.commit()
            except IntegrityError as e:
                await db.rollback()
                logging.error(f"Failed to insert org/user {org}: {e}")
        break

    transport = httpx.ASGITransport(app=app)
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as client:
        # Create all sessions concurrently
        tasks = []
        for org in ORGS:
            for i in range(SESSIONS_PER_ORG):
                tasks.append(run_session_limited(client, org, i, sem))
                
        logging.info(f"Starting {len(tasks)} concurrent sessions across {len(ORGS)} organizations...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        sessions = []
        for r in results:
            if isinstance(r, Exception):
                logging.error(f"Session failed: {r}")
            else:
                sessions.append(r)
                
        if len(sessions) != len(ORGS) * SESSIONS_PER_ORG:
            logging.error("Not all sessions completed successfully.")
            sys.exit(1)
            
        logging.info(f"Successfully finished {len(sessions)} session creations/turn requests. Waiting 5s for background turn completion...")
        await asyncio.sleep(5)
        
        # Verify Ledgers serially to avoid overwhelming connection pool during reads
        logging.info("Verifying ledger integrity...")
        ledger_results = []
        for s in sessions:
            res = await verify_ledger(client, s)
            ledger_results.append(res)
            
        if not all(ledger_results):
            logging.error("Ledger validation failed for one or more sessions.")
            sys.exit(1)
            
        # Verify Tenant Isolation serially
        logging.info("Verifying cross-tenant isolation...")
        iso_results = []
        for s in sessions:
            res = await check_isolation(client, s)
            iso_results.append(res)
            
        if not all(iso_results):
            logging.error("Tenant isolation validation failed.")
            sys.exit(1)
            
        logging.info("All Multi-Tenant Load Tests Passed!")

if __name__ == "__main__":
    asyncio.run(main())
