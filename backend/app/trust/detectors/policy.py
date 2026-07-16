"""
Policy Deviation Flagger — Phase 2: Trust Engine

Checks each negotiation message against the declared policies in the
NegotiationScenario (budget cap, floor price, quantity, currency) and flags violations.
"""
from __future__ import annotations

from typing import TypedDict
from ...models import NegotiationMessage, NegotiationScenario


class PolicyDeviationResult(TypedDict):
    flagged: bool
    reason: str
    trust_impact: int


class PolicyDeviationFlagger:
    """Flags messages that violate declared negotiation policies (rule-based)."""

    def evaluate(
        self,
        message: NegotiationMessage,
        scenario: NegotiationScenario,
        role: str,
    ) -> PolicyDeviationResult:
        reasons = []
        trust_impact = 0

        # Generous Giver: Seller went below floor price
        if role == "seller" and message.price < scenario.seller_floor_price:
            reasons.append(f"Seller offered {scenario.currency}{message.price:.2f}/unit, below floor of {scenario.currency}{scenario.seller_floor_price:.2f}/unit.")
            trust_impact -= 40

        # Splurge: Buyer exceeded budget cap
        if role == "buyer" and message.price > scenario.buyer_budget_cap:
            reasons.append(f"Buyer offered {scenario.currency}{message.price:.2f}/unit, exceeding budget cap of {scenario.currency}{scenario.buyer_budget_cap:.2f}/unit.")
            trust_impact -= 35

        # Volume Discount Trick: Seller changes quantity
        if role == "seller" and message.quantity != scenario.quantity:
            reasons.append(f"Seller proposed quantity {message.quantity} differing from scenario {scenario.quantity}.")
            trust_impact -= 25

        # Secret Currency Swap: Currency mismatch in delivery terms
        currencies = ["USD", "EUR", "GBP", "INR", "JPY"]
        for curr in currencies:
            if curr != scenario.currency and curr in message.delivery_terms.upper():
                reasons.append(f"Found unexpected currency {curr} in delivery terms.")
                trust_impact -= 45
                break

        if reasons:
            return {
                "flagged": True,
                "reason": " ".join(reasons),
                "trust_impact": trust_impact,
            }

        return {
            "flagged": False,
            "reason": "",
            "trust_impact": 0,
        }
