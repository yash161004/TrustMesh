"""
Commitment Tracker — Phase 2: Trust Engine

Tracks commitments made in delivery_terms and notes across turns,
and flags when an agent contradicts a previous promise.
"""
from __future__ import annotations

import re
from ...models import NegotiationMessage
from ..models import Severity, Violation, ViolationType


class CommitmentTracker:
    """Tracks promises in negotiation and flags broken commitments."""

    # Phrases that indicate a commitment
    COMMITMENT_PATTERNS = [
        r"(?:will|can|shall|agree to|guarantee|promise|commit to)\s+(?:deliver|provide|offer|give|include)",
        r"(?:fixed|final|best|last)\s+(?:offer|price|bid)",
        r"(?:cannot|won't|will not)\s+(?:go below|exceed|reduce|increase)",
    ]

    def evaluate(
        self,
        history: list[NegotiationMessage],
        agent_id: str,
    ) -> list[Violation]:
        violations: list[Violation] = []
        agent_msgs = [m for m in history if m.sender == agent_id]
        if len(agent_msgs) < 2:
            return violations

        # Track prices that were called "final" or "last"
        final_price_declarations: list[tuple[int, float]] = []
        for msg in agent_msgs:
            combined = f"{msg.notes or ''} {msg.delivery_terms}".lower()
            if re.search(r"(?:final|last|best)\s+offer", combined):
                final_price_declarations.append((msg.turn_number, msg.price))

        # Check if agent later contradicted a "final" offer
        for turn, price in final_price_declarations:
            later_msgs = [m for m in agent_msgs if m.turn_number > turn]
            for later in later_msgs:
                if later.message_type.value in ("COUNTER_OFFER", "OFFER") and abs(later.price - price) > 0.001:
                    violations.append(Violation(
                        violation_type=ViolationType.BROKEN_COMMITMENT,
                        severity=Severity.MEDIUM,
                        message_turn=later.turn_number,
                        agent_id=agent_id,
                        description=f"Contradicted 'final offer' of {price:.2f} at turn {turn} with new offer of {later.price:.2f} at turn {later.turn_number}",
                        detail={"promised_price": price, "promise_turn": turn, "actual_price": later.price, "actual_turn": later.turn_number},
                    ))
                    break

        return violations
