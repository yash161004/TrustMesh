import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine
from app.db import Base

import os
from dotenv import load_dotenv

load_dotenv()

POSTGRES_URL = os.environ.get("STAGING_DATABASE_URL", "postgresql+asyncpg://myuser:mypassword@localhost:5432/trustmesh_staging")
if POSTGRES_URL.startswith("postgresql://"):
    POSTGRES_URL = POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

async def main():
    pg_engine = create_async_engine(POSTGRES_URL)
    
    async with pg_engine.begin() as conn:
        print("Creating all tables in Postgres...")
        await conn.run_sync(Base.metadata.create_all)
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
