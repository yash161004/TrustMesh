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

from pydantic import BaseModel, Field, field_validator, model_validator, computed_field


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


class AgentIdentity(BaseModel):
    """Persistent agent identity and reputation data."""
    id: str = Field(..., description="Unique identifier (UUID or stable string).")
    role: AgentRole = Field(..., description="Primary role of this agent.")
    name: str = Field(..., description="Human-readable name.")
    reputation_score: float = Field(default=100.0, description="Current trust reputation (0-100).")
    session_count: int = Field(default=0, description="Total completed sessions.")
    created_at: datetime
    updated_at: datetime


class AgentReputation(BaseModel):
    """Cross-session reputation layer for an agent."""
    agent_id: str = Field(..., description="Unique agent identifier.")
    trust_score: float = Field(default=0.75, ge=0.0, le=1.0, description="Current trust score (0.0 - 1.0).")
    total_sessions: int = Field(default=0, description="Total number of sessions evaluated.")
    violations_count: int = Field(default=0, description="Total number of trust violations across all sessions.")
    last_updated: datetime


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
    proposed_items: list["ProposedItem"] = Field(
        ...,
        min_length=1,
        description="List of proposed items (SKUs) and their pricing/quantities.",
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
    signer_public_key: Optional[str] = Field(
        default=None,
        description="Base64-encoded Ed25519 public key of the signer.",
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
                "proposed_items": [
                    {
                        "sku": "ITEM-001",
                        "price": 149.99,
                        "quantity": 500
                    }
                ],
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
    user_id: Optional[str] = Field(default=None, description="Owner user ID.")
    org_id: Optional[str] = Field(default=None, description="Owner organization ID.")
    buyer_agent_id: str = Field(..., description="Unique ID of the buyer agent.")
    seller_agent_id: str = Field(..., description="Unique ID of the seller agent.")
    buyer_identity_id: Optional[str] = Field(default=None, description="Persistent buyer identity.")
    seller_identity_id: Optional[str] = Field(default=None, description="Persistent seller identity.")
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


# ---------------------------------------------------------------------------
# Negotiation Scenario — dynamic input data (Phase 1 refactor)
# ---------------------------------------------------------------------------

class LineItem(BaseModel):
    sku: str = Field(..., description="Unique SKU identifier")
    product_name: str = Field(..., description="Product or service being negotiated")
    quantity: int = Field(..., ge=1, description="Number of units under negotiation")
    unit: str = Field(..., description="Unit of measurement, e.g. units, kg, cases")
    market_reference_price: float = Field(..., gt=0, description="Prevailing market price per unit")
    buyer_target_price: float = Field(..., gt=0, description="Buyer's ideal / target price per unit (secret)")
    buyer_budget_cap: float = Field(..., gt=0, description="Buyer's absolute maximum per unit (secret)")
    seller_asking_price: float = Field(..., gt=0, description="Seller's initial asking price per unit")
    seller_floor_price: float = Field(..., gt=0, description="Seller's absolute minimum per unit (secret)")

class NonPriceTerm(BaseModel):
    term_type: str = Field(..., description="E.g., payment_terms, sla, penalty_clause")
    description: str = Field(..., description="Full text description of the term")
    negotiable: bool = Field(default=True, description="Whether this term is negotiable")

    name: str = Field(..., description="Human-readable name.")
    reputation_score: float = Field(default=100.0, description="Current trust reputation (0-100).")
    session_count: int = Field(default=0, description="Total completed sessions.")
    created_at: datetime
    updated_at: datetime


class AgentReputation(BaseModel):
    """Cross-session reputation layer for an agent."""
    agent_id: str = Field(..., description="Unique agent identifier.")
    trust_score: float = Field(default=0.75, ge=0.0, le=1.0, description="Current trust score (0.0 - 1.0).")
    total_sessions: int = Field(default=0, description="Total number of sessions evaluated.")
    violations_count: int = Field(default=0, description="Total number of trust violations across all sessions.")
    last_updated: datetime


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
    proposed_items: list["ProposedItem"] = Field(
        ...,
        min_length=1,
        description="List of proposed items (SKUs) and their pricing/quantities.",
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
    signer_public_key: Optional[str] = Field(
        default=None,
        description="Base64-encoded Ed25519 public key of the signer.",
    )

    @property
    def price(self) -> float:
        if self.proposed_items:
            return self.proposed_items[0].price
        return 0.0

    @property
    def quantity(self) -> int:
        if self.proposed_items:
            return self.proposed_items[0].quantity
        return 0

    @computed_field
    @property
    def price(self) -> float:
        return self.proposed_items[0].price if self.proposed_items else 0.0

    @computed_field
    @property
    def quantity(self) -> int:
        return self.proposed_items[0].quantity if self.proposed_items else 1

    @model_validator(mode="before")
    @classmethod
    def _convert_legacy_price_quantity(cls, data: any) -> any:
        if isinstance(data, dict):
            if not data.get("proposed_items"):
                price = data.get("price")
                quantity = data.get("quantity", 1)
                sku = data.get("sku", "SKU-001")
                if price is not None:
                    data["proposed_items"] = [{
                        "sku": sku,
                        "price": float(price),
                        "quantity": int(quantity),
                    }]
        return data

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
                "proposed_items": [
                    {
                        "sku": "ITEM-001",
                        "price": 149.99,
                        "quantity": 500
                    }
                ],
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
    user_id: Optional[str] = Field(default=None, description="Owner user ID.")
    org_id: Optional[str] = Field(default=None, description="Owner organization ID.")
    buyer_agent_id: str = Field(..., description="Unique ID of the buyer agent.")
    seller_agent_id: str = Field(..., description="Unique ID of the seller agent.")
    buyer_identity_id: Optional[str] = Field(default=None, description="Persistent buyer identity.")
    seller_identity_id: Optional[str] = Field(default=None, description="Persistent seller identity.")
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


# ---------------------------------------------------------------------------
# Negotiation Scenario — dynamic input data (Phase 1 refactor)
# ---------------------------------------------------------------------------

class LineItem(BaseModel):
    sku: str = Field(..., description="Unique SKU identifier")
    product_name: str = Field(..., description="Product or service being negotiated")
    quantity: int = Field(..., ge=1, description="Number of units under negotiation")
    unit: str = Field(..., description="Unit of measurement, e.g. units, kg, cases")
    market_reference_price: float = Field(..., gt=0, description="Prevailing market price per unit")
    buyer_target_price: float = Field(..., gt=0, description="Buyer's ideal / target price per unit (secret)")
    buyer_budget_cap: float = Field(..., gt=0, description="Buyer's absolute maximum per unit (secret)")
    seller_asking_price: float = Field(..., gt=0, description="Seller's initial asking price per unit")
    seller_floor_price: float = Field(..., gt=0, description="Seller's absolute minimum per unit (secret)")

class NonPriceTerm(BaseModel):
    term_type: str = Field(..., description="E.g., payment_terms, sla, penalty_clause")
    description: str = Field(..., description="Full text description of the term")
    negotiable: bool = Field(default=True, description="Whether this term is negotiable")

class ProposedItem(BaseModel):
    sku: str = Field(..., description="The SKU this proposal applies to.")
    price: float = Field(..., ge=0.0, description="Proposed unit price.")
    quantity: int = Field(..., ge=1, description="Proposed quantity.")

class NegotiationScenario(BaseModel):
    """
    Describes the product, pricing, and delivery parameters for a
    single negotiation session.  All hardcoded values from buyer.py /
    seller.py have been moved here so that agents are driven purely
    by data.

    Used by:
    - Phase 1 agents for constructing dynamic system prompts and
      initial offers / acceptance logic.
    - Phase 2 trust engine to know the declared policies to check
      against (e.g., "buyer budget cap is ₹500 — did buyer exceed it?").
    - Phase 5 benchmarking to run many different adversarial scenarios
      without code changes.
    """

    currency: str = Field(default="INR", min_length=1, max_length=10, description="Currency code (INR, USD, EUR, …).")
    line_items: list[LineItem] = Field(..., min_length=1, description="List of items under negotiation")
    non_price_terms: list[NonPriceTerm] = Field(default_factory=list, description="Non-price terms like SLAs")
    delivery_preference_days: int = Field(..., ge=1, description="Buyer's preferred delivery window (days).")
    standard_delivery_days: int = Field(..., ge=1, description="Seller's standard default delivery window (days).")
    expedited_delivery_days: int | None = Field(
        default=None, ge=1,
        description="Seller's expedited delivery window (days); None = not available.",
    )
    expedited_premium_per_unit: float | None = Field(
        default=None, ge=0,
        description="Premium per unit for expedited delivery; None = not available.",
    )

    @field_validator("currency", mode="before")
    @classmethod
    def _validate_currency(cls, v: str) -> str:
        """Normalize and validate the currency against the config-driven registry.

        The registry (env var TRUSTMESH_CURRENCIES) is the single source of truth —
        do not hardcode currency lists elsewhere. Unknown codes are rejected rather
        than silently accepted.
        """
        from .currency_registry import registry
        code = str(v).strip().upper()
        if not registry.is_valid(code):
            raise ValueError(
                f"Unsupported currency {v!r}. Configured currencies: "
                f"{', '.join(registry.codes)}. Add it to TRUSTMESH_CURRENCIES to enable."
            )
        return code

    @model_validator(mode="after")
    def _check_price_sanity(self):
        """Raise error if the buyer and seller price ranges don't overlap for any line item."""
        for item in self.line_items:
            if item.buyer_budget_cap < item.seller_floor_price:
                raise ValueError(
                    f"Scenario price gap for SKU {item.sku}: buyer budget cap ({item.buyer_budget_cap:.2f}) < "
                    f"seller floor ({item.seller_floor_price:.2f}) — a deal is impossible."
                )
        return self

    @computed_field
    @property
    def product_name(self) -> str:
        return self.line_items[0].product_name if self.line_items else ""

    @computed_field
    @property
    def quantity(self) -> int:
        return self.line_items[0].quantity if self.line_items else 1

    @computed_field
    @property
    def market_reference_price(self) -> float:
        return self.line_items[0].market_reference_price if self.line_items else 0.0

    @computed_field
    @property
    def buyer_target_price(self) -> float:
        return self.line_items[0].buyer_target_price if self.line_items else 0.0

    @computed_field
    @property
    def buyer_budget_cap(self) -> float:
        return self.line_items[0].buyer_budget_cap if self.line_items else 0.0

    @computed_field
    @property
    def seller_asking_price(self) -> float:
        return self.line_items[0].seller_asking_price if self.line_items else 0.0

    @computed_field
    @property
    def seller_floor_price(self) -> float:
        return self.line_items[0].seller_floor_price if self.line_items else 0.0

    model_config = {
        "json_schema_extra": {
            "example": {
                "currency": "INR",
                "line_items": [
                    {
                        "sku": "SKU-001",
                        "product_name": "Office chairs",
                        "quantity": 100,
                        "unit": "units",
                        "market_reference_price": 500.0,
                        "buyer_target_price": 440.0,
                        "buyer_budget_cap": 500.0,
                        "seller_asking_price": 550.0,
                        "seller_floor_price": 420.0
                    }
                ],
                "delivery_preference_days": 14,
                "standard_delivery_days": 21,
                "expedited_delivery_days": 10,
                "expedited_premium_per_unit": 25.0,
            }
        }
    }


# ---------------------------------------------------------------------------
# Default scenario (original office-chairs setup)
# ---------------------------------------------------------------------------

DEFAULT_SCENARIO = NegotiationScenario(
    currency="INR",
    line_items=[
        LineItem(
            sku="SKU-001",
            product_name="Office chairs",
            quantity=100,
            unit="units",
            market_reference_price=500.0,
            buyer_target_price=440.0,
            buyer_budget_cap=500.0,
            seller_asking_price=550.0,
            seller_floor_price=420.0,
        )
    ],
    delivery_preference_days=14,
    standard_delivery_days=21,
    expedited_delivery_days=10,
    expedited_premium_per_unit=25.0,
)
