"""Unit tests for async DB URL scheme normalization (Render/Heroku Postgres safety)."""
from app.db import _normalize_async_db_url


def test_sqlite_gets_aiosqlite_driver():
    assert _normalize_async_db_url("sqlite:///./trustmesh.db") == "sqlite+aiosqlite:///./trustmesh.db"


def test_postgresql_scheme_gets_asyncpg():
    assert _normalize_async_db_url("postgresql://u:p@host:5432/db") == "postgresql+asyncpg://u:p@host:5432/db"


def test_bare_postgres_scheme_gets_asyncpg():
    # Render/Heroku connectionString emits the bare `postgres://` form.
    assert _normalize_async_db_url("postgres://u:p@host:5432/db") == "postgresql+asyncpg://u:p@host:5432/db"


def test_already_async_url_untouched():
    url = "postgresql+asyncpg://u:p@host:5432/db"
    assert _normalize_async_db_url(url) == url


def test_already_aiosqlite_untouched():
    url = "sqlite+aiosqlite:///./trustmesh.db"
    assert _normalize_async_db_url(url) == url
