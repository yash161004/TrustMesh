import os
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.db import User, get_db_url

async def main():
    engine = create_async_engine(get_db_url(), echo=False)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as db:
        user = await db.scalar(select(User).where(User.id == "system-user-000"))
        if not user:
            user = User(
                id="system-user-000",
                clerk_user_id="system-clerk-000",
                email="system@trustmesh.test",
                role="admin",
                org_id="system-org-000"
            )
            db.add(user)
            await db.commit()
            print("Dummy user inserted.")
        else:
            print("Dummy user already exists.")

if __name__ == "__main__":
    asyncio.run(main())
