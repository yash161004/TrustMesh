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

from fastapi import WebSocket

from .agents.buyer import BuyerAgent
from .agents.seller import SellerAgent
from .config import get_settings
from .db import (
    init_db,
    list_sessions_for_org,
    load_ledger_entries,
    load_session,
    get_ledger_sequence_count,
    save_ledger_entry,
    save_message,
    save_session,
    update_session_status,
    load_trust_report,
    save_trust_report,
    get_agent_reputation,
    update_agent_reputation_v2,
)
from .trust.engine import trust_engine
from .crypto.signing import get_public_key_b64, sign_message, sign_message_for_agent
from .identity.agent_card import get_or_create_agent_card, card_file_path, verify_agent_card
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


# ---------------------------------------------------------------------------
# WebSocket connection manager (Phase 4)
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Tracks active WebSocket connections per session and broadcasts updates."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(session_id, []).append(websocket)
        logger.info("WS connected: session=%s (total=%d)", session_id, len(self._connections[session_id]))

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        conns = self._connections.get(session_id, [])
        if websocket in conns:
            conns.remove(websocket)
            logger.info("WS disconnected: session=%s (remaining=%d)", session_id, len(conns))
        if not conns:
            self._connections.pop(session_id, None)

    async def broadcast(self, session_id: str, payload: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self._connections.get(session_id, []):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_id, ws)


ws_manager = ConnectionManager()


