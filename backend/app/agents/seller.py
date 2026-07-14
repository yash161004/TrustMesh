"""
TrustMesh Seller Agent — Phase 1: Agent Logic

Implements the Seller agent's negotiation strategy for B2B sales.
The seller aims to maximize revenue while maintaining competitive pricing.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..llm_client import LLMClient
from ..models import AgentRole, MessageType, NegotiationMessage
from .base import BaseAgent


class SellerAgent(BaseAgent):
    """
    Seller agent for B2B negotiation.
    
    Strategy:
    - Start with a premium price above market rate
    - Counter with incremental decreases
    - Emphasize value, quality, and reliability
    - Consider volume discounts strategically
    """

    def __init__(
        self,
        agent_id: str = "seller-agent-001",
        llm_client: Optional[LLMClient] = None,
        provider: str = "gemini",
        floor_price: float = 170.0,
        asking_price: float = 250.0,
        min_quantity: int = 50,
    ):
        super().__init__(agent_id, AgentRole.SELLER, llm_client, provider)
        self.floor_price = floor_price
        self.asking_price = asking_price
        self.min_quantity = min_quantity

    @property
    def system_prompt(self) -> str:
        return """You are a Seller agent in a B2B sales negotiation.

Your objectives:
- Maximize revenue while remaining competitive
- Build long-term customer relationships
- Maintain profit margins above floor price
- Offer value-added services when possible

Negotiation strategy:
1. Start with asking price or slightly above
2. Counter with small decreases (5-8%) each turn
3. Emphasize quality, reliability, and total value
4. Offer volume discounts for larger orders
5. Highlight payment terms and delivery advantages
6. Know when to hold firm on price

Response format (JSON only):
{
    "message_type": "OFFER" | "COUNTER_OFFER" | "ACCEPT" | "REJECT",
    "price": <number>,
    "quantity": <integer>,
    "delivery_terms": "<string>",
    "notes": "<your reasoning>"
}

Be professional, value-focused, and strategic."""

    def create_initial_offer(self, context: dict) -> NegotiationMessage:
        """Create the seller's initial offer."""
        self.turn_number = 1
        starting_price = context.get("asking_price", self.asking_price)
        quantity = context.get("quantity", self.min_quantity)

        message = NegotiationMessage(
            message_type=MessageType.OFFER,
            sender=self.agent_id,
            price=round(starting_price, 2),
            quantity=quantity,
            delivery_terms="Net-15, FOB origin, quality guarantee included",
            timestamp=datetime.now(timezone.utc),
            turn_number=self.turn_number,
            notes="Premium offering with quality guarantee and fast payment terms.",
        )

        self.add_message(message)
        return message

    def should_accept(self, price: float, quantity: int) -> bool:
        """Determine if the seller should accept the current offer."""
        if price >= self.asking_price:
            return True
        if price >= self.floor_price and quantity >= self.min_quantity * 2:
            return True
        return False

    def calculate_min_counter(self) -> float:
        """Calculate the minimum price the seller is willing to counter."""
        if not self.history:
            return self.floor_price

        last_offer = self.history[-1]
        decrement = (self.asking_price - self.floor_price) * 0.12
        return max(last_offer.price - decrement, self.floor_price)
