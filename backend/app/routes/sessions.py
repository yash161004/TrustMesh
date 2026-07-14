"""
TrustMesh Session Routes — Phase 1: Agent Logic

API endpoints for managing negotiation sessions between buyer and seller agents.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..models import NegotiationMessage, NegotiationSession, NegotiationSessionStatus
from ..session_manager import session_manager

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
