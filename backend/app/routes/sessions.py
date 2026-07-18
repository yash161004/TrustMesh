"""
TrustMesh Session Routes — Phase 1: Agent Logic + Phase 2: Trust Engine + Crypto Ledger + Phase 4: WebSocket

API endpoints for managing negotiation sessions between buyer and seller agents,
including trust evaluation (Phase 2), the cryptographic ledger (Phase 3),
and live WebSocket streaming (Phase 4).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel, Field

from ..auth.dependencies import get_current_user, get_current_user_ws
from ..config import get_settings
from ..crypto.ledger import verify_chain
from ..db import User, load_ledger_entries, load_trust_report, save_trust_report, get_agent_reputation, update_agent_reputation_v2
from ..limiter import limiter
from ..models import NegotiationMessage, NegotiationScenario, NegotiationSession, NegotiationSessionStatus, DEFAULT_SCENARIO
from ..session_manager import session_manager, ws_manager
from ..trust.engine import trust_engine
from ..trust.models import TrustReport

settings = get_settings()

router = APIRouter()


# --------------------------------------------------------------------------- #
# Request / Response schemas
# --------------------------------------------------------------------------- #

class CreateSessionRequest(BaseModel):
    """Request to create a new negotiation session."""
    buyer_agent_id: str = Field(default="buyer-agent-001", description="Buyer agent identifier")
    seller_agent_id: str = Field(default="seller-agent-001", description="Seller agent identifier")
    provider: str = Field(default="gemini", description="LLM provider (gemini/groq/mock)")
    initial_context: Optional[dict] = Field(default=None, description="Initial negotiation context")
    scenario: Optional[NegotiationScenario] = Field(
        default=None,
        description="Negotiation scenario (prices, product, delivery). Falls back to DEFAULT_SCENARIO.",
    )
    buyer_identity_id: Optional[str] = Field(default=None, description="Buyer identity ID")
    seller_identity_id: Optional[str] = Field(default=None, description="Seller identity ID")


class SessionResponse(BaseModel):
    """Response with session details."""
    session_id: str
    buyer_agent_id: str
    seller_agent_id: str
    buyer_identity_id: Optional[str] = None
    seller_identity_id: Optional[str] = None
    status: str
    created_at: datetime
    message_count: int


class TurnRequest(BaseModel):
    """Request to process a negotiation turn."""
    context: Optional[dict] = Field(default=None, description="Turn context")
    max_turns: int = Field(default=5, ge=1, le=20, description="Maximum turns to process")


class TurnResponse(BaseModel):
    """Response with turn results."""
    session_id: str
    status: str
    messages: list[NegotiationMessage]
    total_messages: int


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.post("", response_model=SessionResponse, summary="Create Session")
@limiter.limit(settings.rate_limit_session_create)
async def create_session(request: Request, payload: CreateSessionRequest, user: User = Depends(get_current_user)):
    """Create a new negotiation session between buyer and seller agents."""
    session = await session_manager.create_session(
        buyer_agent_id=payload.buyer_agent_id,
        seller_agent_id=payload.seller_agent_id,
        initial_context=payload.initial_context,
        provider=payload.provider,
        scenario=payload.scenario,
        buyer_identity_id=payload.buyer_identity_id,
        seller_identity_id=payload.seller_identity_id,
        user_id=user.id,
        org_id=user.org_id,
    )
    return SessionResponse(
        session_id=session.session_id,
        buyer_agent_id=session.buyer_agent_id,
        seller_agent_id=session.seller_agent_id,
        buyer_identity_id=session.buyer_identity_id,
        seller_identity_id=session.seller_identity_id,
        status=session.status.value,
        created_at=session.created_at,
        message_count=len(session.messages),
    )


@router.post("/{session_id}/start", status_code=202, summary="Start Session")
@limiter.limit(settings.rate_limit_turn)
async def start_session(
    request: Request,
    session_id: str, 
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
):
    """Start a negotiation session with the buyer's initial offer."""
    try:
        session = await session_manager.get_session(session_id)
        if session.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this session.")
            
        background_tasks.add_task(session_manager.start_session, session_id)
        return {"status": "accepted", "message": "Session start queued", "session_id": session_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/turn", status_code=202, summary="Process Turn")
@limiter.limit(settings.rate_limit_turn)
async def process_turn(
    request: Request,
    session_id: str, 
    turn_request: TurnRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
):
    """Process one or more negotiation turns."""
    try:
        session = await session_manager.get_session(session_id)
        if session.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this session.")

        background_tasks.add_task(
            session_manager.process_turn,
            session_id,
            context=turn_request.context,
            max_turns=turn_request.max_turns,
        )
        return {"status": "accepted", "message": "Turn processing queued", "session_id": session_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{session_id}", response_model=SessionResponse, summary="Get Session")
async def get_session(session_id: str, user: User = Depends(get_current_user)):
    """Get session details by ID."""
    try:
        session = await session_manager.get_session(session_id)
        if session.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this session.")
        return SessionResponse(
            session_id=session.session_id,
            buyer_agent_id=session.buyer_agent_id,
            seller_agent_id=session.seller_agent_id,
            buyer_identity_id=session.buyer_identity_id,
            seller_identity_id=session.seller_identity_id,
            status=session.status.value,
            created_at=session.created_at,
            message_count=len(session.messages),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{session_id}/messages", response_model=list[NegotiationMessage], summary="Get Messages")
async def get_messages(session_id: str, user: User = Depends(get_current_user)):
    """Get all messages for a negotiation session."""
    try:
        session = await session_manager.get_session(session_id)
        if session.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this session.")
        messages = await session_manager.get_messages(session_id)
        return messages
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=list[SessionResponse], summary="List Sessions")
async def list_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user)
):
    """List all negotiation sessions for the current organization."""
    sessions = await session_manager.list_sessions(org_id=user.org_id, limit=limit, offset=offset)
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


