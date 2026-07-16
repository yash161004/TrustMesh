"""
Manipulation Detector — Phase 2: Trust Engine

Analyses price movement patterns across a negotiation to detect
manipulation tactics:
- Price swings (sudden large changes)
- Circular pricing (returning to a previous price)
- Unreasonable anchoring
"""
from __future__ import annotations

from typing import Optional

from ...models import NegotiationMessage
from ..models import Severity, Violation, ViolationType


class ManipulationDetector:
    """Detects suspicious price patterns in negotiation history."""

    MAX_SWING_PCT = 15.0  # Max reasonable single-turn price change (%)
    MAX_SWING_PCT_EARLY = 25.0  # Looser for first 3 turns

    def evaluate(
        self,
        history: list[NegotiationMessage],
        agent_id: str,
    ) -> list[Violation]:
        violations: list[Violation] = []
        agent_msgs = [m for m in history if m.sender == agent_id]
        if len(agent_msgs) < 2:
            return violations

        prices = [m.price for m in agent_msgs]

        # --- Price swing detection ---
        for i in range(1, len(prices)):
            pct_change = abs(prices[i] - prices[i-1]) / prices[i-1] * 100
            threshold = self.MAX_SWING_PCT_EARLY if i <= 2 else self.MAX_SWING_PCT
            if pct_change > threshold:
                violations.append(Violation(
                    violation_type=ViolationType.PRICE_SWING,
                    severity=Severity.MEDIUM if pct_change <= 30 else Severity.HIGH,
                    message_turn=agent_msgs[i].turn_number,
                    agent_id=agent_id,
                    description=f"Price swing of {pct_change:.1f}% from {prices[i-1]:.2f} to {prices[i]:.2f} (threshold: {threshold}%)",
                    detail={"from": prices[i-1], "to": prices[i], "pct_change": round(pct_change, 1)},
                ))

        # --- Circular pricing: returning to same price within tolerance ---
        for i in range(2, len(prices)):
            for j in range(i - 1):
                if abs(prices[i] - prices[j]) / max(prices[i], prices[j], 0.01) < 0.01:
                    violations.append(Violation(
                        violation_type=ViolationType.CIRCULAR_PRICING,
                        severity=Severity.MEDIUM,
                        message_turn=agent_msgs[i].turn_number,
                        agent_id=agent_id,
                        description=f"Circular pricing: returned to {prices[i]:.2f} (turn {agent_msgs[j].turn_number} → turn {agent_msgs[i].turn_number})",
                        detail={"price": prices[i], "first_turn": agent_msgs[j].turn_number, "return_turn": agent_msgs[i].turn_number},
                    ))
                    break  # one circular flag per message

        return violations
