import asyncio
from sqlalchemy import select
from app.db import init_db, get_session_factory, User
from datetime import datetime, timezone
import uuid

async def main():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        admin_user = await db.execute(select(User).where(User.clerk_user_id == "system-clerk-000"))
        if not admin_user.scalar_one_or_none():
            db.add(User(
                id="system-user-000",
                clerk_user_id="system-clerk-000",
                email="admin@test.com",
                role="admin",
                org_id="system-org-000",
                created_at=datetime.now(timezone.utc)
            ))
        
        reg_user = await db.execute(select(User).where(User.clerk_user_id == "user_123_clerk"))
        if not reg_user.scalar_one_or_none():
            db.add(User(
                id=str(uuid.uuid4()),
                clerk_user_id="user_123_clerk",
                email="user@test.com",
                role="user",
                org_id="system-org-000",
                created_at=datetime.now(timezone.utc)
            ))
        
        await db.commit()

if __name__ == "__main__":
    asyncio.run(main())
