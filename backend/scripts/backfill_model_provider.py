"""
TrustMesh — Backfill model_provider for existing database session records.

Fixes mislabeled rows in PostgreSQL/SQLite:
- NVIDIA-run sessions (c7b5018c, 716dc391, 4ade32c5, ece72c2c) -> model_provider = 'nvidia'
- All other real LLM sessions (groq runs prior to task-852) -> model_provider = 'groq'
- Mock/synthetic runs -> model_provider = 'mock'
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update, text
from app.db import init_db, get_session_factory, SessionRecord

NVIDIA_SESSION_IDS = {
    "c7b5018c-e71f-49e7-b07e-67f24d10b36c",
    "716dc391-3407-4bd4-9c5a-34864e190169",
    "4ade32c5-e5ec-40ec-a9fb-61e84ef7b4e9",
    "ece72c2c-74ae-4bbb-a73c-33857d44cc5f",
}

async def backfill():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        # 1. Update explicit NVIDIA session IDs
        for sid in NVIDIA_SESSION_IDS:
            await db.execute(
                update(SessionRecord)
                .where(SessionRecord.id == sid)
                .values(model_provider="nvidia")
            )
        
        # 2. Update remaining real LLM sessions (data_source starting with real_llm) to groq
        await db.execute(
            update(SessionRecord)
            .where(SessionRecord.data_source.like("real_llm%"))
            .where(SessionRecord.id.not_in(NVIDIA_SESSION_IDS))
            .values(model_provider="groq")
        )

        # 3. Update synthetic/mock sessions
        await db.execute(
            update(SessionRecord)
            .where(
                (SessionRecord.data_source == "mock") |
                (SessionRecord.data_source == "synthetic") |
                (SessionRecord.data_source.is_(None))
            )
            .values(model_provider="mock")
        )

        await db.commit()
        print("Successfully backfilled model_provider across all session records.")

        # Print summary report
        res = await db.execute(text("SELECT model_provider, COUNT(*) FROM negotiation_sessions GROUP BY model_provider;"))
        rows = res.fetchall()
        print("\nUpdated model_provider breakdown:")
        for provider, count in rows:
            print(f"  {provider}: {count} sessions")

if __name__ == "__main__":
    asyncio.run(backfill())
