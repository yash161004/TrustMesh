import asyncio
from sqlalchemy import select
from app.db import init_db, get_session_factory, TrustReportRecord
import json

async def main():
    await init_db()
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(TrustReportRecord.report_json).limit(5)
        result = await session.execute(stmt)
        for row in result.scalars().all():
            print(row)
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
