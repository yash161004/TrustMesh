import asyncio
import os
import sys
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db import init_db, get_session_factory, SessionRecord, MessageRecord


async def check_test_batch():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        res = await db.execute(
            select(SessionRecord)
            .where(SessionRecord.data_source == "real_llm_v6_test")
            .order_by(SessionRecord.created_at.asc())
        )
        records = res.scalars().all()

        print(f"Found {len(records)} test sessions:\n")
        print(f"{'Session ID':38} | {'Status':10} | {'Outcome':10} | {'Turns':5} | {'Created At':25}")
        print("-" * 95)
        for r in records:
            msg_res = await db.execute(
                select(MessageRecord).where(MessageRecord.session_id == r.id)
            )
            msgs = msg_res.scalars().all()
            print(f"{r.id:38} | {r.status:10} | {str(r.outcome):10} | {len(msgs):5} | {str(r.created_at):25}")


if __name__ == "__main__":
    asyncio.run(check_test_batch())
