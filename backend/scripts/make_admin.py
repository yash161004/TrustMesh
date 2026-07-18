import asyncio
from sqlalchemy import select, update
from app.db import init_db, get_session_factory, User

async def main():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        await db.execute(update(User).where(User.clerk_user_id == 'owner-user-id').values(role='admin'))
        await db.commit()
        print("Updated owner-user-id to admin")

if __name__ == "__main__":
    asyncio.run(main())
