"""
TrustMesh Buyer Agent — Phase 1: Agent Logic

Implements the Buyer agent's negotiation strategy for B2B procurement.
The buyer aims to minimize cost while securing quality and delivery terms.
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
    - Focus on total cost of ownership
    - Consider volume discounts
    """

    def __init__(
        self,
        agent_id: str = "buyer-agent-001",
        llm_client: Optional[LLMClient] = None,
        provider: str = "gemini",
        target_price: float = 180.0,
        max_price: float = 250.0,
        min_quantity: int = 50,
    ):
        super().__init__(agent_id, AgentRole.BUYER, llm_client, provider)
        self.target_price = target_price
        self.max_price = max_price
        self.min_quantity = min_quantity

    @property
    def system_prompt(self) -> str:
        return """You are a Buyer agent in a B2B procurement negotiation.

Your objectives:
- Secure the best possible price for quality goods
- Ensure reliable delivery terms
- Build a long-term supplier relationship
- Stay within budget constraints

Negotiation strategy:
1. Start with an offer 10-15% below market rate
2. Counter with small increases (5-10%) each turn
3. Emphasize volume and repeat business potential
4. Consider total cost including delivery and payment terms
5. Know when to walk away if price exceeds value

Response format (JSON only):
{
    "message_type": "OFFER" | "COUNTER_OFFER" | "ACCEPT" | "REJECT",
    "price": <number>,
    "quantity": <integer>,
    "delivery_terms": "<string>",
    "notes": "<your reasoning>"
}

Be professional, data-driven, and strategic."""

    def create_initial_offer(self, context: dict) -> NegotiationMessage:
        """Create the buyer's initial offer."""
        self.turn_number = 1
        starting_price = context.get("starting_price", 250.0) * 0.85  # 15% below asking
        quantity = context.get("quantity", self.min_quantity)

        message = NegotiationMessage(
            message_type=MessageType.OFFER,
            sender=self.agent_id,
            price=round(starting_price, 2),
            quantity=quantity,
            delivery_terms="Net-30, FOB destination, 2% early payment discount",
            timestamp=datetime.now(timezone.utc),
            turn_number=self.turn_number,
            notes="Initial offer based on market research and volume commitment.",
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
