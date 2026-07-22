"""
TrustMesh DB Inspector CLI

Unified inspection utility consolidating session status counts, trust report JSON inspection,
trust report totals, system metrics/status, and user records inspection.

Usage:
    python scripts/db_inspect.py session-status
    python scripts/db_inspect.py trust-json [--limit 5]
    python scripts/db_inspect.py count-reports
    python scripts/db_inspect.py status
    python scripts/db_inspect.py users [--limit 5]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func, text
from app.db import (
    init_db,
    get_session_factory,
    get_session_db,
    SessionRecord,
    TrustReportRecord,
    User,
)
from app.session_manager import session_manager


async def cmd_session_status():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(SessionRecord.status, func.count(SessionRecord.id)).group_by(SessionRecord.status)
        )
        print("--- Session Status Counts ---")
        for row in result.all():
            print(f"Status: {row[0]}, Count: {row[1]}")


async def cmd_trust_json(limit: int = 5):
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        stmt = select(TrustReportRecord.report_json).limit(limit)
        result = await db.execute(stmt)
        print(f"--- Top {limit} Trust Reports ---")
        for row in result.scalars().all():
            print(row)
            print("-" * 40)


async def cmd_count_reports():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        res = await db.execute(select(func.count(TrustReportRecord.session_id)))
        count = res.scalar()
        print(f"Total Trust Reports: {count}")


async def cmd_status():
    await init_db()
    async for db in get_session_db():
        reports_count = await db.scalar(select(func.count(TrustReportRecord.id)))
        print(f"Total trust_reports: {reports_count}")

        stmt_failed = (
            select(SessionRecord.id)
            .where(SessionRecord.status == "COMPLETED")
            .where(~SessionRecord.id.in_(select(TrustReportRecord.session_id)))
        )
        failed_session_ids = (await db.execute(stmt_failed)).scalars().all()
        print(f"Succeeded: {reports_count}")
        print(f"Failed: {len(failed_session_ids)}")

        if failed_session_ids:
            print("\nFailures Breakdown:")
            for s_id in failed_session_ids:
                try:
                    await session_manager.evaluate_trust_for_session(
                        session_id=s_id,
                        recompute=False,
                        update_reputation=False,
                    )
                    print(f"  Session {s_id}: Succeeded on retry!")
                except Exception as e:
                    print(f"  Session {s_id} ERROR: {str(e)}")

        print("\n--- METRICS ---")
        stmt_reports = select(TrustReportRecord.report_json)
        reports = (await db.execute(stmt_reports)).scalars().all()

        total_score = 0.0
        count = 0
        tactic_counts: dict[str, int] = {}
        for r_str in reports:
            try:
                r_data = json.loads(r_str)
                buyer_score = r_data.get("buyer_score", {}).get("overall_score")
                seller_score = r_data.get("seller_score", {}).get("overall_score")
                if buyer_score is not None:
                    total_score += float(buyer_score)
                    count += 1
                if seller_score is not None:
                    total_score += float(seller_score)
                    count += 1

                for violation in r_data.get("violations", []):
                    name = violation.get("violation_type", "UNKNOWN")
                    tactic_counts[name] = tactic_counts.get(name, 0) + 1
            except Exception:
                pass

        avg_score = total_score / count if count > 0 else 0.0
        print(f"Average Trust Score: {avg_score}")
        print("Tactics Frequency:")
        for name, freq in tactic_counts.items():
            print(f"  {name}: {freq}")
        break


async def cmd_users(limit: int = 5):
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        users = await db.execute(select(User).limit(limit))
        rows = users.scalars().all()
        print(f"--- Users (Limit {limit}) ---")
        for u in rows:
            print(f"ID: {u.id}, Clerk ID: {u.clerk_user_id}, Role: {u.role}, Org ID: {u.org_id}")
        if not rows:
            print("No users found.")


def main():
    parser = argparse.ArgumentParser(description="TrustMesh DB Inspector CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    subparsers.add_parser("session-status", help="Count sessions grouped by status")
    
    t_parser = subparsers.add_parser("trust-json", help="Print trust report JSON payloads")
    t_parser.add_argument("--limit", type=int, default=5, help="Number of records to show")

    subparsers.add_parser("count-reports", help="Print total count of trust reports")
    subparsers.add_parser("status", help="Print full trust system status breakdown")
    
    u_parser = subparsers.add_parser("users", help="List user records")
    u_parser.add_argument("--limit", type=int, default=5, help="Number of users to show")

    args = parser.parse_args()

    if args.subcommand == "session-status":
        asyncio.run(cmd_session_status())
    elif args.subcommand == "trust-json":
        asyncio.run(cmd_trust_json(args.limit))
    elif args.subcommand == "count-reports":
        asyncio.run(cmd_count_reports())
    elif args.subcommand == "status":
        asyncio.run(cmd_status())
    elif args.subcommand == "users":
        asyncio.run(cmd_users(args.limit))


if __name__ == "__main__":
    main()
