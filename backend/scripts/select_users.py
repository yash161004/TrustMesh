import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine('sqlite+aiosqlite:///./trustmesh.db')
    async with engine.begin() as conn:
        result = await conn.execute(text('SELECT * FROM users'))
        rows = result.fetchall()
        for r in rows:
            print(dict(r._mapping))
        if not rows:
            print("Users table is empty.")

if __name__ == '__main__':
    asyncio.run(main())
