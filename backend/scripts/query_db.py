"""
TrustMesh Database CLI Helper

Run direct SQL audit queries against PostgreSQL (backend/.env DATABASE_URL)
Usage:
    python backend/scripts/query_db.py
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db import init_db, get_session_factory


async def run_query():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        print("\n" + "="*80)
        print("TRUSTMESH POSTGRESQL DATABASE SESSION AUDIT")
        print("="*80)
        res = await db.execute(text(
            "SELECT data_source, status, outcome, count(*) "
            "FROM negotiation_sessions "
            "GROUP BY data_source, status, outcome "
            "ORDER BY data_source;"
        ))
        rows = res.all()
        if not rows:
            print("No sessions found in database.")
        else:
            print(f"{'DATA_SOURCE':<18} | {'STATUS':<12} | {'OUTCOME':<12} | {'COUNT'}")
            print("-" * 60)
            for r in rows:
                print(f"{str(r[0]):<18} | {str(r[1]):<12} | {str(r[2]):<12} | {r[3]}")
        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_query())
