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


async def breakdown():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        res = await db.execute(
            text(
                """
                SELECT data_source, status, outcome, model_provider, COUNT(*)
                FROM negotiation_sessions
                WHERE data_source LIKE 'real_llm%'
                GROUP BY data_source, status, outcome, model_provider
                ORDER BY data_source, status, outcome;
                """
            )
        )
        rows = res.fetchall()
        print("data_source     | status      | outcome    | model_provider | count")
        print("-" * 65)
        total_real = 0
        usable_real = 0
        for ds, status, outcome, provider, count in rows:
            print(f"{str(ds):15} | {str(status):11} | {str(outcome):10} | {str(provider):14} | {count}")
            total_real += count
            if status == "COMPLETED" or outcome in ("DEAL", "NO_DEAL", "MAX_TURNS"):
                usable_real += count

        print("-" * 65)
        print(f"Total real_llm sessions: {total_real}")
        print(f"Usable for training (completed / non-failed): {usable_real}")


if __name__ == "__main__":
    asyncio.run(breakdown())
