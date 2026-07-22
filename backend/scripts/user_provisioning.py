"""
TrustMesh User Provisioning CLI

Consolidated user provisioning utility for seeding system, admin, and test users.

Usage:
    python scripts/user_provisioning.py insert-system
    python scripts/user_provisioning.py insert-user --email user@example.com --role admin --org-id org_123
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db import init_db, get_session_factory, User


async def cmd_insert_system():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        user = await db.scalar(select(User).where(User.id == "system-user-000"))
        if not user:
            user = User(
                id="system-user-000",
                clerk_user_id="system-clerk-000",
                email="system@trustmesh.test",
                role="admin",
                org_id="system-org-000",
            )
            db.add(user)
            await db.commit()
            print("System user 'system-user-000' inserted.")
        else:
            print("System user 'system-user-000' already exists.")


async def cmd_insert_user(email: str, role: str, org_id: str | None, user_id: str | None, clerk_id: str | None):
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        uid = user_id or f"user-{os.urandom(4).hex()}"
        cid = clerk_id or f"clerk-{os.urandom(4).hex()}"
        user = User(
            id=uid,
            clerk_user_id=cid,
            email=email,
            role=role,
            org_id=org_id,
        )
        db.add(user)
        await db.commit()
        print(f"Inserted user {uid} ({email}) with role '{role}' under org '{org_id}'.")


def main():
    parser = argparse.ArgumentParser(description="TrustMesh User Provisioning CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    subparsers.add_parser("insert-system", help="Insert default system user")

    u_parser = subparsers.add_parser("insert-user", help="Insert a new user")
    u_parser.add_argument("--email", required=True, help="User email address")
    u_parser.add_argument("--role", default="member", help="User role (admin, member)")
    u_parser.add_argument("--org-id", default=None, help="Organization ID")
    u_parser.add_argument("--user-id", default=None, help="Custom User ID")
    u_parser.add_argument("--clerk-id", default=None, help="Custom Clerk User ID")

    args = parser.parse_args()

    if args.subcommand == "insert-system":
        asyncio.run(cmd_insert_system())
    elif args.subcommand == "insert-user":
        asyncio.run(cmd_insert_user(args.email, args.role, args.org_id, args.user_id, args.clerk_id))


if __name__ == "__main__":
    main()
