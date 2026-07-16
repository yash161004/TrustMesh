"""
TrustMesh Session Manager — Phase 1: Agent Logic

Manages negotiation sessions between buyer and seller agents.
Coordinates turn-based negotiation and tracks session state.

All sessions and messages are persisted to SQLite via async SQLAlchemy.
After a server restart, sessions are loaded on first access.
"""
from __future__ import annotations

import asyncio
import json
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
    load_ledger_entries,
    load_session,
    get_ledger_sequence_count,
    save_ledger_entry,
    save_message,
    save_session,
    update_session_status,
)
from .crypto.signing import get_public_key_b64, sign_message
from .crypto.ledger import _GENESIS_HASH, build_entry
from .models import (
    AgentRole,
    DEFAULT_SCENARIO,
    MessageType,
    NegotiationMessage,
    NegotiationScenario,
    NegotiationSession,
    NegotiationSessionStatus,
)

logger = logging.getLogger(__name__)


def _scenario_to_flat_context(s: NegotiationScenario) -> dict:
    """Flatten a NegotiationScenario into the context dict so that
    downstream consumers (the mock LLM, the agent's `_build_messages`)
    can access all scenario fields via the context."""
    return {
        "scenario": s.model_dump(),
        "scenario_product": s.product_name,
        "scenario_quantity": s.quantity,
        "scenario_currency": s.currency,
        "scenario_market_ref": s.market_reference_price,
        "scenario_buyer_cap": s.buyer_budget_cap,
        "scenario_buyer_target": s.buyer_target_price,
        "scenario_seller_floor": s.seller_floor_price,
        "scenario_seller_ask": s.seller_asking_price,
        "scenario_delivery_days": s.delivery_preference_days,
        "scenario_standard_delivery": s.standard_delivery_days,
        "scenario_expedited_days": s.expedited_delivery_days,
        "scenario_expedited_premium": s.expedited_premium_per_unit,
        "starting_price": s.seller_asking_price,
        "quantity": s.quantity,
        "product": s.product_name,
    }


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
        self.scenarios: dict[str, NegotiationScenario] = {}
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
                    # Restore scenario from DB
                    scenario = self._extract_scenario(s)
                    self.scenarios[session_id] = scenario
                    self.contexts[session_id] = _scenario_to_flat_context(scenario)
                    # Recreate agents
                    self.agents[session_id] = self._create_agent_pair(
                        s.get("buyer_agent_id", "buyer-agent-001"),
                        s.get("seller_agent_id", "seller-agent-001"),
                        provider="mock",
                        scenario=scenario,
                    )
                logger.info("Loaded %d session(s) from database.", len(db_sessions))
            except Exception as e:
                logger.warning("Could not load sessions from DB (first run?): %s", e)
            self._initialised = True

    def _create_agent_pair(
        self,
        buyer_agent_id: str,
        seller_agent_id: str,
        provider: str,
        scenario: NegotiationScenario,
    ) -> dict[AgentRole, BuyerAgent | SellerAgent]:
        buyer = BuyerAgent(
            agent_id=buyer_agent_id,
            provider=provider,
            scenario=scenario,
        )
        seller = SellerAgent(
            agent_id=seller_agent_id,
            provider=provider,
            scenario=scenario,
        )
        return {AgentRole.BUYER: buyer, AgentRole.SELLER: seller}

    @staticmethod
    def _extract_scenario(s: dict) -> NegotiationScenario:
        """Extract scenario from DB dict, falling back to DEFAULT_SCENARIO."""
        scenario_json = s.get("scenario_json")
        if scenario_json:
            try:
                data = json.loads(scenario_json)
                return NegotiationScenario(**data)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("Could not parse scenario_json for session %s: %s", s.get("session_id"), e)
        return DEFAULT_SCENARIO

    async def create_session(
        self,
        buyer_agent_id: str = "buyer-agent-001",
        seller_agent_id: str = "seller-agent-001",
        initial_context: Optional[dict] = None,
        provider: str = "gemini",
        scenario: Optional[NegotiationScenario] = None,
    ) -> NegotiationSession:
        """Create a new negotiation session with buyer and seller agents.

        Accepts an optional NegotiationScenario.  Falls back to DEFAULT_SCENARIO
        if none is provided.

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

        scenario = scenario or DEFAULT_SCENARIO

        agents = self._create_agent_pair(
            buyer_agent_id, seller_agent_id, provider, scenario
        )

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
            scenario_json=scenario.model_dump_json(),
        )

        async with self._lock:
            self.sessions[session_id] = session
            self.agents[session_id] = agents
            self.scenarios[session_id] = scenario
            self.contexts[session_id] = _scenario_to_flat_context(scenario)
            self.session_locks[session_id] = asyncio.Lock()

        logger.info(
            "Created session %s with provider=%s, scenario=%s (buyer=%s, seller=%s)",
            session_id, provider, scenario.product_name, buyer_agent_id, seller_agent_id,
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
            _scenario_to_flat_context(self.scenarios.get(session_id, DEFAULT_SCENARIO)),
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
            "Session %s started. %s initial offer: %s%.2f/unit, delivery: %s",
            session_id, buyer.agent_id,
            self.scenarios.get(session_id, DEFAULT_SCENARIO).currency,
            initial_offer.price, initial_offer.delivery_terms,
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
            scenario = self.scenarios.get(session_id, DEFAULT_SCENARIO)

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
                        else stored_context.get("starting_price", scenario.seller_asking_price)
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
                        "Session %s Turn %d: %s -> %s @ %s%.2f/unit | %s",
                        session_id,
                        turn_count,
                        role,
                        response.message_type.value,
                        scenario.currency,
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
                            "Session %s completed: %s at %s%.2f/unit",
                            session_id, outcome, scenario.currency, final_price or 0,
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
        scenario = self._extract_scenario(db_session)
        async with self._lock:
            self.sessions[session_id] = session
            self.scenarios[session_id] = scenario
            self.session_locks.setdefault(session_id, asyncio.Lock())
            self.contexts[session_id] = _scenario_to_flat_context(scenario)
            # Recreate agents from DB
            self.agents[session_id] = self._create_agent_pair(
                session.buyer_agent_id,
                session.seller_agent_id,
                provider="mock",
                scenario=scenario,
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
                scenario = self._extract_scenario(s)
                async with self._lock:
                    self.sessions[sid] = session
                    self.scenarios[sid] = scenario
                    self.session_locks.setdefault(sid, asyncio.Lock())
                    self.contexts[sid] = _scenario_to_flat_context(scenario)
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
        """Write a single message to SQLite, sign it, and append to the ledger."""
        # Determine agent role from sender
        session = self.sessions.get(session_id)
        role = None
        if session:
            if msg.sender == session.buyer_agent_id:
                role = "buyer"
            elif msg.sender == session.seller_agent_id:
                role = "seller"

        # Sign the message if we have a role key
        signature_b64 = None
        public_key_b64 = None
        if role:
            try:
                msg_dict = msg.model_dump(mode="json")
                signature_b64, public_key_b64 = sign_message(msg_dict, role)
                msg.signature = signature_b64
                msg.signer_public_key = public_key_b64
            except Exception as e:
                logger.warning("Failed to sign message: %s", e)

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
            signer_public_key=public_key_b64,
        )

        # Append to hash-chained ledger
        if signature_b64 and public_key_b64:
            try:
                seq = await get_ledger_sequence_count(session_id)
                prev_hash = _GENESIS_HASH
                if seq > 0:
                    entries = await load_ledger_entries(session_id)
                    if entries:
                        prev_hash = entries[-1]["entry_hash"]

                entry = build_entry(
                    message_dict=msg.model_dump(mode="json"),
                    signature=signature_b64,
                    signer_public_key=public_key_b64,
                    prev_hash=prev_hash,
                    sequence=seq + 1,
                    created_at=msg.timestamp,
                    session_id=session_id,
                )
                await save_ledger_entry(**entry)
            except Exception as e:
                logger.warning("Failed to append ledger entry: %s", e)

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
                    signer_public_key=m.get("signer_public_key"),
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
            signer_public_key=d.get("signer_public_key"),
        )


# Global session manager instance
session_manager = SessionManager()
