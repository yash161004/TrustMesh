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
from ..models import AgentRole, MessageType, NegotiationMessage, NegotiationScenario, ProposedItem
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
        
        items_desc = "\n".join([
            f"- {i.quantity} {i.unit} of {i.product_name} (SKU: {i.sku}). Max budget: {s.currency}{i.buyer_budget_cap:.2f}/unit. Market ref: {s.currency}{i.market_reference_price:.2f}/unit."
            for i in s.line_items
        ])
        
        expedited_section = ""
        if s.expedited_delivery_days and s.expedited_premium_per_unit:
            expedited_section = (
                f"- If faster delivery is needed, expedited ({s.expedited_delivery_days} days) "
                f"is available at +{s.currency}{s.expedited_premium_per_unit:.2f}/unit\n"
            )
            
        return f"""You are a Buyer agent in a B2B procurement negotiation.

Your objectives:
- Secure the best possible prices across all items without exceeding max budgets.
- Get delivery within {s.delivery_preference_days} days (faster is better, but cost matters more)
- Ensure quality and product standards
- Build a long-term supplier relationship

You are negotiating for the following items:
{items_desc}

Negotiation strategy:
1. Start with conservative offers below your max budget.
2. Counter with small increases (5-8%) each turn.
3. Trade faster delivery for slightly higher price if needed.
4. Know when to walk away if price exceeds budget cap for any item.
5. If the seller's price is within your budget cap and within 5% of your target, accept the deal with "message_type": "ACCEPT".
6. Consider delivery terms: {s.delivery_preference_days}-day delivery is preferred.
{expedited_section}
Response format (JSON only):
{{
    "message_type": "OFFER" | "COUNTER_OFFER" | "ACCEPT" | "REJECT",
    "proposed_items": [
        {{ "sku": "<sku>", "price": <number>, "quantity": <number> }}
    ],
    "delivery_terms": "<delivery time in days, payment terms>",
    "notes": "<your reasoning including delivery considerations>"
}}

Be professional, data-driven, and strategic. Prices in {s.currency}."""

    def create_initial_offer(self, context: dict) -> NegotiationMessage:
        """Create the buyer's initial offer based on scenario."""
        self.turn_number = 1
        s = self.scenario
        
        proposed_items = []
        notes_items = []
        for item in s.line_items:
            # 12% below market reference price
            starting_price = item.market_reference_price * 0.88
            proposed_items.append(
                ProposedItem(sku=item.sku, price=round(starting_price, 2), quantity=item.quantity)
            )
            notes_items.append(f"{item.quantity} {item.unit} of {item.product_name}")

        message = NegotiationMessage(
            message_type=MessageType.OFFER,
            sender=self.agent_id,
            proposed_items=proposed_items,
            delivery_terms=(
                f"Delivery within {s.delivery_preference_days} days, Net-30 payment, "
                "FOB destination, quality inspection on arrival"
            ),
            timestamp=datetime.now(timezone.utc),
            turn_number=self.turn_number,
            notes=(
                f"Initial offer for {', '.join(notes_items)}. "
                f"Requesting delivery within {s.delivery_preference_days} days."
            ),
        )

        self.add_message(message)
        return message

    def should_accept(self, proposed_items: list[ProposedItem]) -> bool:
        """Determine if the buyer should accept the current offer."""
        s = self.scenario
        sku_to_item = {i.sku: i for i in s.line_items}
        
        for p_item in proposed_items:
            s_item = sku_to_item.get(p_item.sku)
            if not s_item:
                continue
            if p_item.price > s_item.buyer_budget_cap:
                return False
        return True
