import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
import uuid

async def main():
    engine = create_async_engine('sqlite+aiosqlite:///./trustmesh.db')
    factory = async_sessionmaker(engine)
    async with factory() as session:
        # Create a valid UUID for the test user
        user_id = str(uuid.uuid4())
        await session.execute(text(f"INSERT INTO users (id, clerk_user_id, email, role, created_at) VALUES ('{user_id}', 'user_3Gf0cxkWBKxARLHOWFJ0BUvo8aD', 'rathodyashraj73@gmail.com', 'standard', '2026-07-18 00:00:00')"))
        await session.commit()
    print("Test user manually inserted into SQLite!")

if __name__ == '__main__':
    asyncio.run(main())
