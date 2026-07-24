import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db import Base
import app.db

@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    app.db._async_engine = engine
    app.db._async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    app.db._db_initialised = True
    
    from app.session_manager import session_manager
    session_manager.reset()
    session_manager._initialised = True
    
    yield
    session_manager.reset()
    await engine.dispose()

@pytest.fixture
def test_client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
