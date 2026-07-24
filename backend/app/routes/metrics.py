import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.db import get_session_db, SessionRecord, TrustReportRecord, LedgerEntryRecord
from app.auth.dependencies import require_role, User

router = APIRouter()


@router.get("/")
async def get_metrics(
    db: AsyncSession = Depends(get_session_db),
    user: User = Depends(require_role("admin")),
):
    total_sessions = await db.scalar(select(func.count(SessionRecord.id)))

    outcome_rows = (
        await db.execute(
            select(SessionRecord.outcome, func.count(SessionRecord.id).label("cnt"))
            .where(SessionRecord.outcome.isnot(None))
            .group_by(SessionRecord.outcome)
        )
    ).all()
    sessions_by_outcome = {row.outcome: row.cnt for row in outcome_rows}

    tamper_alerts_fired = await db.scalar(
        select(func.count(SessionRecord.id)).where(SessionRecord.tamper_alerted_at.isnot(None))
    )

    total_ledger_entries = await db.scalar(select(func.count(LedgerEntryRecord.id)))

    reports_stmt = select(TrustReportRecord.report_json)
    reports_result = await db.execute(reports_stmt)
    violations_by_severity: dict[str, int] = {}
    for (report_str,) in reports_result:
        try:
            report_data = json.loads(report_str)
            for violation in report_data.get("violations", []):
                sev = violation.get("severity", "UNKNOWN")
                violations_by_severity[sev] = violations_by_severity.get(sev, 0) + 1
        except Exception:
            pass

    violations_by_type: dict[str, int] = {}
    reports_result = await db.execute(reports_stmt)
    for (report_str,) in reports_result:
        try:
            report_data = json.loads(report_str)
            for violation in report_data.get("violations", []):
                vtype = violation.get("violation_type", "UNKNOWN")
                violations_by_type[vtype] = violations_by_type.get(vtype, 0) + 1
        except Exception:
            pass

    return {
        "total_sessions": total_sessions or 0,
        "sessions_by_outcome": sessions_by_outcome,
        "violations_by_severity": violations_by_severity,
        "violations_by_type": violations_by_type,
        "tamper_alerts_fired": tamper_alerts_fired or 0,
        "total_ledger_entries": total_ledger_entries or 0,
    }


@router.get("/sessions-per-org")
async def get_sessions_per_org(
    db: AsyncSession = Depends(get_session_db),
    user: User = Depends(require_role("admin")),
):
    stmt = (
        select(SessionRecord.org_id, func.count(SessionRecord.id).label("session_count"))
        .group_by(SessionRecord.org_id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {"org_id": row.org_id if row.org_id else "unassigned", "session_count": row.session_count}
        for row in rows
    ]


@router.get("/tactics-frequency")
async def get_tactics_frequency(
    db: AsyncSession = Depends(get_session_db),
    user: User = Depends(require_role("admin")),
):
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
    user: User = Depends(require_role("admin")),
):
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
