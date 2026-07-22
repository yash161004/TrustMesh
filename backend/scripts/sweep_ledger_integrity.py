"""
TrustMesh Periodic Ledger Integrity Sweep Script.

Performs a full DB sweep across all negotiation session ledgers to detect out-of-band
database tampering or direct SQL mutations. Dispatches tamper alerts for corrupted chains.
Designed to run on a schedule (e.g. Render Cron Job).

Usage:
  python backend/scripts/sweep_ledger_integrity.py
"""
import asyncio
import logging
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.db import get_session_factory, init_db, SessionRecord
from app.db import load_ledger_entries
from app.crypto.ledger import verify_chain
from app.crypto.ledger_alerts import trigger_tamper_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ledger_sweep")


async def run_integrity_sweep() -> tuple[int, int, int]:
    """
    Scans all sessions in DB and verifies their ledger hash-chains.
    Returns (total_sessions, valid_count, tampered_count).
    """
    await init_db()
    factory = get_session_factory()

    async with factory() as session:
        res = await session.execute(select(SessionRecord.id, SessionRecord.org_id))
        rows = res.all()

    total_sessions = len(rows)
    valid_count = 0
    tampered_count = 0

    logger.info("Starting ledger integrity sweep across %d total sessions...", total_sessions)

    for session_id, org_id in rows:
        entries = await load_ledger_entries(session_id)
        if not entries:
            # Empty session or no ledger entries yet
            valid_count += 1
            continue

        is_valid, broken_at = verify_chain(entries)
        if is_valid:
            valid_count += 1
        else:
            tampered_count += 1
            logger.error("Tampered ledger detected in session %s (org_id=%s, broken_at=%s)", session_id, org_id, broken_at)
            await trigger_tamper_alert(
                session_id=session_id,
                org_id=org_id,
                broken_at=broken_at,
                reason="periodic_sweep",
            )

    logger.info(
        "Integrity sweep completed: %d total checked, %d valid, %d tampered",
        total_sessions, valid_count, tampered_count
    )
    return total_sessions, valid_count, tampered_count


def main():
    _, _, tampered_count = asyncio.run(run_integrity_sweep())
    if tampered_count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
