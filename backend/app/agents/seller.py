"""
TrustMesh Seller Agent — Phase 1: Agent Logic

Implements the Seller agent's negotiation strategy for B2B sales.
The seller aims to maximize revenue while maintaining competitive pricing.

All pricing / product details come from a NegotiationScenario object —
NOT hardcoded values.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..llm_client import LLMClient
from ..models import AgentRole, MessageType, NegotiationMessage, NegotiationScenario
from .base import BaseAgent


class SellerAgent(BaseAgent):
    """
    Seller agent for B2B negotiation driven by a NegotiationScenario.

    Strategy:
    - Start with a premium price above market rate
    - Counter with incremental decreases
    - Emphasize value, quality, and reliability
    - Offer expedited delivery as a premium upsell
    """

    def __init__(
        self,
        agent_id: str = "seller-agent-001",
        llm_client: Optional[LLMClient] = None,
        provider: str = "gemini",
        scenario: Optional[NegotiationScenario] = None,
    ):
        super().__init__(agent_id, AgentRole.SELLER, llm_client, provider)
        from ..models import DEFAULT_SCENARIO
        self.scenario = scenario or DEFAULT_SCENARIO

    @property
    def system_prompt(self) -> str:
        s = self.scenario
        expedited_section = ""
        if s.expedited_delivery_days and s.expedited_premium_per_unit:
            expedited_section = (
                f"- Offer expedited {s.expedited_delivery_days}-day delivery "
                f"as a premium service (+{s.currency}{s.expedited_premium_per_unit:.2f}/unit)\n"
            )
        return f"""You are a Seller agent in a B2B sales negotiation for {s.product_name.upper()}.

Your objectives:
- Maximize revenue while remaining competitive
- Build long-term customer relationships
- Maintain profit margins — your floor is {s.currency}{s.seller_floor_price:.2f}/unit
- Offer delivery options: standard ({s.standard_delivery_days} days) is included

The market reference price for {s.product_name} is {s.currency}{s.market_reference_price:.2f}/unit.
You are negotiating for {s.quantity} units.

Negotiation strategy:
1. Start with asking price of {s.currency}{s.seller_asking_price:.2f}/unit (premium pricing)
2. Counter with small decreases (5-8%) each turn
3. Emphasize quality, durability, and warranty
{expedited_section}4. Standard {s.standard_delivery_days}-day delivery is included in the base price
5. Know when to hold firm — don't go below {s.currency}{s.seller_floor_price:.2f}/unit
6. Volume commitment ({s.quantity} units) deserves some discount

Response format (JSON only):
{{
    "message_type": "OFFER" | "COUNTER_OFFER" | "ACCEPT" | "REJECT",
    "price": <number>,
    "quantity": {s.quantity},
    "delivery_terms": "<delivery time in days, payment terms, warranty>",
    "notes": "<your reasoning including delivery options offered>"
}}

Be professional, value-focused, and strategic. Prices in {s.currency}."""

    def create_initial_offer(self, context: dict) -> NegotiationMessage:
        """Create the seller's initial offer based on scenario."""
        self.turn_number = 1
        s = self.scenario
        starting_price = context.get("asking_price", s.seller_asking_price)
        quantity = context.get("quantity", s.quantity)

        expedited_note = ""
        if s.expedited_delivery_days and s.expedited_premium_per_unit:
            expedited_note = (
                f"Expedited {s.expedited_delivery_days}-day delivery available "
                f"at +{s.currency}{s.expedited_premium_per_unit:.2f}/unit."
            )

        message = NegotiationMessage(
            message_type=MessageType.OFFER,
            sender=self.agent_id,
            price=round(starting_price, 2),
            quantity=quantity,
            delivery_terms=(
                f"Standard delivery within {s.standard_delivery_days} days, "
                "Net-15 payment, FOB origin, "
                "2-year warranty on manufacturing defects"
            ),
            timestamp=datetime.now(timezone.utc),
            turn_number=self.turn_number,
            notes=(
                f"Premium offering for {int(quantity)} {s.product_name}. "
                f"Standard delivery {s.standard_delivery_days} days included. "
                f"{expedited_note}"
            ),
        )

        self.add_message(message)
        return message

    def should_accept(self, price: float, quantity: int) -> bool:
        """Determine if the seller should accept the current offer."""
        s = self.scenario
        if price >= s.seller_asking_price:
            return True
        if price >= s.seller_floor_price and quantity >= s.quantity:
            return True
        return False

    def calculate_min_counter(self) -> float:
        """Calculate the minimum price the seller is willing to counter."""
        s = self.scenario
        if not self.history:
            return s.seller_floor_price

        last_offer = self.history[-1]
        decrement = (s.seller_asking_price - s.seller_floor_price) * 0.12
        return max(last_offer.price - decrement, s.seller_floor_price)
