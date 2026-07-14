"""
TrustMesh Buyer Agent — Phase 1: Agent Logic

Implements the Buyer agent's negotiation strategy for B2B procurement.
The buyer aims to minimize cost while securing quality and delivery terms.

Scenario: Purchasing office chairs
- Secret max budget: ₹500/unit
- Wants 100 units
- Prefers delivery within 14 days
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..llm_client import LLMClient
from ..models import AgentRole, MessageType, NegotiationMessage
from .base import BaseAgent


class BuyerAgent(BaseAgent):
    """
    Buyer agent for B2B negotiation.

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
        target_price: float = 440.0,       # Ideal price target (₹/unit)
        max_price: float = 500.0,           # Absolute max budget (₹/unit)
        min_quantity: int = 100,            # Wants 100 units
        preferred_delivery_days: int = 14,  # Wants delivery within 14 days
    ):
        super().__init__(agent_id, AgentRole.BUYER, llm_client, provider)
        self.target_price = target_price
        self.max_price = max_price
        self.min_quantity = min_quantity
        self.preferred_delivery_days = preferred_delivery_days

    @property
    def system_prompt(self) -> str:
        return """You are a Buyer agent in a B2B procurement negotiation for OFFICE CHAIRS.

Your objectives:
- Secure the best possible price — your max budget is ₹500/unit
- Get delivery within 14 days (faster is better, but cost matters more)
- Ensure quality and ergonomic standards
- Build a long-term supplier relationship

Negotiation strategy:
1. Start with an offer around ₹420-440/unit (below your ₹500 max)
2. Counter with small increases (5-8%) each turn
3. Trade faster delivery for slightly higher price if needed
4. Emphasize volume (100 units) and repeat business potential
5. Know when to walk away if price exceeds ₹500/unit
6. Consider delivery terms: 14-day delivery is preferred, but you can stretch to 21 days for a better price

Response format (JSON only):
{
    "message_type": "OFFER" | "COUNTER_OFFER" | "ACCEPT" | "REJECT",
    "price": <number>,
    "quantity": 100,
    "delivery_terms": "<delivery time in days, payment terms>",
    "notes": "<your reasoning including delivery considerations>"
}

Be professional, data-driven, and strategic. Prices in INR (₹)."""

    def create_initial_offer(self, context: dict) -> NegotiationMessage:
        """Create the buyer's initial offer."""
        self.turn_number = 1
        starting_price = context.get("starting_price", 500.0) * 0.88  # 12% below asking
        quantity = context.get("quantity", self.min_quantity)

        message = NegotiationMessage(
            message_type=MessageType.OFFER,
            sender=self.agent_id,
            price=round(starting_price, 2),
            quantity=quantity,
            delivery_terms=(
                "Delivery within 14 days, Net-30 payment, "
                "FOB destination, quality inspection on arrival"
            ),
            timestamp=datetime.now(timezone.utc),
            turn_number=self.turn_number,
            notes=(
                f"Initial offer for {int(quantity)} office chairs. "
                f"Requesting delivery within {self.preferred_delivery_days} days. "
                "Price based on market research for bulk order."
            ),
        )

        self.add_message(message)
        return message

    def should_accept(self, price: float, quantity: int) -> bool:
        """Determine if the buyer should accept the current offer."""
        if price <= self.target_price:
            return True
        if price <= self.max_price and quantity >= self.min_quantity:
            return True
        return False

    def calculate_max_counter(self) -> float:
        """Calculate the maximum price the buyer is willing to counter."""
        if not self.history:
            return self.max_price

        last_offer = self.history[-1]
        increment = (self.max_price - self.target_price) * 0.15
        return min(last_offer.price + increment, self.max_price)
