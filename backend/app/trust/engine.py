"""
Trust Engine — Phase 2: Trust Engine

Orchestrates all trust detectors and produces per-agent trust scores
and a complete TrustReport for a session.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..models import NegotiationMessage, NegotiationScenario
from .detectors.commitments import CommitmentTracker
from .detectors.manipulation import ManipulationDetector
from .detectors.policy import PolicyDeviationFlagger
from .models import Severity, TrustReport, TrustScore, Violation

logger = logging.getLogger(__name__)

# Score weights per severity
_PENALTY_MAP = {
    Severity.LOW: 2,
    Severity.MEDIUM: 5,
    Severity.HIGH: 12,
    Severity.CRITICAL: 25,
}

_BASE_SCORE = 100.0


class TrustEngine:
    """
    Evaluates trust for every message exchanged in a negotiation session.

    Combines results from:
    - PolicyDeviationFlagger (budget caps, floor prices)
    - ManipulationDetector (price swings, circular pricing)
    - CommitmentTracker (broken promises)

    Produces a per-agent TrustScore (0-100) and a complete TrustReport.
    """

    def __init__(self):
        self.policy_flagger = PolicyDeviationFlagger()
        self.manipulation = ManipulationDetector()
        self.commitments = CommitmentTracker()

    def evaluate_session(
        self,
        session_id: str,
        messages: list[NegotiationMessage],
        buyer_agent_id: str,
        seller_agent_id: str,
        scenario: Optional[NegotiationScenario] = None,
    ) -> TrustReport:
        """
        Run all trust detectors across the full message history.

        Produces a TrustReport with per-agent scores and all violations.
        """
        all_violations: list[Violation] = []

        # Per-message policy checks
        for msg in messages:
            if scenario:
                role = "buyer" if msg.sender == buyer_agent_id else "seller"
                result = self.policy_flagger.evaluate(msg, scenario, role)
                if result["flagged"]:
                    impact = abs(result["trust_impact"])
                    if impact >= 40:
                        sev = Severity.CRITICAL
                    elif impact >= 30:
                        sev = Severity.HIGH
                    elif impact >= 20:
                        sev = Severity.MEDIUM
                    else:
                        sev = Severity.LOW
                        
                    all_violations.append(Violation(
                        violation_type=ViolationType.POLICY_VIOLATION,
                        severity=sev,
                        message_turn=msg.turn_number,
                        agent_id=msg.sender,
                        description=result["reason"]
                    ))

        # Pattern checks across history
        # (Stubbed for now as per instructions)
        # all_violations.extend(self.manipulation.evaluate(messages, buyer_agent_id))
        # all_violations.extend(self.manipulation.evaluate(messages, seller_agent_id))

        # Commitment checks
        # (Stubbed for now as per instructions)
        # all_violations.extend(self.commitments.evaluate(messages, buyer_agent_id))
        # all_violations.extend(self.commitments.evaluate(messages, seller_agent_id))

        # Compute per-agent scores
        buyer_violations = [v for v in all_violations if v.agent_id == buyer_agent_id]
        seller_violations = [v for v in all_violations if v.agent_id == seller_agent_id]

        buyer_score_val = self._compute_score(buyer_violations)
        seller_score_val = self._compute_score(seller_violations)

        # Trend: compare first half vs second half violation rates
        buyer_trend = self._compute_trend(buyer_violations, messages, buyer_agent_id)
        seller_trend = self._compute_trend(seller_violations, messages, seller_agent_id)

        # Summary
        total_violations = len(all_violations)
        if total_violations == 0:
            summary = "No trust violations detected. Clean negotiation."
        else:
            summary = (
                f"Found {total_violations} violation(s): "
                f"Buyer {buyer_score_val:.0f}/100 ({len(buyer_violations)} violations, {buyer_trend}), "
                f"Seller {seller_score_val:.0f}/100 ({len(seller_violations)} violations, {seller_trend})"
            )

        return TrustReport(
            session_id=session_id,
            buyer_score=TrustScore(
                agent_id=buyer_agent_id,
                overall_score=buyer_score_val,
                violation_count=len(buyer_violations),
                recent_trend=buyer_trend,
            ),
            seller_score=TrustScore(
                agent_id=seller_agent_id,
                overall_score=seller_score_val,
                violation_count=len(seller_violations),
                recent_trend=seller_trend,
            ),
            violations=all_violations,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _compute_score(self, violations: list[Violation]) -> float:
        """Compute 0-100 score by subtracting penalties for each violation."""
        penalty = sum(_PENALTY_MAP.get(v.severity, 0) for v in violations)
        return max(0.0, _BASE_SCORE - penalty)

    def _compute_trend(
        self,
        violations: list[Violation],
        messages: list[NegotiationMessage],
        agent_id: str,
    ) -> str:
        """Compare violation density in first vs second half of messages."""
        agent_msgs = [m for m in messages if m.sender == agent_id]
        if len(agent_msgs) < 4 or not violations:
            return "stable"

        midpoint = len(agent_msgs) // 2
        first_half = [v for v in violations if v.message_turn <= agent_msgs[midpoint].turn_number]
        second_half = [v for v in violations if v.message_turn > agent_msgs[midpoint].turn_number]

        if len(second_half) > len(first_half) * 1.5:
            return "declining"
        if len(second_half) < len(first_half) * 0.5:
            return "improving"
        return "stable"


# Global trust engine instance
trust_engine = TrustEngine()
