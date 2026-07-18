import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

async def main():
    engine = create_async_engine('sqlite+aiosqlite:///./trustmesh.db')
    factory = async_sessionmaker(engine)
    async with factory() as session:
        await session.execute(text("DELETE FROM users"))
        await session.commit()
    print("Users cleared!")

if __name__ == '__main__':
    asyncio.run(main())
