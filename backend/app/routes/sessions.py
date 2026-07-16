"""
TrustMesh Session Routes — Phase 1: Agent Logic + Phase 2: Trust Engine + Crypto Ledger + Phase 4: WebSocket

API endpoints for managing negotiation sessions between buyer and seller agents,
including trust evaluation (Phase 2), the cryptographic ledger (Phase 3),
and live WebSocket streaming (Phase 4).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..crypto.ledger import verify_chain
from ..db import load_ledger_entries
from ..models import NegotiationMessage, NegotiationScenario, NegotiationSession, NegotiationSessionStatus, DEFAULT_SCENARIO
from ..session_manager import session_manager, ws_manager
from ..trust.engine import trust_engine
from ..trust.models import TrustReport

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


class SessionResponse(BaseModel):
    """Response with session details."""
    session_id: str
    buyer_agent_id: str
    seller_agent_id: str
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
async def create_session(request: CreateSessionRequest):
    """Create a new negotiation session between buyer and seller agents."""
    session = await session_manager.create_session(
        buyer_agent_id=request.buyer_agent_id,
        seller_agent_id=request.seller_agent_id,
        initial_context=request.initial_context,
        provider=request.provider,
        scenario=request.scenario,
    )
    return SessionResponse(
        session_id=session.session_id,
        buyer_agent_id=session.buyer_agent_id,
        seller_agent_id=session.seller_agent_id,
        status=session.status.value,
        created_at=session.created_at,
        message_count=len(session.messages),
    )


@router.post("/{session_id}/start", response_model=NegotiationMessage, summary="Start Session")
async def start_session(session_id: str):
    """Start a negotiation session with the buyer's initial offer."""
    try:
        message = await session_manager.start_session(session_id)
        return message
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/turn", response_model=TurnResponse, summary="Process Turn")
async def process_turn(session_id: str, request: TurnRequest):
    """Process one or more negotiation turns."""
    try:
        messages = await session_manager.process_turn(
            session_id,
            context=request.context,
            max_turns=request.max_turns,
        )
        session = await session_manager.get_session(session_id)
        return TurnResponse(
            session_id=session_id,
            status=session.status.value,
            messages=messages,
            total_messages=len(session.messages),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{session_id}", response_model=SessionResponse, summary="Get Session")
async def get_session(session_id: str):
    """Get session details by ID."""
    try:
        session = await session_manager.get_session(session_id)
        return SessionResponse(
            session_id=session.session_id,
            buyer_agent_id=session.buyer_agent_id,
            seller_agent_id=session.seller_agent_id,
            status=session.status.value,
            created_at=session.created_at,
            message_count=len(session.messages),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{session_id}/messages", response_model=list[NegotiationMessage], summary="Get Messages")
async def get_messages(session_id: str):
    """Get all messages for a negotiation session."""
    try:
        messages = await session_manager.get_messages(session_id)
        return messages
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=list[SessionResponse], summary="List Sessions")
async def list_sessions():
    """List all negotiation sessions."""
    sessions = await session_manager.list_sessions()
    return [
        SessionResponse(
            session_id=s.session_id,
            buyer_agent_id=s.buyer_agent_id,
            seller_agent_id=s.seller_agent_id,
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
async def evaluate_trust(session_id: str):
    """
    Run the full trust evaluation on a completed negotiation session.
    """
    try:
        session = await session_manager.get_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    scenario = session_manager.scenarios.get(session_id) or DEFAULT_SCENARIO
    report = trust_engine.evaluate_session(
        session_id=session_id,
        messages=session.messages,
        buyer_agent_id=session.buyer_agent_id,
        seller_agent_id=session.seller_agent_id,
        scenario=scenario,
    )
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


@router.websocket("/{session_id}/ws")
async def session_websocket(websocket: WebSocket, session_id: str):
    """Live WebSocket stream for a negotiation session.

    On connect: sends full message history, then live updates as new
    messages are persisted.  Handles disconnects gracefully.
    """
    try:
        await session_manager.get_session(session_id)
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
