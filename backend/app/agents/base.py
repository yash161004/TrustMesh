"""
TrustMesh Base Agent — Phase 1: Agent Logic

Provides the foundation for negotiation agents with shared behavior
for message generation, history tracking, and LLM interaction.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import AsyncIterator, Optional
from uuid import uuid4

from ..llm_client import LLMClient, get_llm_client
from ..models import AgentRole, MessageType, NegotiationMessage


class BaseAgent(ABC):
    """
    Abstract base class for negotiation agents.
    
    Subclasses implement role-specific negotiation strategies.
    """

    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        llm_client: Optional[LLMClient] = None,
        provider: str = "gemini",
    ):
        self.agent_id = agent_id
        self.role = role
        self.llm_client = llm_client or get_llm_client(provider)
        self.history: list[NegotiationMessage] = []
        self.turn_number = 0

    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent's role."""
        return f"""You are a {self.role.value} agent in a B2B negotiation.
Your goal is to negotiate the best deal for your position.

Respond with a JSON object containing:
- message_type: OFFER, COUNTER_OFFER, ACCEPT, or REJECT
- price: Your proposed unit price (numeric)
- quantity: Number of units (integer)
- delivery_terms: Delivery/SLA terms (string)
- notes: Your reasoning (string)

Be strategic but fair. Consider market conditions and the other party's constraints.
Always respond with valid JSON only, no other text."""

    def add_message(self, message: NegotiationMessage) -> None:
        """Add a message to the negotiation history."""
        self.history.append(message)
        self.turn_number = message.turn_number

    @abstractmethod
    def create_initial_offer(self, context: dict) -> NegotiationMessage:
        """Create the first offer for this agent's role."""
        ...

    async def generate_response(self, context: dict) -> NegotiationMessage:
        """Generate a response based on negotiation history and context."""
        self.turn_number += 1

        messages = self._build_messages(context)
        response_text = await self.llm_client.generate(messages, self.system_prompt)

        try:
            response_data = json.loads(response_text)
        except json.JSONDecodeError:
            response_data = self._fallback_response(context)

        message = NegotiationMessage(
            message_type=MessageType(response_data.get("message_type", "OFFER")),
            sender=self.agent_id,
            price=float(response_data.get("price", 0)),
            quantity=int(response_data.get("quantity", 1)),
            delivery_terms=response_data.get("delivery_terms", "Net-30"),
            timestamp=datetime.now(timezone.utc),
            turn_number=self.turn_number,
            notes=response_data.get("notes", ""),
        )

        self.add_message(message)
        return message

    async def generate_stream_response(self, context: dict) -> AsyncIterator[str]:
        """Generate a streaming response based on negotiation history."""
        self.turn_number += 1
        messages = self._build_messages(context)

        async for chunk in self.llm_client.generate_stream(messages, self.system_prompt):
            yield chunk

    def _build_messages(self, context: dict) -> list[dict]:
        """Build message history for LLM context."""
        messages = []

        # Add conversation history
        for msg in self.history[-10:]:  # Keep last 10 messages for context
            role = "assistant" if msg.sender == self.agent_id else "user"
            messages.append({
                "role": role,
                "content": json.dumps({
                    "message_type": msg.message_type.value,
                    "price": msg.price,
                    "quantity": msg.quantity,
                    "delivery_terms": msg.delivery_terms,
                    "notes": msg.notes or "",
                })
            })

        # Add current context
        if context:
            messages.append({
                "role": "user",
                "content": json.dumps({
                    "action": "respond_to_negotiation",
                    "context": context,
                    "turn": self.turn_number,
                })
            })

        return messages

    def _fallback_response(self, context: dict) -> dict:
        """Generate a fallback response when JSON parsing fails."""
        return {
            "message_type": "COUNTER_OFFER",
            "price": context.get("last_price", 200),
            "quantity": context.get("quantity", 100),
            "delivery_terms": "Net-30",
            "notes": "Fallback response due to parsing error",
        }
