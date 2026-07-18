import asyncio
from sqlalchemy import select, func
from app.db import init_db, get_session_factory, SessionRecord

async def main():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        # Group sessions by status
        result = await db.execute(select(SessionRecord.status, func.count(SessionRecord.id)).group_by(SessionRecord.status))
        for row in result.all():
            print(f"Status: {row[0]}, Count: {row[1]}")

if __name__ == "__main__":
    asyncio.run(main())
