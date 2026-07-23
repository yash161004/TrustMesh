import asyncio
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from app.db import init_db, get_session_factory, SessionRecord, MessageRecord

# 3bed26c timestamp: Thu Jul 23 11:32:57 2026 +0530 -> 2026-07-23 06:02:57 UTC
FIX_TIMESTAMP = datetime(2026, 7, 23, 6, 2, 57, tzinfo=timezone.utc)


async def inspect_failures():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        res = await db.execute(
            select(SessionRecord)
            .where(SessionRecord.data_source.like("real_llm_v6%"))
            .order_by(SessionRecord.created_at.asc())
        )
        records = res.scalars().all()

        print(f"Commit 3bed26c timestamp (UTC): {FIX_TIMESTAMP.isoformat()}\n")
        print(f"{'Session ID':38} | {'Provider':8} | {'Status':9} | {'Outcome':9} | {'Created At (UTC)':25} | {'Fix Window':10}")
        print("-" * 115)

        pre_fix_failures = 0
        post_fix_failures = 0
        pre_fix_completed = 0
        post_fix_completed = 0

        post_fix_failure_details = []

        for r in records:
            created_at = r.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            is_post_fix = created_at >= FIX_TIMESTAMP
            window_str = "POST-FIX" if is_post_fix else "PRE-FIX"

            print(f"{r.id:38} | {str(r.model_provider):8} | {r.status:9} | {str(r.outcome):9} | {created_at.isoformat():25} | {window_str:10}")

            if r.status == "FAILED":
                if is_post_fix:
                    post_fix_failures += 1
                    # Load messages to find reason for failure
                    msg_res = await db.execute(
                        select(MessageRecord)
                        .where(MessageRecord.session_id == r.id)
                        .order_by(MessageRecord.turn_number.desc())
                    )
                    last_msg = msg_res.scalars().first()
                    post_fix_failure_details.append((r.id, r.model_provider, created_at, last_msg.notes if last_msg else "No messages"))
                else:
                    pre_fix_failures += 1
            elif r.status == "COMPLETED":
                if is_post_fix:
                    post_fix_completed += 1
                else:
                    pre_fix_completed += 1

        print("-" * 115)
        print("\n=== SUMMARY BREAKDOWN ===")
        print(f"PRE-FIX  (before 3bed26c @ {FIX_TIMESTAMP.isoformat()}):")
        print(f"  Completed: {pre_fix_completed}")
        print(f"  Failed:    {pre_fix_failures}")
        print(f"POST-FIX (after 3bed26c @ {FIX_TIMESTAMP.isoformat()}):")
        print(f"  Completed: {post_fix_completed}")
        print(f"  Failed:    {post_fix_failures}")

        if post_fix_failure_details:
            print("\n=== POST-FIX FAILURE DETAILS ===")
            for sid, provider, cat, notes in post_fix_failure_details:
                print(f"ID: {sid} | Provider: {provider} | Time: {cat.isoformat()} | Notes/Error: {notes}")
        else:
            print("\n=== POST-FIX FAILURE DETAILS ===")
            print("ZERO failures occurred after commit 3bed26c!")


if __name__ == "__main__":
    asyncio.run(inspect_failures())
