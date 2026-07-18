import asyncio
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text, select
from app.db import Base, User, Organization, SessionRecord, MessageRecord, LedgerEntryRecord, TrustReportRecord

import os
from dotenv import load_dotenv

load_dotenv()

SQLITE_URL = "sqlite+aiosqlite:///./trustmesh.db"
POSTGRES_URL = os.environ.get("STAGING_DATABASE_URL", "postgresql+asyncpg://myuser:mypassword@localhost:5432/trustmesh_staging")
if POSTGRES_URL.startswith("postgresql://"):
    POSTGRES_URL = POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

async def count_rows(session_maker, model):
    async with session_maker() as session:
        result = await session.execute(text(f"SELECT COUNT(*) FROM {model.__tablename__}"))
        return result.scalar()

async def get_session_details(session_maker, session_id):
    async with session_maker() as session:
        msgs = (await session.execute(select(MessageRecord).where(MessageRecord.session_id == session_id).order_by(MessageRecord.turn_number))).scalars().all()
        ledgers = (await session.execute(select(LedgerEntryRecord).where(LedgerEntryRecord.session_id == session_id).order_by(LedgerEntryRecord.sequence))).scalars().all()
        flags = (await session.execute(select(TrustReportRecord).where(TrustReportRecord.session_id == session_id))).scalars().all()
        return {
            "messages": len(msgs),
            "ledgers": len(ledgers),
            "flags": len(flags)
        }

async def main():
    sqlite_engine = create_async_engine(SQLITE_URL)
    sqlite_factory = async_sessionmaker(sqlite_engine)

    pg_engine = create_async_engine(
        POSTGRES_URL, 
        connect_args={"prepared_statement_cache_size": 0} if "asyncpg" in POSTGRES_URL else {}
    )
    pg_factory = async_sessionmaker(pg_engine)

    print("--- Row Count Diff ---")
    tables = [User, Organization, SessionRecord, MessageRecord, LedgerEntryRecord, TrustReportRecord]
    
    for table in tables:
        sq_count = await count_rows(sqlite_factory, table)
        pg_count = await count_rows(pg_factory, table)
        
        expected_pg_count = sq_count
        if table.__tablename__ == 'organizations':
            expected_pg_count += 1
            
        match = "✅" if expected_pg_count == pg_count else "❌"
        print(f"{table.__tablename__:<25} | SQLite: {sq_count:<5} | Postgres: {pg_count:<5} | {match}")

    print("\n--- Spot Checks ---")
    async with sqlite_factory() as sqlite_session:
        sessions = (await sqlite_session.execute(select(SessionRecord.id))).scalars().all()
    
    if not sessions:
        print("No sessions found to spot check.")
        return

    sample_size = min(3, len(sessions))
    samples = random.sample(sessions, sample_size)
    
    for sid in samples:
        print(f"Session {sid}:")
        sq_det = await get_session_details(sqlite_factory, sid)
        pg_det = await get_session_details(pg_factory, sid)
        
        for k in sq_det.keys():
            match = "✅" if sq_det[k] == pg_det[k] else "❌"
            print(f"  {k:<10}: SQ={sq_det[k]:<3} PG={pg_det[k]:<3} {match}")

if __name__ == "__main__":
    asyncio.run(main())