# --------------------------------------------------------------------------- #
# Phase 2: Trust evaluation
# --------------------------------------------------------------------------- #

@router.get(
    "/{session_id}/trust",
    response_model=TrustReport,
    summary="Evaluate Trust",
)
async def evaluate_trust(
    session_id: str,
    recompute: bool = Query(default=False, description="Force recompute even if cached"),
):
    """
    Return trust evaluation for a session.

    By default serves the pre-computed/cached result (fast).
    Pass ?recompute=true to force a fresh evaluation (slow — runs all detectors).
    """
    try:
        session = await session_manager.get_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Serve cached result unless recompute is requested
    if not recompute:
        cached = await load_trust_report(session_id)
        if cached:
            return json.loads(cached["report_json"])

    # Fetch identities to get the base reputation scores
    buyer_reputation = await get_agent_reputation(session.buyer_agent_id) if session.buyer_agent_id else None
    seller_reputation = await get_agent_reputation(session.seller_agent_id) if session.seller_agent_id else None
    
    buyer_trust = buyer_reputation["trust_score"] if buyer_reputation else 0.75
    seller_trust = seller_reputation["trust_score"] if seller_reputation else 0.75

    # Full recompute (slow — runs all detectors including LLM calls)
    scenario = session_manager.scenarios.get(session_id) or DEFAULT_SCENARIO
    report = await trust_engine.evaluate_session(
        session_id=session_id,
        messages=session.messages,
        buyer_agent_id=session.buyer_agent_id,
        seller_agent_id=session.seller_agent_id,
        scenario=scenario,
        buyer_trust_score=buyer_trust,
        seller_trust_score=seller_trust,
    )

    # Persist for future fast reads
    await save_trust_report(
        session_id=session_id,
        report_json=json.dumps(report.model_dump(mode="json")),
        evaluated_at=report.evaluated_at,
    )

    # Apply reputation update ONLY on first calculation
    if not recompute and not cached:
        if session.buyer_agent_id:
            await update_agent_reputation_v2(session.buyer_agent_id, report.buyer_score.violation_count)
        if session.seller_agent_id:
            await update_agent_reputation_v2(session.seller_agent_id, report.seller_score.violation_count)

    return report.model_dump(mode="json")


# --------------------------------------------------------------------------- #
# Phase 3: Cryptographic ledger
# --------------------------------------------------------------------------- #


class LedgerEntry(BaseModel):
    """A single entry in the hash-chained ledger."""
    id: int
    session_id: str
    sequence: int
    message_json: str
    signature: str
    signer_public_key: str
    prev_hash: str
    entry_hash: str
    created_at: datetime


class LedgerResponse(BaseModel):
    """Full ledger for a session with chain-validity flag."""
    session_id: str
    entries: list[LedgerEntry]
    chain_valid: bool
    broken_at: Optional[int] = None


@router.get(
    "/{session_id}/ledger",
    response_model=LedgerResponse,
    summary="Get Ledger",
)
async def get_ledger(session_id: str):
    """Return the full hash-chained ledger for a session with chain-validity."""
    try:
        await session_manager.get_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    raw_entries = await load_ledger_entries(session_id)
    entries = [LedgerEntry(**e) for e in raw_entries]
    chain_valid, broken_at = verify_chain(raw_entries)
    return LedgerResponse(
        session_id=session_id,
        entries=entries,
        chain_valid=chain_valid,
        broken_at=broken_at,
    )


# --------------------------------------------------------------------------- #
# Phase 4: WebSocket live stream
# --------------------------------------------------------------------------- #
from ..auth.dependencies import get_current_user, get_current_user_ws

@router.websocket("/{session_id}/ws")
async def session_websocket(
    websocket: WebSocket, 
    session_id: str,
    user: User = Depends(get_current_user_ws)
):
    """Live WebSocket stream for a negotiation session.

    On connect: sends full message history, then live updates as new
    messages are persisted.  Handles disconnects gracefully.
    """
    try:
        session = await session_manager.get_session(session_id)
        if session.user_id != user.id and user.role != "admin":
            await websocket.close(code=4003, reason="Forbidden")
            return
    except ValueError:
        await websocket.close(code=4004, reason="Session not found")
        return

    await ws_manager.connect(session_id, websocket)
    try:
        # Send existing message history on connect
        messages = await session_manager.get_messages(session_id)
        await websocket.send_json({
            "type": "history",
            "messages": [m.model_dump(mode="json") for m in messages],
        })

        # Keep connection alive; client may send pings or close
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    except Exception:
        pass
    finally:
        ws_manager.disconnect(session_id, websocket)
