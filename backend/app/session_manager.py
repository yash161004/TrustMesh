"""
TrustMesh Session Manager — Phase 1: Agent Logic

Manages negotiation sessions between buyer and seller agents.
Coordinates turn-based negotiation and tracks session state.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from .agents.buyer import BuyerAgent
from .agents.seller import SellerAgent
from .config import get_settings
from .models import (
    AgentRole,
    MessageType,
    NegotiationMessage,
    NegotiationSession,
    NegotiationSessionStatus,
)

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages active negotiation sessions.
    
    Responsibilities:
    - Create and track negotiation sessions
    - Coordinate agent turns
    - Enforce turn limits and timeouts
    - Provide session state queries
    """

    def __init__(self):
        self.sessions: dict[str, NegotiationSession] = {}
        self.agents: dict[str, dict[AgentRole, BuyerAgent | SellerAgent]] = {}
        self.contexts: dict[str, dict] = {}  # Store initial context per session
        self.session_locks: dict[str, asyncio.Lock] = {}  # Per-session locks
        self._lock = asyncio.Lock()  # Global lock for session creation

    async def create_session(
        self,
        buyer_agent_id: str = "buyer-agent-001",
        seller_agent_id: str = "seller-agent-001",
        initial_context: Optional[dict] = None,
        provider: str = "gemini",
    ) -> NegotiationSession:
        """Create a new negotiation session with buyer and seller agents."""
        session_id = str(uuid4())
        settings = get_settings()

        # Use provider from settings if not specified
        if not provider:
            provider = "gemini" if settings.gemini_api_key else "mock"

        # Create agents
        buyer = BuyerAgent(
            agent_id=buyer_agent_id,
            provider=provider,
        )
        seller = SellerAgent(
            agent_id=seller_agent_id,
            provider=provider,
        )

        # Create session
        session = NegotiationSession(
            session_id=session_id,
            buyer_agent_id=buyer_agent_id,
            seller_agent_id=seller_agent_id,
            status=NegotiationSessionStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )

        async with self._lock:
            self.sessions[session_id] = session
            self.agents[session_id] = {
                AgentRole.BUYER: buyer,
                AgentRole.SELLER: seller,
            }
            self.contexts[session_id] = initial_context or {
                "starting_price": 250.0,
                "quantity": 100,
                "product": "Industrial components",
            }
            self.session_locks[session_id] = asyncio.Lock()

        logger.info(f"Created session {session_id} with provider={provider}")
        return session

    async def start_session(self, session_id: str, context: Optional[dict] = None) -> NegotiationMessage:
        """Start a negotiation session with the buyer's initial offer.
        
        Note: When called from process_turn, the per-session lock is already held.
        This method does NOT acquire the global lock to avoid deadlock.
        """
        session = self._get_session(session_id)
        agents = self._get_agents(session_id)

        session.status = NegotiationSessionStatus.ACTIVE
        buyer = agents[AgentRole.BUYER]

        # Use provided context or stored context
        initial_context = context or self.contexts.get(session_id, {
            "starting_price": 250.0,
            "quantity": 100,
            "product": "Industrial components",
        })
        
        initial_offer = buyer.create_initial_offer(initial_context)
        session.messages.append(initial_offer)
        
        logger.info(f"Session {session_id} started with initial offer: ${initial_offer.price}")
        return initial_offer

    async def process_turn(
        self,
        session_id: str,
        context: Optional[dict] = None,
        max_turns: int = 10,
    ) -> list[NegotiationMessage]:
        """
        Run a full negotiation session until completion or max turns.
        
        Returns list of all messages exchanged in this call.
        Uses per-session lock to prevent race conditions.
        """
        session = self._get_session(session_id)
        session_lock = self.session_locks.get(session_id)
        
        if not session_lock:
            raise ValueError(f"No lock found for session {session_id}")

        # Use per-session lock to prevent concurrent process_turn calls
        async with session_lock:
            agents = self._get_agents(session_id)
            stored_context = self.contexts.get(session_id, {})

            # Start session if pending
            if session.status == NegotiationSessionStatus.PENDING:
                await self.start_session(session_id, context)

            session.status = NegotiationSessionStatus.ACTIVE
            messages = []
            turn_count = 0

            while (
                session.status == NegotiationSessionStatus.ACTIVE
                and turn_count < max_turns
            ):
                # Determine whose turn it is based on last message
                last_message = session.messages[-1] if session.messages else None
                
                if last_message and last_message.sender == session.buyer_agent_id:
                    # Seller's turn to respond
                    current_agent = agents[AgentRole.SELLER]
                    role = "seller"
                else:
                    # Buyer's turn (initial or after seller)
                    current_agent = agents[AgentRole.BUYER]
                    role = "buyer"

                # Build context for this turn
                turn_context = {
                    **stored_context,
                    **(context or {}),
                    "last_price": last_message.price if last_message else stored_context.get("starting_price", 250.0),
                    "turn": len(session.messages) + 1,
                    "role": role,
                }

                # Generate response
                try:
                    response = await current_agent.generate_response(turn_context)
                    session.messages.append(response)
                    messages.append(response)
                    turn_count += 1
                    
                    logger.info(
                        f"Session {session_id} Turn {turn_count}: "
                        f"{role} -> {response.message_type.value} @ ${response.price}"
                    )

                    # Check for termination conditions
                    if response.message_type in (MessageType.ACCEPT, MessageType.REJECT):
                        session.status = NegotiationSessionStatus.COMPLETED
                        break
                        
                except Exception as e:
                    logger.error(f"Session {session_id} turn error: {e}")
                    session.status = NegotiationSessionStatus.FAILED
                    break

            # Mark completed if we hit max turns
            if session.status == NegotiationSessionStatus.ACTIVE:
                session.status = NegotiationSessionStatus.COMPLETED
                logger.info(f"Session {session_id} completed after {turn_count} turns")

            return messages

    async def get_session(self, session_id: str) -> NegotiationSession:
        """Get session by ID."""
        async with self._lock:
            return self._get_session(session_id)

    async def list_sessions(self) -> list[NegotiationSession]:
        """List all sessions."""
        async with self._lock:
            return list(self.sessions.values())

    async def get_messages(self, session_id: str) -> list[NegotiationMessage]:
        """Get all messages for a session."""
        async with self._lock:
            session = self._get_session(session_id)
            return session.messages.copy()

    def _get_session(self, session_id: str) -> NegotiationSession:
        """Get session or raise if not found."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        return self.sessions[session_id]

    def _get_agents(self, session_id: str) -> dict:
        """Get agents for a session."""
        if session_id not in self.agents:
            raise ValueError(f"Agents for session {session_id} not found")
        return self.agents[session_id]


# Global session manager instance
session_manager = SessionManager()
