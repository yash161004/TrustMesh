from fastapi import APIRouter, Depends, Query
from ..auth.dependencies import require_role
from ..db import User
from ..session_manager import session_manager
from .sessions import SessionResponse

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/sessions", response_model=list[SessionResponse], summary="List All Sessions (Admin)")
async def list_all_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_role("admin"))
):
    """List all negotiation sessions across all organizations. (Admin only)"""
    # Passing org_id=None to fetch all sessions
    sessions = await session_manager.list_sessions(org_id=None, limit=limit, offset=offset)
    return [
        SessionResponse(
            session_id=s.session_id,
            buyer_agent_id=s.buyer_agent_id,
            seller_agent_id=s.seller_agent_id,
            buyer_identity_id=s.buyer_identity_id,
            seller_identity_id=s.seller_identity_id,
            status=s.status.value,
            created_at=s.created_at,
            message_count=len(s.messages),
        )
        for s in sessions
    ]
