"""
TrustMesh Buyer Agent — Phase 1: Agent Logic

Implements the Buyer agent's negotiation strategy for B2B procurement.
The buyer aims to minimize cost while securing quality and delivery terms.

All pricing / product details come from a NegotiationScenario object —
NOT hardcoded values.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..llm_client import LLMClient
from ..models import AgentRole, MessageType, NegotiationMessage, NegotiationScenario
from .base import BaseAgent


class BuyerAgent(BaseAgent):
    """
    Buyer agent for B2B negotiation driven by a NegotiationScenario.

    Strategy:
    - Start with a conservative offer below market rate
    - Counter with incremental increases
    - Focus on total cost of ownership including delivery
    - Consider volume discounts
    """

    def __init__(
        self,
        agent_id: str = "buyer-agent-001",
        llm_client: Optional[LLMClient] = None,
        provider: str = "gemini",
        scenario: Optional[NegotiationScenario] = None,
    ):
        super().__init__(agent_id, AgentRole.BUYER, llm_client, provider)
        from ..models import DEFAULT_SCENARIO
        self.scenario = scenario or DEFAULT_SCENARIO

    @property
    def system_prompt(self) -> str:
        s = self.scenario
        expedited_section = ""
        if s.expedited_delivery_days and s.expedited_premium_per_unit:
            expedited_section = (
                f"- If faster delivery is needed, expedited ({s.expedited_delivery_days} days) "
                f"is available at +{s.currency}{s.expedited_premium_per_unit:.2f}/unit\n"
            )
        return f"""You are a Buyer agent in a B2B procurement negotiation for {s.product_name.upper()}.

Your objectives:
- Secure the best possible price — your max budget is {s.currency}{s.buyer_budget_cap:.2f}/unit
- Get delivery within {s.delivery_preference_days} days (faster is better, but cost matters more)
- Ensure quality and product standards
- Build a long-term supplier relationship

The market reference price for {s.product_name} is {s.currency}{s.market_reference_price:.2f}/unit.
You are negotiating for {s.quantity} units.

Negotiation strategy:
1. Start with an offer around {s.currency}{s.buyer_target_price:.2f}/unit (below your {s.currency}{s.buyer_budget_cap:.2f} max)
2. Counter with small increases (5-8%) each turn
3. Trade faster delivery for slightly higher price if needed
4. Emphasize volume ({s.quantity} units) and repeat business potential
5. Know when to walk away if price exceeds {s.currency}{s.buyer_budget_cap:.2f}/unit
6. Consider delivery terms: {s.delivery_preference_days}-day delivery is preferred, but you can stretch to longer for a better price
{expedited_section}
Response format (JSON only):
{{
    "message_type": "OFFER" | "COUNTER_OFFER" | "ACCEPT" | "REJECT",
    "price": <number>,
    "quantity": {s.quantity},
    "delivery_terms": "<delivery time in days, payment terms>",
    "notes": "<your reasoning including delivery considerations>"
}}

Be professional, data-driven, and strategic. Prices in {s.currency}."""

    def create_initial_offer(self, context: dict) -> NegotiationMessage:
        """Create the buyer's initial offer based on scenario."""
        self.turn_number = 1
        s = self.scenario
        # 12% below market reference price
        starting_price = s.market_reference_price * 0.88
        quantity = context.get("quantity", s.quantity)

        message = NegotiationMessage(
            message_type=MessageType.OFFER,
            sender=self.agent_id,
            price=round(starting_price, 2),
            quantity=quantity,
            delivery_terms=(
                f"Delivery within {s.delivery_preference_days} days, Net-30 payment, "
                "FOB destination, quality inspection on arrival"
            ),
            timestamp=datetime.now(timezone.utc),
            turn_number=self.turn_number,
            notes=(
                f"Initial offer for {int(quantity)} {s.product_name}. "
                f"Requesting delivery within {s.delivery_preference_days} days. "
                f"Price based on market research ({s.currency} {s.market_reference_price:.2f}/unit reference) for bulk order."
            ),
        )

        self.add_message(message)
        return message

    def should_accept(self, price: float, quantity: int) -> bool:
        """Determine if the buyer should accept the current offer."""
        s = self.scenario
        if price <= s.buyer_target_price:
            return True
        if price <= s.buyer_budget_cap and quantity >= s.quantity:
            return True
        return False

    def calculate_max_counter(self) -> float:
        """Calculate the maximum price the buyer is willing to counter."""
        s = self.scenario
        if not self.history:
            return s.buyer_budget_cap

        last_offer = self.history[-1]
        increment = (s.buyer_budget_cap - s.buyer_target_price) * 0.15
        return min(last_offer.price + increment, s.buyer_budget_cap)
