"""
TrustMesh DB Admin CLI

Unified admin utility for database administration task management:
clearing users, assigning admin roles, resyncing PostgreSQL sequences, and initializing Postgres schemas.

Usage:
    python scripts/db_admin.py clear-users
    python scripts/db_admin.py make-admin [--clerk-user-id <id>]
    python scripts/db_admin.py resync-sequences
    python scripts/db_admin.py init-schema [--url <postgres_url>]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db import init_db, get_session_factory, User, Base


async def cmd_clear_users():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        await db.execute(text("DELETE FROM users"))
        await db.commit()
    print("Users table cleared successfully.")


async def cmd_make_admin(clerk_user_id: str):
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(update(User).where(User.clerk_user_id == clerk_user_id).values(role="admin"))
        await db.commit()
        print(f"Updated user '{clerk_user_id}' role to admin (rows affected: {result.rowcount}).")


async def cmd_resync_sequences():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable is missing.")
        sys.exit(1)

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    print("Connecting to Postgres to resync sequences...")
    engine = create_async_engine(database_url, echo=False)

    tables_with_sequences = ["negotiation_messages", "ledger_entries", "trust_reports"]
    uuid_tables = ["negotiation_sessions", "users", "organizations"]

    async with engine.begin() as conn:
        for table in tables_with_sequences:
            seq_name = f"{table}_id_seq"
            print(f"Syncing sequence {seq_name} for table {table}...")
            query = f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table}), 1))"
            try:
                res = await conn.execute(text(query))
                new_val = res.scalar()
                print(f"  -> Success. Sequence {seq_name} synced to {new_val}.")
            except Exception as e:
                print(f"  -> Error syncing {seq_name}: {e}")

        for table in uuid_tables:
            print(f"Skipping table {table} (Uses UUID primary keys).")

    await engine.dispose()
    print("Resync complete.")


async def cmd_init_schema(pg_url: str | None = None):
    url = pg_url or os.environ.get("STAGING_DATABASE_URL", "postgresql+asyncpg://myuser:mypassword@localhost:5432/trustmesh_staging")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    print(f"Initializing schema on target DB...")
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Schema initialization complete!")


def main():
    parser = argparse.ArgumentParser(description="TrustMesh DB Admin CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    subparsers.add_parser("clear-users", help="Clear all records from users table")

    ma_parser = subparsers.add_parser("make-admin", help="Assign admin role to a user")
    ma_parser.add_argument("--clerk-user-id", default="owner-user-id", help="Clerk user ID to promote")

    subparsers.add_parser("resync-sequences", help="Resync PostgreSQL sequence counters")

    schema_parser = subparsers.add_parser("init-schema", help="Initialize database schema tables")
    schema_parser.add_argument("--url", default=None, help="Postgres database URL")

    args = parser.parse_args()

    if args.subcommand == "clear-users":
        asyncio.run(cmd_clear_users())
    elif args.subcommand == "make-admin":
        asyncio.run(cmd_make_admin(args.clerk_user_id))
    elif args.subcommand == "resync-sequences":
        asyncio.run(cmd_resync_sequences())
    elif args.subcommand == "init-schema":
        asyncio.run(cmd_init_schema(args.url))


if __name__ == "__main__":
    main()
