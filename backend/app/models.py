"""
TrustMesh Pydantic Models — Phase 0: Foundation

Defines the core negotiation message schema shared across all agents
and the trust engine.  These models will be extended in later phases
to carry cryptographic signatures and trust scores.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class MessageType(str, Enum):
    """All valid negotiation message types."""
    OFFER = "OFFER"
    COUNTER_OFFER = "COUNTER_OFFER"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    COMMITMENT = "COMMITMENT"


class AgentRole(str, Enum):
    """High-level roles an agent can occupy in a negotiation session."""
    BUYER = "BUYER"
    SELLER = "SELLER"
    OBSERVER = "OBSERVER"  # e.g., the trust engine itself


# ---------------------------------------------------------------------------
# Core negotiation message schema
# ---------------------------------------------------------------------------

class NegotiationMessage(BaseModel):
    """
    A single turn in a B2B negotiation between two LLM agents.

    Required fields
    ---------------
    message_type : MessageType
        Semantic intent of this turn.
    sender : str
        Unique identifier of the agent sending the message
        (e.g. "buyer-agent-001").
    price : float
        Proposed unit price in the negotiated currency.
    quantity : int
        Number of units under negotiation.
    delivery_terms : str
        Free-text delivery / SLA specification
        (e.g. "Net-30, FOB destination").
    timestamp : datetime
        UTC timestamp of message creation.
    turn_number : int
        Monotonically increasing counter within the session (starts at 1).

    Optional fields (populated by later phases)
    -------------------------------------------
    session_id : str | None
        UUID of the parent NegotiationSession.
    notes : str | None
        Free-text rationale or human-readable annotation.
    signature : str | None
        Base64-encoded Ed25519 signature over canonical message bytes
        (Phase 3+).
    """

    message_type: MessageType = Field(
        ...,
        description="Semantic intent of this negotiation turn.",
    )
    sender: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique agent identifier.",
    )
    price: float = Field(
        ...,
        ge=0.0,
        description="Proposed unit price (must be non-negative).",
    )
    quantity: int = Field(
        ...,
        ge=1,
        description="Number of units (must be at least 1).",
    )
    delivery_terms: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Delivery / SLA specification.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of message creation.",
    )
    turn_number: int = Field(
        ...,
        ge=1,
        description="Monotonically increasing turn counter within the session.",
    )

    # Optional fields reserved for later phases
    session_id: Optional[str] = Field(
        default=None,
        description="UUID of the parent NegotiationSession (Phase 1+).",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=2048,
        description="Free-text rationale or annotation.",
    )
    signature: Optional[str] = Field(
        default=None,
        description="Base64-encoded Ed25519 signature (Phase 3+).",
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ensure_utc(cls, v: datetime) -> datetime:
        """Attach UTC timezone if the datetime is naive."""
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "message_type": "OFFER",
                "sender": "buyer-agent-001",
                "price": 149.99,
                "quantity": 500,
                "delivery_terms": "Net-30, FOB destination",
                "timestamp": "2026-07-14T07:00:00Z",
                "turn_number": 1,
                "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "notes": "Initial offer based on market survey.",
            }
        }
    }


# ---------------------------------------------------------------------------
# Session-level model (stub — expanded in Phase 1)
# ---------------------------------------------------------------------------

class NegotiationSessionStatus(str, Enum):
    """Lifecycle states for a negotiation session."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class NegotiationSession(BaseModel):
    """
    Stub model representing a full negotiation session.
    Will be fleshed out in Phase 1 when agent logic is introduced.
    """
    session_id: str = Field(..., description="UUID v4 session identifier.")
    buyer_agent_id: str = Field(..., description="Unique ID of the buyer agent.")
    seller_agent_id: str = Field(..., description="Unique ID of the seller agent.")
    status: NegotiationSessionStatus = NegotiationSessionStatus.PENDING
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    messages: list[NegotiationMessage] = Field(
        default_factory=list,
        description="Ordered list of all messages in this session.",
    )

    model_config = {"json_schema_extra": {"example": {
        "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "buyer_agent_id": "buyer-agent-001",
        "seller_agent_id": "seller-agent-001",
        "status": "PENDING",
    }}}
