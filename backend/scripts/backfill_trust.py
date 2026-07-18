import asyncio
import logging
from sqlalchemy import select
from app.db import init_db, get_session_factory, SessionRecord, TrustReportRecord
from app.session_manager import session_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    await init_db()
    factory = get_session_factory()
    
    async with factory() as db:
        # Find all COMPLETED sessions that do NOT have a TrustReportRecord
        # Using a subquery or outer join
        stmt = (
            select(SessionRecord.id)
            .where(SessionRecord.status == "COMPLETED")
            .where(
                ~SessionRecord.id.in_(
                    select(TrustReportRecord.session_id)
                )
            )
        )
        result = await db.execute(stmt)
        session_ids = [row[0] for row in result.all()]
        
    total = len(session_ids)
    logger.info(f"Found {total} COMPLETED sessions missing trust reports.")
    
    success_count = 0
    fail_count = 0
    
    for idx, session_id in enumerate(session_ids, start=1):
        logger.info(f"Processing session {idx}/{total}: {session_id}")
        try:
            # evaluate_trust_for_session with update_reputation=False
            await session_manager.evaluate_trust_for_session(
                session_id=session_id,
                recompute=False,
                update_reputation=False
            )
            success_count += 1
            
            # Wait 1 second to avoid rate limits on LLM detectors (e.g. ManipulationDetector)
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Failed to backfill session {session_id}: {e}")
            fail_count += 1
            if "All API calls failed" in str(e) or "RateLimit" in str(e):
                logger.warning("Rate limits hit globally across providers. Sleeping for 60 seconds before continuing...")
                await asyncio.sleep(60)

    logger.info(f"Backfill complete! Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    asyncio.run(main())
