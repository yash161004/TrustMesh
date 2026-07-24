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
    from app.limiter import limiter
    session_manager.reset()
    session_manager._initialised = True
    try:
        limiter.reset()
    except Exception:
        pass
    
    yield
    session_manager.reset()
    try:
        limiter.reset()
    except Exception:
        pass
    await engine.dispose()

@pytest.fixture(autouse=True)
def _isolate_filesystem_state(tmp_path):
    """Isolate per-test filesystem state (agent cards, signing keys, key caches).

    Each test gets its own agent_cards/ and .keys/ directories so that
    agent cards and Ed25519 keypairs written by one test cannot leak
    into another.  Also clears the in-memory keypair cache.
    """
    from app.identity import agent_card as ac_mod
    from app.crypto import signing as sig_mod

    cards_dir = tmp_path / "agent_cards"
    keys_dir = tmp_path / ".keys"
    cards_dir.mkdir(parents=True, exist_ok=True)
    keys_dir.mkdir(parents=True, exist_ok=True)

    old_cards_dir = ac_mod.CARDS_DIR
    old_keys_dir = sig_mod._KEYS_DIR
    old_keypairs = sig_mod._keypairs

    ac_mod.CARDS_DIR = cards_dir
    sig_mod._KEYS_DIR = keys_dir
    sig_mod._keypairs = {}

    yield

    ac_mod.CARDS_DIR = old_cards_dir
    sig_mod._KEYS_DIR = old_keys_dir
    sig_mod._keypairs = old_keypairs

@pytest.fixture
def test_client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
