"""
TrustMesh Seller Agent — Phase 1: Agent Logic

Implements the Seller agent's negotiation strategy for B2B sales.
The seller aims to maximize revenue while maintaining competitive pricing.

Scenario: Selling office chairs
- Secret minimum price: ₹420/unit
- Standard delivery: 21 days
- Can expedite to 10 days for a premium
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
    - Offer expedited delivery as a premium upsell
    """

    def __init__(
        self,
        agent_id: str = "seller-agent-001",
        llm_client: Optional[LLMClient] = None,
        provider: str = "gemini",
        floor_price: float = 420.0,         # Absolute minimum (₹/unit)
        asking_price: float = 550.0,         # Initial asking (₹/unit)
        min_quantity: int = 100,             # Minimum order
        standard_delivery_days: int = 21,    # Standard delivery time
        expedited_delivery_days: int = 10,   # Expedited delivery time
        expedited_premium: float = 25.0,     # Premium for expedited (₹/unit)
    ):
        super().__init__(agent_id, AgentRole.SELLER, llm_client, provider)
        self.floor_price = floor_price
        self.asking_price = asking_price
        self.min_quantity = min_quantity
        self.standard_delivery_days = standard_delivery_days
        self.expedited_delivery_days = expedited_delivery_days
        self.expedited_premium = expedited_premium

    @property
    def system_prompt(self) -> str:
        return """You are a Seller agent in a B2B sales negotiation for OFFICE CHAIRS.

Your objectives:
- Maximize revenue while remaining competitive
- Build long-term customer relationships
- Maintain profit margins — your floor is ₹420/unit
- Offer delivery options: standard (21 days) or expedited (10 days, +₹25/unit)

Negotiation strategy:
1. Start with asking price around ₹550/unit (premium pricing)
2. Counter with small decreases (5-8%) each turn
3. Emphasize ergonomic quality, durability, and warranty
4. Offer expedited 10-day delivery as a premium service (+₹25/unit)
5. Standard 21-day delivery is included in the base price
6. Know when to hold firm — don't go below ₹420/unit
7. Volume commitment (100 units) deserves some discount

Response format (JSON only):
{
    "message_type": "OFFER" | "COUNTER_OFFER" | "ACCEPT" | "REJECT",
    "price": <number>,
    "quantity": 100,
    "delivery_terms": "<delivery time in days, payment terms, warranty>",
    "notes": "<your reasoning including delivery options offered>"
}

Be professional, value-focused, and strategic. Prices in INR (₹)."""

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
            delivery_terms=(
                f"Standard delivery within {self.standard_delivery_days} days, "
                "Net-15 payment, FOB origin, "
                "2-year warranty on manufacturing defects"
            ),
            timestamp=datetime.now(timezone.utc),
            turn_number=self.turn_number,
            notes=(
                f"Premium offering for {int(quantity)} ergonomic office chairs. "
                f"Standard delivery {self.standard_delivery_days} days included. "
                f"Expedited {self.expedited_delivery_days}-day delivery available at +₹{self.expedited_premium}/unit."
            ),
        )

        self.add_message(message)
        return message

    def should_accept(self, price: float, quantity: int) -> bool:
        """Determine if the seller should accept the current offer."""
        if price >= self.asking_price:
            return True
        if price >= self.floor_price and quantity >= self.min_quantity:
            return True
        return False

    def calculate_min_counter(self) -> float:
        """Calculate the minimum price the seller is willing to counter."""
        if not self.history:
            return self.floor_price

        last_offer = self.history[-1]
        decrement = (self.asking_price - self.floor_price) * 0.12
        return max(last_offer.price - decrement, self.floor_price)