def _scenario_to_flat_context(s: NegotiationScenario) -> dict:
    """Flatten a NegotiationScenario into the context dict so that
    downstream consumers (the mock LLM, the agent's `_build_messages`)
    can access all scenario fields via the context."""
    item0 = s.line_items[0] if s.line_items else None
    return {
        "scenario": s.model_dump(),
        "scenario_product": item0.product_name if item0 else "",
        "scenario_quantity": item0.quantity if item0 else 1,
        "scenario_currency": s.currency,
        "scenario_market_ref": item0.market_reference_price if item0 else 0.0,
        "scenario_buyer_cap": item0.buyer_budget_cap if item0 else 0.0,
        "scenario_buyer_target": item0.buyer_target_price if item0 else 0.0,
        "scenario_seller_floor": item0.seller_floor_price if item0 else 0.0,
        "scenario_seller_ask": item0.seller_asking_price if item0 else 0.0,
        "scenario_delivery_days": s.delivery_preference_days,
        "scenario_standard_delivery": s.standard_delivery_days,
        "scenario_expedited_days": s.expedited_delivery_days,
        "scenario_expedited_premium": s.expedited_premium_per_unit,
        "starting_price": item0.seller_asking_price if item0 else 0.0,
        "quantity": item0.quantity if item0 else 1,
        "product": item0.product_name if item0 else "",
        "market_reference_price": item0.market_reference_price if item0 else 0.0,
        "buyer_target_price": item0.buyer_target_price if item0 else 0.0,
        "buyer_budget_cap": item0.buyer_budget_cap if item0 else 0.0,
        "seller_asking_price": item0.seller_asking_price if item0 else 0.0,
        "seller_floor_price": item0.seller_floor_price if item0 else 0.0,
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
        """Initialize database connection without pre-loading all sessions into memory."""
        if self._initialised:
            return
        async with self._lock:
            if self._initialised:
                return
            await init_db()
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
        buyer_identity_id: Optional[str] = None,
        seller_identity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
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
            user_id=user_id,
            org_id=org_id,
            buyer_agent_id=buyer_agent_id,
            seller_agent_id=seller_agent_id,
            buyer_identity_id=buyer_identity_id,
            seller_identity_id=seller_identity_id,
            status=NegotiationSessionStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )

        # Persist to SQLite
        await save_session(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            buyer_agent_id=buyer_agent_id,
            seller_agent_id=seller_agent_id,
            buyer_identity_id=buyer_identity_id,
            seller_identity_id=seller_identity_id,
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
            scenario = self.scenarios.get(session_id, DEFAULT_SCENARIO)
            stored_context = {**_scenario_to_flat_context(scenario), **self.contexts.get(session_id, {})}

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

            # --- Trigger Trust Evaluation Automatically ---
            if session.status == NegotiationSessionStatus.COMPLETED:
                try:
                    await self.evaluate_trust_for_session(session_id, update_reputation=True)
                except Exception as e:
                    logger.error(f"Failed to automatically evaluate trust for session {session_id}: {e}")

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

    async def list_sessions(self, org_id: str = None, limit: int = 50, offset: int = 0) -> list[NegotiationSession]:
        """List sessions from database for a specific org."""
        await self._ensure_initialised()
        db_sessions = await list_sessions_for_org(org_id, limit, offset)
        result = []
        for s in db_sessions:
            session = self._dict_to_session(s)
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
        org_id = getattr(session, "org_id", None) if session else None
        user_id = getattr(session, "user_id", None) if session else None

        if session:
            if msg.sender == session.buyer_agent_id:
                role = "buyer"
            elif msg.sender == session.seller_agent_id:
                role = "seller"

        # Sign the message per-agent using AgentCard key
        signature_b64 = None
        public_key_b64 = None
        if role and msg.sender:
            try:
                get_or_create_agent_card(
                    agent_id=msg.sender,
                    role=role,
                    org_id=org_id,
                    owner_user_id=user_id,
                )
                # Enforce AgentCard verification and org-tenancy check at message time
                c_path = card_file_path(msg.sender)
                if not verify_agent_card(c_path, expected_org_id=org_id):
                    raise ValueError(f"AgentCard org tenancy check failed for {msg.sender} (expected org_id={org_id})")

                msg_dict = msg.model_dump(mode="json")
                signature_b64, public_key_b64 = sign_message_for_agent(msg_dict, msg.sender)
                msg.signature = signature_b64
                msg.signer_public_key = public_key_b64
            except Exception as e:
                logger.warning("Failed to sign message: %s", e)

        items_json = [i.model_dump(mode="json") for i in msg.proposed_items] if hasattr(msg, "proposed_items") else []
        await save_message(
            session_id=session_id,
            message_type=msg.message_type.value,
            sender=msg.sender,
            proposed_items=items_json,
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

        # Broadcast to connected WebSocket clients (Phase 4)
        try:
            await ws_manager.broadcast(session_id, {
                "type": "new_message",
                "message": msg.model_dump(mode="json"),
            })
        except Exception as e:
            logger.warning("Failed to broadcast message: %s", e)

    def _get_session(self, session_id: str) -> NegotiationSession:
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        return self.sessions[session_id]

    def _get_agents(self, session_id: str) -> dict:
        """Get agents for a session."""
        if session_id not in self.agents:
            raise ValueError(f"Agents for session {session_id} not found")
        return self.agents[session_id]

    async def evaluate_trust_for_session(self, session_id: str, recompute: bool = False, update_reputation: bool = True) -> dict:
        """
        Evaluates and persists the TrustReport for a session.
        If recompute=False, returns cached report if it exists.
        If update_reputation=True and this is the FIRST computation, updates the live agent reputation scores.
        """
        await self._ensure_initialised()
        session = await self.get_session(session_id)

        # Serve cached result unless recompute is requested
        if not recompute:
            cached = await load_trust_report(session_id)
            if cached:
                return json.loads(cached["report_json"])

        # Fetch identities to get the base reputation scores
        buyer_reputation = await get_agent_reputation(session.buyer_agent_id) if session.buyer_agent_id else None
        seller_reputation = await get_agent_reputation(session.seller_agent_id) if session.seller_agent_id else None
        
        buyer_trust = buyer_reputation["trust_score"] if buyer_reputation else 0.75
        seller_trust = seller_reputation["trust_score"] if seller_reputation else 0.75

        # Full recompute (slow — runs all detectors including LLM calls)
        scenario = self.scenarios.get(session_id, DEFAULT_SCENARIO)
        report = await trust_engine.evaluate_session(
            session_id=session_id,
            messages=session.messages,
            buyer_agent_id=session.buyer_agent_id,
            seller_agent_id=session.seller_agent_id,
            scenario=scenario,
            buyer_trust_score=buyer_trust,
            seller_trust_score=seller_trust,
        )

        # Persist for future fast reads
        await save_trust_report(
            session_id=session_id,
            report_json=json.dumps(report.model_dump(mode="json")),
            evaluated_at=report.evaluated_at,
        )

        # Apply reputation update ONLY on first calculation if requested
        if update_reputation and not recompute:
            # Check cached again just in case there was a race condition
            cached = await load_trust_report(session_id)
            # Actually, save_trust_report uses UPSERT and doesn't tell us if it inserted.
            # But we already checked `cached` at the beginning of the function.
            if session.buyer_agent_id:
                await update_agent_reputation_v2(session.buyer_agent_id, report.buyer_score.violation_count)
            if session.seller_agent_id:
                await update_agent_reputation_v2(session.seller_agent_id, report.seller_score.violation_count)

        return report.model_dump(mode="json")

    @staticmethod
    def _dict_to_session(d: dict) -> NegotiationSession:
        """Convert a DB dict back to a NegotiationSession model."""
        from .models import NegotiationSessionStatus
        return NegotiationSession(
            session_id=d["session_id"],
            user_id=d.get("user_id"),
            org_id=d.get("org_id"),
            buyer_agent_id=d["buyer_agent_id"],
            seller_agent_id=d["seller_agent_id"],
            buyer_identity_id=d.get("buyer_identity_id"),
            seller_identity_id=d.get("seller_identity_id"),
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
