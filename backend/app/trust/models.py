"""
TrustMesh Trust Engine Models — Phase 2: Trust Engine

Schemas for trust evaluation scores, violations, and reports.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ViolationType(str, Enum):
    """Categories of trust violations detected by the Trust Engine."""
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    FLOOR_VIOLATED = "FLOOR_VIOLATED"
    PRICE_SWING = "PRICE_SWING"
    CIRCULAR_PRICING = "CIRCULAR_PRICING"
    BROKEN_COMMITMENT = "BROKEN_COMMITMENT"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    MANIPULATION_PATTERN = "MANIPULATION_PATTERN"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ViolationStatus(str, Enum):
    FLAGGED = "FLAGGED"
    DISPUTED = "DISPUTED"
    CLEARED = "CLEARED"


class Violation(BaseModel):
    """A single detected trust violation."""
    violation_type: ViolationType
    severity: Severity
    message_turn: int
    agent_id: str
    description: str
    status: ViolationStatus = Field(default=ViolationStatus.FLAGGED)
    detail: Optional[dict] = None


class TrustScore(BaseModel):
    """Trust score for a single agent in a session."""
    agent_id: str
    overall_score: float = Field(..., ge=0, le=100)
    violation_count: int = 0
    recent_trend: str = "stable"  # improving, declining, stable


class TrustReport(BaseModel):
    """Complete trust evaluation for a session at a point in time."""
    session_id: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    buyer_score: Optional[TrustScore] = None
    seller_score: Optional[TrustScore] = None
    violations: list[Violation] = Field(default_factory=list)
    summary: str = ""
