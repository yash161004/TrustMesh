"""
TrustMesh — Backfill model_provider for existing database session records. (FIXED)

This replaces backend/scripts/backfill_model_provider.py (commit ebb8768).

Bug in the original: the "mock" clause only matched
  data_source IN ('mock', 'synthetic', NULL)
but the legacy DB migration default was `data_source VARCHAR(36) DEFAULT 'real'`
(see backend/app/db.py line 235). That means every row carrying the literal
string data_source='real' — the 694-row legacy bucket already confirmed in
commit 0625dd2 to be mislabeled synthetic seed data — was silently skipped by
the original script and left with whatever model_provider it had before.

This version handles that bucket explicitly, tags it unambiguously, and prints
a per-data_source breakdown so the output can be diffed against what gets
reported back, instead of trusting a single collapsed summary number.
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
        # 1. Explicit NVIDIA session IDs
        for sid in NVIDIA_SESSION_IDS:
            await db.execute(
                update(SessionRecord)
                .where(SessionRecord.id == sid)
                .values(model_provider="nvidia")
            )

        # 2. Real LLM sessions (real_llm_v4/v5/v6) not already tagged NVIDIA -> groq
        await db.execute(
            update(SessionRecord)
            .where(SessionRecord.data_source.like("real_llm%"))
            .where(SessionRecord.id.not_in(NVIDIA_SESSION_IDS))
            .values(model_provider="groq")
        )

        # 3. Explicit synthetic/mock rows -> mock
        await db.execute(
            update(SessionRecord)
            .where(
                (SessionRecord.data_source == "mock")
                | (SessionRecord.data_source == "synthetic")
                | (SessionRecord.data_source.is_(None))
            )
            .values(model_provider="mock")
        )

        # 4. THE FIX: legacy rows with data_source == 'real' (the old DDL default).
        # These are the previously-mislabeled-synthetic bucket from 0625dd2.
        # Tag distinctly as 'legacy_unverified' — NOT 'gemini', NOT 'mock' —
        # so nothing downstream mistakes this for either real gemini-negotiated
        # data or genuinely mock data. This bucket stays excluded from training
        # regardless of this label; the point is making the label honest.
        await db.execute(
            update(SessionRecord)
            .where(SessionRecord.data_source == "real")
            .values(model_provider="legacy_unverified")
        )

        await db.commit()
        print("Backfill complete.\n")

        # Per-data_source breakdown, not just a collapsed model_provider count —
        # this is the number that actually needs to be checked against reports.
        res = await db.execute(
            text(
                """
                SELECT data_source, model_provider, COUNT(*)
                FROM negotiation_sessions
                GROUP BY data_source, model_provider
                ORDER BY data_source, model_provider;
                """
            )
        )
        rows = res.fetchall()
        print("data_source | model_provider | count")
        print("-" * 45)
        for data_source, provider, count in rows:
            print(f"{data_source!s:15} {provider!s:16} {count}")


if __name__ == "__main__":
    asyncio.run(backfill())
