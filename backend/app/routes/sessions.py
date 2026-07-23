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
    if not user.org_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: You must belong to an organization to create a session.")
        
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


@router.post("/load-demo", summary="Load Demo Data")
async def load_demo_data(user: User = Depends(get_current_user)):
    """Generates fresh demo sessions assigned to the current user by cloning seed data."""
    import uuid
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from ..db import _async_session_factory, SessionRecord, MessageRecord, LedgerEntryRecord, TrustReportRecord
    
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    async with _async_session_factory() as db:
        # Find the demo sessions (those with org_id IS NULL)
        result = await db.execute(
            select(SessionRecord)
            .where(SessionRecord.org_id == None)
            .options(selectinload(SessionRecord.messages))
        )
        demo_sessions = result.scalars().all()
        
        for old_s in demo_sessions:
            new_id = str(uuid.uuid4())
            new_s = SessionRecord(
                id=new_id,
                user_id=user.id,
                org_id=user.org_id,
                buyer_agent_id=old_s.buyer_agent_id,
                seller_agent_id=old_s.seller_agent_id,
                buyer_identity_id=old_s.buyer_identity_id,
                seller_identity_id=old_s.seller_identity_id,
                status=old_s.status,
                created_at=old_s.created_at,
                final_price=old_s.final_price,
                outcome=old_s.outcome,
                scenario_json=old_s.scenario_json,
            )
            db.add(new_s)
            
            for old_m in old_s.messages:
                new_m = MessageRecord(
                    session_id=new_id,
                    message_type=old_m.message_type,
                    sender=old_m.sender,
                    price=old_m.price,
                    quantity=old_m.quantity,
                    delivery_terms=old_m.delivery_terms,
                    timestamp=old_m.timestamp,
                    turn_number=old_m.turn_number,
                    notes=old_m.notes,
                    signer_public_key=old_m.signer_public_key,
                )
                db.add(new_m)
                
            tr_result = await db.execute(select(TrustReportRecord).where(TrustReportRecord.session_id == old_s.id))
            old_tr = tr_result.scalar_one_or_none()
            if old_tr:
                new_tr = TrustReportRecord(
                    session_id=new_id,
                    evaluated_at=old_tr.evaluated_at,
                    report_json=old_tr.report_json,
                    created_at=old_tr.created_at,
                )
                db.add(new_tr)
                
            le_result = await db.execute(select(LedgerEntryRecord).where(LedgerEntryRecord.session_id == old_s.id))
            for old_le in le_result.scalars().all():
                new_le = LedgerEntryRecord(
                    session_id=new_id,
                    sequence=old_le.sequence,
                    message_json=old_le.message_json,
                    signature=old_le.signature,
                    signer_public_key=old_le.signer_public_key,
                    prev_hash=old_le.prev_hash,
                    entry_hash=old_le.entry_hash,
                    created_at=old_le.created_at,
                )
                db.add(new_le)
                
        await db.commit()
    return {"status": "success"}


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
        if user.role != "admin" and (not session.org_id or not user.org_id or session.org_id != user.org_id):
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
        if user.role != "admin" and (not session.org_id or not user.org_id or session.org_id != user.org_id):
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
        if user.role != "admin" and (not session.org_id or not user.org_id or session.org_id != user.org_id):
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


