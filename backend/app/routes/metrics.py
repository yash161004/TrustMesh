import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db import get_session_db, SessionRecord, TrustReportRecord
from app.auth.dependencies import require_role, User

router = APIRouter()

@router.get("/sessions-per-org")
async def get_sessions_per_org(
    db: AsyncSession = Depends(get_session_db),
    user: User = Depends(require_role("admin"))
):
    """
    Returns the count of negotiation sessions per organization.
    Admin only.
    """
    stmt = (
        select(SessionRecord.org_id, func.count(SessionRecord.id).label("session_count"))
        .group_by(SessionRecord.org_id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    # Handle None org_id for system/unassigned sessions
    return [
        {"org_id": row.org_id if row.org_id else "unassigned", "session_count": row.session_count}
        for row in rows
    ]

@router.get("/tactics-frequency")
async def get_tactics_frequency(
    db: AsyncSession = Depends(get_session_db),
    user: User = Depends(require_role("admin"))
):
    """
    Returns the frequency of each manipulation tactic/violation detected.
    Admin only. Computes by parsing TrustReportRecord JSON in-memory for MVP.
    """
    stmt = select(TrustReportRecord.report_json)
    result = await db.execute(stmt)
    reports = result.scalars().all()
    
    tactic_counts = {}
    for report_str in reports:
        try:
            report_data = json.loads(report_str)
            for violation in report_data.get("violations", []):
                name = violation.get("violation_type", "UNKNOWN")
                tactic_counts[name] = tactic_counts.get(name, 0) + 1
        except Exception:
            pass
            
    return [
        {"tactic_name": name, "frequency": count}
        for name, count in tactic_counts.items()
    ]

@router.get("/average-trust")
async def get_average_trust(
    db: AsyncSession = Depends(get_session_db),
    user: User = Depends(require_role("admin"))
):
    """
    Returns the average trust score across all sessions.
    Admin only. Computes by parsing TrustReportRecord JSON in-memory for MVP.
    """
    stmt = select(TrustReportRecord.report_json)
    result = await db.execute(stmt)
    reports = result.scalars().all()
    
    total_score = 0.0
    count = 0
    for report_str in reports:
        try:
            report_data = json.loads(report_str)
            buyer_score = report_data.get("buyer_score", {}).get("overall_score")
            seller_score = report_data.get("seller_score", {}).get("overall_score")
            
            if buyer_score is not None:
                total_score += float(buyer_score)
                count += 1
            if seller_score is not None:
                total_score += float(seller_score)
                count += 1
        except Exception:
            pass
            
    avg_score = total_score / count if count > 0 else 0.0
    return {"average_trust_score": avg_score}
