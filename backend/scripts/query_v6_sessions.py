import asyncio
import json
import os
import sys
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db import init_db, get_session_factory, SessionRecord

async def run():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        res = await db.execute(
            select(SessionRecord)
            .where(SessionRecord.data_source == "real_llm_v6")
            .order_by(SessionRecord.created_at.desc())
        )
        records = res.scalars().all()
        out = [
            {
                "session_id": r.id,
                "data_source": r.data_source,
                "status": r.status,
                "outcome": r.outcome,
                "final_price": r.final_price,
                "created_at": str(r.created_at),
            }
            for r in records
        ]
        print(json.dumps(out, indent=2))

if __name__ == "__main__":
    asyncio.run(run())
