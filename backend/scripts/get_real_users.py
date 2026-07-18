import asyncio
from sqlalchemy import select
from app.db import init_db, get_session_factory, User

async def main():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        users = await db.execute(select(User).limit(5))
        for u in users.scalars().all():
            print(f"ID: {u.id}, Clerk ID: {u.clerk_user_id}, Role: {u.role}")

if __name__ == "__main__":
    asyncio.run(main())
