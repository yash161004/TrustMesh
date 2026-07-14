"""
TrustMesh Session Manager — Phase 1: Agent Logic

Manages negotiation sessions between buyer and seller agents.
Coordinates turn-based negotiation and tracks session state.

All sessions and messages are persisted to SQLite via async SQLAlchemy.
After a server restart, sessions are loaded on first access.
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
from .db import (
    init_db,
    load_all_sessions,
    load_session,
    save_message,
    save_session,
    update_session_status,
)
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
    - Create and track negotiation sessions (persisted to SQLite)
    - Coordinate agent turns
    - Enforce turn limits and timeouts
    - Provide session state queries (reads from SQLite)
    """

    def __init__(self):
        # In-memory caches (loaded lazily from DB)
        self.sessions: dict[str, NegotiationSession] = {}
        self.agents: dict[str, dict[AgentRole, BuyerAgent | SellerAgent]] = {}
        self.contexts: dict[str, dict] = {}
        self.session_locks: dict[str, asyncio.Lock] = {}
        self._lock = asyncio.Lock()
        self._initialised = False  # Whether we've loaded from DB

    async def _ensure_initialised(self) -> None:
        """Load sessions from database on first access after startup."""
        if self._initialised:
            return
        async with self._lock:
            if self._initialised:
                return
            await init_db()
            try:
                db_sessions = await load_all_sessions()
                for s in db_sessions:
                    session_id = s["session_id"]
                    self.sessions[session_id] = self._dict_to_session(s)
                    self.session_locks[session_id] = asyncio.Lock()
                    self.contexts[session_id] = {
                        "starting_price": 500.0,
                        "quantity": 100,
                        "product": "Office chairs",
                    }
                logger.info("Loaded %d session(s) from database.", len(db_sessions))
            except Exception as e:
                logger.warning("Could not load sessions from DB (first run?): %s", e)
            self._initialised = True

    async def create_session(
        self,
        buyer_agent_id: str = "buyer-agent-001",
        seller_agent_id: str = "seller-agent-001",
        initial_context: Optional[dict] = None,
        provider: str = "gemini",
    ) -> NegotiationSession:
        """Create a new negotiation session with buyer and seller agents.

        Persists the session to SQLite immediately.
        """
        await self._ensure_initialised()
        session_id = str(uuid4())
        settings = get_settings()

        # Auto-detect mock mode: if no valid API key, force mock even if
        # provider is explicitly set to "gemini" or "groq"
        from .llm_client import _resolve_api_key as _has_key
        if not provider or (provider == "gemini" and not _has_key(settings.gemini_api_key)):
            provider = "mock"
            logger.info("No valid Gemini API key — forcing mock mode")
        if provider == "groq" and not _has_key(settings.groq_api_key):
            provider = "mock"
            logger.info("No valid Groq API key — forcing mock mode")

        buyer = BuyerAgent(agent_id=buyer_agent_id, provider=provider)
        seller = SellerAgent(agent_id=seller_agent_id, provider=provider)

        session = NegotiationSession(
            session_id=session_id,
            buyer_agent_id=buyer_agent_id,
            seller_agent_id=seller_agent_id,
            status=NegotiationSessionStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )

        # Persist to SQLite
        await save_session(
            session_id=session_id,
            buyer_agent_id=buyer_agent_id,
            seller_agent_id=seller_agent_id,
            status=session.status.value,
            created_at=session.created_at,
        )

        async with self._lock:
            self.sessions[session_id] = session
            self.agents[session_id] = {
                AgentRole.BUYER: buyer,
                AgentRole.SELLER: seller,
            }
            self.contexts[session_id] = initial_context or {
                "starting_price": 500.0,
                "quantity": 100,
                "product": "Office chairs",
            }
            self.session_locks[session_id] = asyncio.Lock()

        logger.info(
            "Created session %s with provider=%s (buyer=%s, seller=%s)",
            session_id, provider, buyer_agent_id, seller_agent_id,
        )
        return session

    async def start_session(
        self, session_id: str, context: Optional[dict] = None
    ) -> NegotiationMessage:
        """Start a negotiation session with the buyer's initial offer."""
        await self._ensure_initialised()
        session = self._get_session(session_id)
        agents = self._get_agents(session_id)

        session.status = NegotiationSessionStatus.ACTIVE
        buyer = agents[AgentRole.BUYER]

        initial_context = context or self.contexts.get(
            session_id,
            {"starting_price": 500.0, "quantity": 100, "product": "Office chairs"},
        )

        initial_offer = buyer.create_initial_offer(initial_context)
        session.messages.append(initial_offer)

        # Persist message and updated status
        await self._persist_message(session_id, initial_offer)
        await update_session_status(
            session_id=session_id,
            status=session.status.value,
        )

        logger.info(
            "Session %s started. %s initial offer: ₹%.2f/unit, delivery: %s",
            session_id, buyer.agent_id, initial_offer.price, initial_offer.delivery_terms,
        )
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
        All messages are persisted to SQLite as they are generated.
        """
        await self._ensure_initialised()
        session = self._get_session(session_id)
        session_lock = self.session_locks.get(session_id)

        if not session_lock:
            raise ValueError(f"No lock found for session {session_id}")

        async with session_lock:
            agents = self._get_agents(session_id)
            stored_context = self.contexts.get(session_id, {})

            if session.status == NegotiationSessionStatus.PENDING:
                await self.start_session(session_id, context)

            session.status = NegotiationSessionStatus.ACTIVE
            messages = []
            turn_count = 0

            while (
                session.status == NegotiationSessionStatus.ACTIVE
                and turn_count < max_turns
            ):
                last_message = session.messages[-1] if session.messages else None

                if last_message and last_message.sender == session.buyer_agent_id:
                    current_agent = agents[AgentRole.SELLER]
                    role = "seller"
                else:
                    current_agent = agents[AgentRole.BUYER]
                    role = "buyer"

                turn_context = {
                    **stored_context,
                    **(context or {}),
                    "last_price": (
                        last_message.price
                        if last_message
                        else stored_context.get("starting_price", 500.0)
                    ),
                    "turn": len(session.messages) + 1,
                    "role": role,
                }

                try:
                    response = await current_agent.generate_response(turn_context)
                    session.messages.append(response)
                    messages.append(response)
                    turn_count += 1

                    # Persist each message to SQLite immediately
                    await self._persist_message(session_id, response)

                    logger.info(
                        "Session %s Turn %d: %s -> %s @ ₹%.2f/unit | %s",
                        session_id,
                        turn_count,
                        role,
                        response.message_type.value,
                        response.price,
                        response.delivery_terms,
                    )

                    if response.message_type in (
                        MessageType.ACCEPT,
                        MessageType.REJECT,
                    ):
                        session.status = NegotiationSessionStatus.COMPLETED
                        outcome = "DEAL" if response.message_type == MessageType.ACCEPT else "NO_DEAL"
                        final_price = response.price if response.message_type == MessageType.ACCEPT else None
                        await update_session_status(
                            session_id=session_id,
                            status=session.status.value,
                            final_price=final_price,
                            outcome=outcome,
                        )
                        logger.info(
                            "Session %s completed: %s at ₹%.2f/unit",
                            session_id, outcome, final_price or 0,
                        )
                        break

                except Exception as e:
                    logger.error("Session %s turn error: %s", session_id, e)
                    session.status = NegotiationSessionStatus.FAILED
                    await update_session_status(
                        session_id=session_id,
                        status=session.status.value,
                        outcome="FAILED",
                    )
                    break

            if session.status == NegotiationSessionStatus.ACTIVE:
                session.status = NegotiationSessionStatus.COMPLETED
                await update_session_status(
                    session_id=session_id,
                    status=session.status.value,
                    outcome="MAX_TURNS",
                )
                logger.info(
                    "Session %s completed after max %d turns.",
                    session_id, turn_count,
                )

            return messages

    async def get_session(self, session_id: str) -> NegotiationSession:
        """Get session by ID. Loads from database if not in memory."""
        await self._ensure_initialised()
        # Check memory first
        if session_id in self.sessions:
            return self.sessions[session_id]
        # Load from database
        db_session = await load_session(session_id)
        if db_session is None:
            raise ValueError(f"Session {session_id} not found")
        session = self._dict_to_session(db_session)
        async with self._lock:
            self.sessions[session_id] = session
            self.session_locks.setdefault(session_id, asyncio.Lock())
            self.contexts.setdefault(
                session_id,
                {"starting_price": 500.0, "quantity": 100, "product": "Office chairs"},
            )
        return session

    async def list_sessions(self) -> list[NegotiationSession]:
        """List all sessions. Loads from database."""
        await self._ensure_initialised()
        db_sessions = await load_all_sessions()
        result = []
        for s in db_sessions:
            sid = s["session_id"]
            if sid in self.sessions:
                result.append(self.sessions[sid])
            else:
                session = self._dict_to_session(s)
                async with self._lock:
                    self.sessions[sid] = session
                    self.session_locks.setdefault(sid, asyncio.Lock())
                result.append(session)
        return result

    async def get_messages(self, session_id: str) -> list[NegotiationMessage]:
        """Get all messages for a session. Loads from database."""
        await self._ensure_initialised()
        # If session is in memory with messages, return those
        if session_id in self.sessions and self.sessions[session_id].messages:
            return self.sessions[session_id].messages.copy()
        # Otherwise load from DB
        from .db import load_messages as db_load_messages
        db_messages = await db_load_messages(session_id)
        if not db_messages:
            # Check if session exists at all
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")
        return [self._dict_to_message(m) for m in db_messages]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _persist_message(self, session_id: str, msg: NegotiationMessage) -> None:
        """Write a single message to SQLite."""
        await save_message(
            session_id=session_id,
            message_type=msg.message_type.value,
            sender=msg.sender,
            price=msg.price,
            quantity=msg.quantity,
            delivery_terms=msg.delivery_terms,
            timestamp=msg.timestamp,
            turn_number=msg.turn_number,
            notes=msg.notes,
        )

    def _get_session(self, session_id: str) -> NegotiationSession:
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        return self.sessions[session_id]

    def _get_agents(self, session_id: str) -> dict:
        if session_id not in self.agents:
            raise ValueError(f"Agents for session {session_id} not found")
        return self.agents[session_id]

    @staticmethod
    def _dict_to_session(d: dict) -> NegotiationSession:
        """Convert a DB dict back to a NegotiationSession model."""
        from .models import NegotiationSessionStatus
        return NegotiationSession(
            session_id=d["session_id"],
            buyer_agent_id=d["buyer_agent_id"],
            seller_agent_id=d["seller_agent_id"],
            status=NegotiationSessionStatus(d.get("status", "PENDING")),
            created_at=d["created_at"],
            messages=[
                NegotiationMessage(
                    message_type=MessageType(m["message_type"]),
                    sender=m["sender"],
                    price=m["price"],
                    quantity=m["quantity"],
                    delivery_terms=m["delivery_terms"],
                    timestamp=m["timestamp"],
                    turn_number=m["turn_number"],
                    notes=m.get("notes"),
                    session_id=m.get("session_id"),
                )
                for m in d.get("messages", [])
            ],
        )

    @staticmethod
    def _dict_to_message(d: dict) -> NegotiationMessage:
        """Convert a DB dict to a NegotiationMessage."""
        return NegotiationMessage(
            message_type=MessageType(d["message_type"]),
            sender=d["sender"],
            price=d["price"],
            quantity=d["quantity"],
            delivery_terms=d["delivery_terms"],
            timestamp=d["timestamp"],
            turn_number=d["turn_number"],
            notes=d.get("notes"),
            session_id=d.get("session_id"),
        )


# Global session manager instance
session_manager = SessionManager()
