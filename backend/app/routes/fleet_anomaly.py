from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.dependencies import get_current_user, User
from app.db import get_session_db, SessionRecord, AgentReputationRecord

router = APIRouter()

Z_SCORE_THRESHOLD = 2.0


@router.get("/anomalies")
async def get_fleet_anomalies(
    db: AsyncSession = Depends(get_session_db),
    user: User = Depends(get_current_user),
):
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Forbidden: User does not belong to an organization.")

    buyer_stmt = select(SessionRecord.buyer_agent_id).where(SessionRecord.org_id == user.org_id)
    seller_stmt = select(SessionRecord.seller_agent_id).where(SessionRecord.org_id == user.org_id)
    combined = buyer_stmt.union(seller_stmt)
    result = await db.execute(combined)
    agent_ids = [row[0] for row in result.all()]

    if not agent_ids:
        return {"agents": [], "note": None}

    rep_stmt = select(AgentReputationRecord).where(AgentReputationRecord.agent_id.in_(agent_ids))
    rep_result = await db.execute(rep_stmt)
    rep_map = {r.agent_id: r for r in rep_result.scalars().all()}

    agent_stats = []
    for agent_id in agent_ids:
        rep = rep_map.get(agent_id)
        if rep:
            total_sessions = rep.total_sessions
            violations_count = rep.violations_count
            trust_score = rep.trust_score
        else:
            total_sessions = 0
            violations_count = 0
            trust_score = None
        violation_rate = violations_count / total_sessions if total_sessions > 0 else 0.0
        agent_stats.append({
            "agent_id": agent_id,
            "total_sessions": total_sessions,
            "violations_count": violations_count,
            "violation_rate": round(violation_rate, 4),
            "average_trust_score": trust_score,
            "z_score": None,
            "is_anomalous": None,
        })

    rates = [a["violation_rate"] for a in agent_stats]
    n = len(rates)
    note = None

    if n >= 3:
        mean = sum(rates) / n
        variance = sum((r - mean) ** 2 for r in rates) / n
        stddev = variance ** 0.5
        for stat in agent_stats:
            if stddev > 0:
                z = (stat["violation_rate"] - mean) / stddev
                stat["z_score"] = round(z, 4)
                stat["is_anomalous"] = abs(z) > Z_SCORE_THRESHOLD
            else:
                stat["z_score"] = 0.0
                stat["is_anomalous"] = False
    else:
        note = "Insufficient agents for meaningful z-score computation (need >= 3)."

    return {"agents": agent_stats, "note": note}