@router.get("/{session_id}/export", summary="Export Session PDF")
@limiter.limit(settings.rate_limit_turn)
async def export_session_pdf(
    request: Request,
    session_id: str,
    user: User = Depends(get_current_user)
):
    """Export a PDF report of the negotiation session."""
    from fastapi.responses import Response
    try:
        session = await session_manager.get_session(session_id)
        if user.role != "admin" and (not session.org_id or not user.org_id or session.org_id != user.org_id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this session.")
        
        messages = await session_manager.get_messages(session_id)
        try:
            report = await session_manager.evaluate_trust_for_session(session_id)
            trust_dict = report.model_dump()
        except Exception:
            trust_dict = {}

        raw_entries = await load_ledger_entries(session_id)
        chain_valid, broken_at = verify_chain(raw_entries)
        
        ledger_dict = {
            "chain_valid": chain_valid,
            "entries": [e for e in raw_entries]
        }
        
        from ..pdf_generator import generate_session_pdf
        pdf_bytes = generate_session_pdf(
            session_id=session_id,
            session=session.model_dump(),
            messages=[m.model_dump() for m in messages],
            trust_report=trust_dict,
            ledger=ledger_dict
        )
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="session_{session_id}.pdf"'
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{session_id}/messages", response_model=list[NegotiationMessage], summary="Get Messages")
async def get_messages(session_id: str, user: User = Depends(get_current_user)):
    """Get all messages for a negotiation session."""
    try:
        session = await session_manager.get_session(session_id)
        if user.role != "admin" and (not session.org_id or not user.org_id or session.org_id != user.org_id):
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
    user: User = Depends(get_current_user)
):
    """
    Return trust evaluation for a session.

    By default serves the pre-computed/cached result (fast).
    Pass ?recompute=true to force a fresh evaluation (slow — runs all detectors).
    """
    try:
        # Check if session exists
        session = await session_manager.get_session(session_id)
        if user.role != "admin" and (not session.org_id or not user.org_id or session.org_id != user.org_id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this session.")
        
        # Calling evaluate_trust_for_session with update_reputation=True so that
        # if a client manually polls it first before it completes, reputation is updated once.
        report = await session_manager.evaluate_trust_for_session(
            session_id, 
            recompute=recompute, 
            update_reputation=True
        )
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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
async def get_ledger(
    session_id: str,
    user: User = Depends(get_current_user)
):
    """Return the full hash-chained ledger for a session with chain-validity."""
    try:
        session = await session_manager.get_session(session_id)
        if user.role != "admin" and (not session.org_id or not user.org_id or session.org_id != user.org_id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this session.")
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
# Deal outcome prediction (Tier 1 #1 — classical ML on session history)
# --------------------------------------------------------------------------- #

class DealPredictionResponse(BaseModel):
    """P(deal closes) for a session's current state, from the model trained
    by scripts/train_deal_outcome_model.py. model_available=False (with the
    other fields null) means no model has been trained yet -- this is the
    expected state until someone runs the training script with enough
    labeled session history, not an error."""
    session_id: str
    model_available: bool
    p_deal: Optional[float] = None
    model_name: Optional[str] = None
    trained_at: Optional[str] = None


@router.get(
    "/{session_id}/prediction",
    response_model=DealPredictionResponse,
    summary="Predict Deal Outcome",
)
async def predict_session_outcome(session_id: str, user: User = Depends(get_current_user)):
    """
    Score a session's current state with the deal-outcome model.

    Uses only the cached trust report (never triggers a fresh LLM
    evaluation), so this stays a fast, cheap read safe to poll from a
    dashboard. If no model has been trained yet, returns
    model_available=False rather than an error -- callers should hide the
    prediction UI in that case, not surface a failure state.
    """
    from ..ml.predict import predict_deal_probability, model_available
    from ..db import load_trust_report as _load_trust_report_raw

    try:
        session = await session_manager.get_session(session_id)
        if user.role != "admin" and (not session.org_id or not user.org_id or session.org_id != user.org_id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this session.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not model_available():
        return DealPredictionResponse(session_id=session_id, model_available=False)

    scenario = session_manager.scenarios.get(session_id, DEFAULT_SCENARIO).model_dump(mode="json")

    messages = await session_manager.get_messages(session_id)
    message_dicts = [m.model_dump(mode="json") for m in messages]

    cached = await _load_trust_report_raw(session_id)
    trust_report = None
    if cached and cached.get("report_json"):
        try:
            trust_report = json.loads(cached["report_json"])
        except (TypeError, ValueError):
            trust_report = None

    result = predict_deal_probability(scenario, message_dicts, trust_report)
    if result is None:
        return DealPredictionResponse(session_id=session_id, model_available=False)

    return DealPredictionResponse(
        session_id=session_id,
        model_available=True,
        p_deal=result["p_deal"],
        model_name=result["model_name"],
        trained_at=result["trained_at"],
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
        if user.role != "admin" and (not session.org_id or not user.org_id or session.org_id != user.org_id):
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
