import asyncio
from sqlalchemy import select, func
from app.db import init_db, get_session_factory, TrustReportRecord

async def main():
    await init_db()
    db = get_session_factory()()
    res = await db.execute(select(func.count(TrustReportRecord.session_id)))
    count = res.scalar()
    print(f"Total Trust Reports: {count}")
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
