import asyncio
import uuid
import sys
import os

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

async def main():
    sqlite_engine = create_async_engine(SQLITE_URL)
    sqlite_factory = async_sessionmaker(sqlite_engine)

    pg_engine = create_async_engine(
        POSTGRES_URL, 
        connect_args={"prepared_statement_cache_size": 0} if "asyncpg" in POSTGRES_URL else {}
    )
    pg_factory = async_sessionmaker(pg_engine)

    # Note: We assume the Postgres schema is already created by Alembic upgrade head
    
    print("Reading from SQLite...")
    async with sqlite_factory() as sqlite_session:
        # Load all data
        users = (await sqlite_session.execute(select(User))).scalars().all()
        orgs = (await sqlite_session.execute(select(Organization))).scalars().all()
        sessions = (await sqlite_session.execute(select(SessionRecord))).scalars().all()
        messages = (await sqlite_session.execute(select(MessageRecord))).scalars().all()
        ledger_entries = (await sqlite_session.execute(select(LedgerEntryRecord))).scalars().all()
        flags = (await sqlite_session.execute(select(TrustReportRecord))).scalars().all()

    print(f"Loaded from SQLite:")
    print(f"Users: {len(users)}")
    print(f"Orgs: {len(orgs)}")
    print(f"Sessions: {len(sessions)}")
    print(f"Messages: {len(messages)}")
    print(f"Ledger Entries: {len(ledger_entries)}")
    print(f"Flags: {len(flags)}")

    print("Writing to Postgres...")
    async with pg_factory() as pg_session:
        # Clear existing
        await pg_session.execute(text("TRUNCATE trust_reports, ledger_entries, negotiation_messages, negotiation_sessions, users, organizations CASCADE"))
        
        # Insert Orgs
        for org in orgs:
            pg_session.add(Organization(**{c.name: getattr(org, c.name) for c in Organization.__table__.columns}))
        
        # Create System Org if not exists
        system_org = await pg_session.execute(select(Organization).where(Organization.name == "system"))
        system_org = system_org.scalar_one_or_none()
        
        if not system_org:
            system_org_id = str(uuid.uuid4())
            system_org = Organization(id=system_org_id, clerk_org_id="system_org", name="system", plan_tier="system")
            pg_session.add(system_org)
            await pg_session.flush()

        # Insert Users
        for user in users:
            pg_session.add(User(**{c.name: getattr(user, c.name) for c in User.__table__.columns}))
        await pg_session.flush()

        # Insert Sessions
        for session in sessions:
            session_dict = {c.name: getattr(session, c.name) for c in SessionRecord.__table__.columns}
            if session_dict['org_id'] is None:
                session_dict['org_id'] = system_org.id
            pg_session.add(SessionRecord(**session_dict))
            
        await pg_session.flush()
            
        # Insert Messages
        for msg in messages:
            pg_session.add(MessageRecord(**{c.name: getattr(msg, c.name) for c in MessageRecord.__table__.columns}))
        await pg_session.flush()
            
        # Insert Ledger Entries
        for entry in ledger_entries:
            pg_session.add(LedgerEntryRecord(**{c.name: getattr(entry, c.name) for c in LedgerEntryRecord.__table__.columns}))
        await pg_session.flush()
            
        # Insert Flags
        for flag in flags:
            pg_session.add(TrustReportRecord(**{c.name: getattr(flag, c.name) for c in TrustReportRecord.__table__.columns}))
            
        await pg_session.commit()
    print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(main())
