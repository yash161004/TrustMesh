import asyncio
import json
from sqlalchemy import select, func
from app.db import init_db, get_session_db, SessionRecord, TrustReportRecord
from app.session_manager import session_manager

async def main():
    await init_db()
    
    async for db in get_session_db():
        # Count of trust reports
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
                        update_reputation=False
                    )
                    print(f"  Session {s_id}: Succeeded on retry!")
                except Exception as e:
                    print(f"  Session {s_id} ERROR: {str(e)}")
                    
        # Metrics
        print("\n--- METRICS ---")
        stmt_reports = select(TrustReportRecord.report_json)
        reports = (await db.execute(stmt_reports)).scalars().all()
        
        total_score = 0.0
        count = 0
        tactic_counts = {}
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

if __name__ == "__main__":
    asyncio.run(main())
