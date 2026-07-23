"""
TrustMesh Database Layer — Phase 1: Agent Logic

Async SQLAlchemy engine with tables for persisting negotiation sessions
and messages to SQLite (via aiosqlite).

Usage:
    from .db import init_db, get_session_db, get_messages_db
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import json
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    select,
    text,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, joinedload, relationship

from .config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------

class Organization(Base):
    """SaaS Organization / Tenant."""
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    clerk_org_id = Column(String(128), unique=True, nullable=False)
    plan_tier = Column(String(50), nullable=False, default="free")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class User(Base):
    """SaaS User."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clerk_user_id = Column(String(128), unique=True, nullable=False)
    email = Column(String(255), nullable=False)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    role = Column(String(50), nullable=False, default="standard")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization")



class AgentIdentityRecord(Base):
    """Persistent identity and reputation for agents across sessions."""
    __tablename__ = "agent_identities"

    id = Column(String(36), primary_key=True)  # UUID or string identifier
    role = Column(String(20), nullable=False)
    name = Column(String(128), nullable=False)
    reputation_score = Column(Float, nullable=False, default=100.0)
    session_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class AgentReputationRecord(Base):
    """Cross-session reputation layer for an agent."""
    __tablename__ = "agent_reputations"

    agent_id = Column(String(128), primary_key=True)
    trust_score = Column(Float, nullable=False, default=0.75)
    total_sessions = Column(Integer, nullable=False, default=0)
    violations_count = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime(timezone=True), nullable=False)


class SessionRecord(Base):
    """Persistent storage for negotiation sessions."""

    __tablename__ = "negotiation_sessions"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    buyer_agent_id = Column(String(128), nullable=False)
    seller_agent_id = Column(String(128), nullable=False)
    buyer_identity_id = Column(String(36), nullable=True)
    seller_identity_id = Column(String(36), nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")
    created_at = Column(DateTime(timezone=True), nullable=False)
    final_price = Column(Float, nullable=True)
    outcome = Column(String(20), nullable=True)  # "DEAL", "NO_DEAL", "FAILED"
    scenario_json = Column(Text, nullable=True)  # JSON-encoded NegotiationScenario
    tamper_alerted_at = Column(DateTime(timezone=True), nullable=True)
    data_source = Column(String(36), nullable=True, default="synthetic")  # "synthetic" or "real_llm_vX"

    messages = relationship(
        "MessageRecord",
        back_populates="session",
        order_by="MessageRecord.turn_number",
        cascade="all, delete-orphan",
    )


class MessageRecord(Base):
    """Persistent storage for individual negotiation messages."""

    __tablename__ = "negotiation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36), ForeignKey("negotiation_sessions.id"), nullable=False
    )
    message_type = Column(String(20), nullable=False)
    sender = Column(String(128), nullable=False)
    proposed_items_json = Column(Text, nullable=True)
    price = Column(Float, nullable=True, default=0.0)
    quantity = Column(Integer, nullable=True, default=1)
    delivery_terms = Column(String(512), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    turn_number = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    signer_public_key = Column(Text, nullable=True)

    session = relationship("SessionRecord", back_populates="messages")


class TrustReportRecord(Base):
    """Cached trust evaluation results for a session."""

    __tablename__ = "trust_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36), ForeignKey("negotiation_sessions.id"), unique=True, nullable=False
    )
    report_json = Column(Text, nullable=False)
    evaluated_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


class LedgerEntryRecord(Base):
    """Append-only hash-chained ledger for signed messages."""

    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36), ForeignKey("negotiation_sessions.id"), nullable=False
    )
    sequence = Column(Integer, nullable=False)
    message_json = Column(Text, nullable=False)
    signature = Column(Text, nullable=False)
    signer_public_key = Column(Text, nullable=False)
    prev_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

_async_engine = None
_async_session_factory = None
_db_initialised = False


async def init_db() -> None:
    """Create the database engine, tables, and session factory.

    Call once at application startup.  Safe to call multiple times —
    subsequent calls are no-ops.
    """
    global _async_engine, _async_session_factory, _db_initialised

    if _db_initialised:
        return

    settings = get_settings()
    database_url = settings.database_url

    # aiosqlite driver requires sqlite+aiosqlite:// prefix
    if database_url.startswith("sqlite://") and "aiosqlite" not in database_url:
        connect_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    elif database_url.startswith("postgresql://"):
        connect_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        connect_url = database_url

    _async_engine = create_async_engine(
        connect_url, 
        echo=False,
        connect_args={"prepared_statement_cache_size": 0} if "asyncpg" in connect_url else {}
    )

    # Create tables
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Migrations for existing tables missing new columns
    async with _async_engine.begin() as conn:
        for col_name, col_type_pg, col_type_lite in [
            ("scenario_json", "TEXT", "TEXT"),
            ("buyer_identity_id", "VARCHAR(36)", "TEXT"),
            ("seller_identity_id", "VARCHAR(36)", "TEXT"),
            ("tamper_alerted_at", "TIMESTAMP WITH TIME ZONE", "DATETIME"),
            ("data_source", "VARCHAR(36) DEFAULT 'real'", "TEXT DEFAULT 'real'"),
        ]:
            col_type = col_type_lite if _async_engine.dialect.name == "sqlite" else col_type_pg
            if _async_engine.dialect.name == "sqlite":
                res = await conn.execute(
                    text(f"SELECT COUNT(*) AS cnt FROM pragma_table_info('negotiation_sessions') WHERE name='{col_name}'")
                )
            else:
                res = await conn.execute(
                    text(f"SELECT COUNT(*) AS cnt FROM information_schema.columns WHERE table_name='negotiation_sessions' AND column_name='{col_name}'")
                )
            if res.one().cnt == 0:
                await conn.execute(text(f"ALTER TABLE negotiation_sessions ADD COLUMN {col_name} {col_type}"))
                logger.info(f"Added {col_name} column to negotiation_sessions.")

        # Check negotiation_messages missing columns
        for msg_col, col_type_pg, col_type_lite in [
            ("proposed_items_json", "TEXT", "TEXT"),
            ("delivery_terms", "VARCHAR(512)", "TEXT"),
            ("notes", "TEXT", "TEXT"),
            ("signer_public_key", "TEXT", "TEXT"),
            ("price", "DOUBLE PRECISION DEFAULT 0.0", "REAL DEFAULT 0.0"),
            ("quantity", "INTEGER DEFAULT 1", "INTEGER DEFAULT 1"),
        ]:
            col_type = col_type_lite if _async_engine.dialect.name == "sqlite" else col_type_pg
            if _async_engine.dialect.name == "sqlite":
                res = await conn.execute(
                    text(f"SELECT COUNT(*) AS cnt FROM pragma_table_info('negotiation_messages') WHERE name='{msg_col}'")
                )
            else:
                res = await conn.execute(
                    text(f"SELECT COUNT(*) AS cnt FROM information_schema.columns WHERE table_name='negotiation_messages' AND column_name='{msg_col}'")
                )
            if res.one().cnt == 0:
                await conn.execute(text(f"ALTER TABLE negotiation_messages ADD COLUMN {msg_col} {col_type}"))
                logger.info(f"Added {msg_col} column to negotiation_messages.")

    _async_session_factory = async_sessionmaker(
        _async_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Seed Agent Identities
    async with _async_session_factory() as db:
        result = await db.execute(select(AgentIdentityRecord).limit(1))
        if result.scalar_one_or_none() is None:
            now = datetime.now(timezone.utc)
            identities = [
                AgentIdentityRecord(
                    id="demo-buyer-bad-actor",
                    role="BUYER",
                    name="Demo Buyer (Bad Actor)",
                    reputation_score=65.0,
                    session_count=1,
                    created_at=now,
                    updated_at=now,
                ),
                AgentIdentityRecord(
                    id="demo-buyer-good",
                    role="BUYER",
                    name="Demo Buyer (Good)",
                    reputation_score=100.0,
                    session_count=0,
                    created_at=now,
                    updated_at=now,
                ),
                AgentIdentityRecord(
                    id="demo-seller-good",
                    role="SELLER",
                    name="Demo Seller (Good)",
                    reputation_score=100.0,
                    session_count=0,
                    created_at=now,
                    updated_at=now,
                ),
            ]
            db.add_all(identities)
            await db.commit()
            logger.info("Seeded initial agent identities.")

    # Seed Agent Reputations
    async with _async_session_factory() as db:
        result = await db.execute(select(AgentReputationRecord).limit(1))
        if result.scalar_one_or_none() is None:
            now = datetime.now(timezone.utc)
            reputations = [
                AgentReputationRecord(
                    agent_id="demo-buyer-bad-actor",
                    trust_score=0.3,  # Pre-degraded for testing
                    total_sessions=3,
                    violations_count=5,
                    last_updated=now,
                ),
                AgentReputationRecord(
                    agent_id="demo-buyer-good",
                    trust_score=0.75,
                    total_sessions=0,
                    violations_count=0,
                    last_updated=now,
                ),
                AgentReputationRecord(
                    agent_id="demo-seller-good",
                    trust_score=0.75,
                    total_sessions=0,
                    violations_count=0,
                    last_updated=now,
                ),
            ]
            db.add_all(reputations)
            await db.commit()
            logger.info("Seeded initial agent reputations.")

    _db_initialised = True
    logger.info("Database initialised: %s", database_url)


async def close_db() -> None:
    """Dispose of the database engine. Call at application shutdown."""
    global _async_engine, _db_initialised
    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
        _db_initialised = False
        logger.info("Database connection closed.")


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the configured async session factory."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _async_session_factory

async def get_session_db():
    """FastAPI dependency that provides an async DB session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Repository — session CRUD
# ---------------------------------------------------------------------------


async def save_session(
    session_id: str,
    buyer_agent_id: str,
    seller_agent_id: str,
    status: str,
    created_at: datetime,
    buyer_identity_id: Optional[str] = None,
    seller_identity_id: Optional[str] = None,
    final_price: Optional[float] = None,
    outcome: Optional[str] = None,
    scenario_json: Optional[str] = None,
    user_id: Optional[str] = None,
    org_id: Optional[str] = None,
    data_source: Optional[str] = "real",
) -> None:
    """Insert or update a session record."""
    factory = get_session_factory()
    async with factory() as db:
        # Check if session exists (for updates)
        result = await db.execute(select(SessionRecord).where(SessionRecord.id == session_id))
        existing = result.scalar_one_or_none()

        if existing:
            existing.status = status
            existing.final_price = final_price
            existing.outcome = outcome
            if buyer_identity_id is not None:
                existing.buyer_identity_id = buyer_identity_id
            if seller_identity_id is not None:
                existing.seller_identity_id = seller_identity_id
            if scenario_json is not None:
                existing.scenario_json = scenario_json
            if user_id is not None:
                existing.user_id = user_id
            if org_id is not None:
                existing.org_id = org_id
            if data_source is not None:
                existing.data_source = data_source
        else:
            new_session = SessionRecord(
                id=session_id,
                user_id=user_id,
                org_id=org_id,
                buyer_agent_id=buyer_agent_id,
                seller_agent_id=seller_agent_id,
                buyer_identity_id=buyer_identity_id,
                seller_identity_id=seller_identity_id,
                status=status,
                created_at=created_at,
                final_price=final_price,
                outcome=outcome,
                scenario_json=scenario_json,
                data_source=data_source,
            )
            db.add(new_session)
        await db.commit()


async def save_message(
    session_id: str,
    message_type: str,
    sender: str,
    proposed_items: list[dict],
    delivery_terms: str,
    timestamp: datetime,
    turn_number: int,
    notes: Optional[str] = None,
    signer_public_key: Optional[str] = None,
) -> int:
    # Convenience columns: extracts first line item only; see proposed_items_json for full multi-SKU list
    first_price = proposed_items[0].get("price", 0.0) if proposed_items else 0.0
    first_qty = proposed_items[0].get("quantity", 1) if proposed_items else 1
    factory = get_session_factory()
    async with factory() as db:
        record = MessageRecord(
            session_id=session_id,
            message_type=message_type,
            sender=sender,
            proposed_items_json=json.dumps(proposed_items),
            price=first_price,
            quantity=first_qty,
            delivery_terms=delivery_terms,
            timestamp=timestamp,
            turn_number=turn_number,
            notes=notes,
            signer_public_key=signer_public_key,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record.id


async def load_session(session_id: str) -> Optional[dict]:
    """Load a session and its messages from the database.

    Returns a dict matching NegotiationSession structure, or None.
    """
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(SessionRecord)
            .where(SessionRecord.id == session_id)
            .options(joinedload(SessionRecord.messages))
        )
        record = result.unique().scalar_one_or_none()
        if record is None:
            return None
        return _session_record_to_dict(record)


from sqlalchemy.orm import selectinload

async def list_sessions_for_org(org_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Load sessions for a specific org, with pagination."""
    factory = get_session_factory()
    async with factory() as db:
        # If org_id is provided, filter by it. If None, it might be an admin fetching all.
        stmt = select(SessionRecord).options(selectinload(SessionRecord.messages))
        
        if org_id:
            stmt = stmt.where(SessionRecord.org_id == org_id)
            
        stmt = stmt.order_by(SessionRecord.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(stmt)
        records = result.scalars().all()
        return [_session_record_to_dict(r) for r in records]


async def load_messages(session_id: str) -> list[dict]:
    """Load all messages for a session (ordered by turn_number)."""
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(MessageRecord)
            .where(MessageRecord.session_id == session_id)
            .order_by(MessageRecord.turn_number)
        )
        records = result.scalars().all()
        return [_message_record_to_dict(r) for r in records]


async def update_session_status(
    session_id: str,
    status: str,
    final_price: Optional[float] = None,
    outcome: Optional[str] = None,
) -> None:
    """Update session status, final_price, and/or outcome."""
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(select(SessionRecord).where(SessionRecord.id == session_id))
        record = result.scalar_one_or_none()
        if record:
            record.status = status
            if final_price is not None:
                record.final_price = final_price
            if outcome is not None:
                record.outcome = outcome
            await db.commit()


# ---------------------------------------------------------------------------
# Helpers — convert ORM records to dicts
# ---------------------------------------------------------------------------


def _session_record_to_dict(record: SessionRecord) -> dict:
    return {
        "session_id": record.id,
        "user_id": record.user_id,
        "org_id": record.org_id,
        "buyer_agent_id": record.buyer_agent_id,
        "seller_agent_id": record.seller_agent_id,
        "buyer_identity_id": record.buyer_identity_id,
        "seller_identity_id": record.seller_identity_id,
        "status": record.status,
        "created_at": record.created_at,
        "final_price": record.final_price,
        "outcome": record.outcome,
        "scenario_json": record.scenario_json,
        "data_source": getattr(record, "data_source", "real"),
        "messages": [
            _message_record_to_dict(m) for m in (record.messages or [])
        ],
    }


def _message_record_to_dict(record: MessageRecord) -> dict:
    return {
        "message_type": record.message_type,
        "sender": record.sender,
        "proposed_items": json.loads(record.proposed_items_json) if record.proposed_items_json else [],
        "delivery_terms": record.delivery_terms,
        "timestamp": record.timestamp,
        "turn_number": record.turn_number,
        "notes": record.notes,
        "session_id": record.session_id,
        "signer_public_key": record.signer_public_key,
    }


# ---------------------------------------------------------------------------
# Ledger CRUD
# ---------------------------------------------------------------------------


async def save_ledger_entry(
    session_id: str,
    sequence: int,
    message_json: str,
    signature: str,
    signer_public_key: str,
    prev_hash: str,
    entry_hash: str,
    created_at: datetime,
) -> None:
    """Append a ledger entry to the database."""
    factory = get_session_factory()
    async with factory() as db:
        record = LedgerEntryRecord(
            session_id=session_id,
            sequence=sequence,
            message_json=message_json,
            signature=signature,
            signer_public_key=signer_public_key,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            created_at=created_at,
        )
        db.add(record)
        await db.commit()


async def load_ledger_entries(session_id: str) -> list[dict]:
    """Load all ledger entries for a session, ordered by sequence."""
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(LedgerEntryRecord)
            .where(LedgerEntryRecord.session_id == session_id)
            .order_by(LedgerEntryRecord.sequence)
        )
        records = result.scalars().all()
        return [
            {
                "id": r.id,
                "session_id": r.session_id,
                "sequence": r.sequence,
                "message_json": r.message_json,
                "signature": r.signature,
                "signer_public_key": r.signer_public_key,
                "prev_hash": r.prev_hash,
                "entry_hash": r.entry_hash,
                "created_at": r.created_at,
            }
            for r in records
        ]


async def get_ledger_sequence_count(session_id: str) -> int:
    """Return the current sequence count for a session's ledger."""
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(LedgerEntryRecord)
            .where(LedgerEntryRecord.session_id == session_id)
            .order_by(LedgerEntryRecord.sequence.desc())
            .limit(1)
        )
        record = result.scalar_one_or_none()
        return record.sequence if record else 0


# ---------------------------------------------------------------------------
# Trust report CRUD
# ---------------------------------------------------------------------------


async def save_trust_report(
    session_id: str,
    report_json: str,
    evaluated_at: datetime,
) -> None:
    """Persist a computed trust report for a session (upsert)."""
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(TrustReportRecord).where(TrustReportRecord.session_id == session_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.report_json = report_json
            existing.evaluated_at = evaluated_at
            existing.created_at = datetime.now(timezone.utc)
        else:
            record = TrustReportRecord(
                session_id=session_id,
                report_json=report_json,
                evaluated_at=evaluated_at,
                created_at=datetime.now(timezone.utc),
            )
            db.add(record)
        await db.commit()


async def load_trust_report(session_id: str) -> Optional[dict]:
    """Load a cached trust report for a session. Returns None if not cached."""
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(TrustReportRecord).where(TrustReportRecord.session_id == session_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return {
            "session_id": record.session_id,
            "report_json": record.report_json,
            "evaluated_at": record.evaluated_at,
            "created_at": record.created_at,
        }

# ---------------------------------------------------------------------------
# Agent Identity CRUD & Reputation Updates
# ---------------------------------------------------------------------------

async def get_agent_identity(identity_id: str) -> Optional[dict]:
    """Load an AgentIdentity by ID."""
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(AgentIdentityRecord).where(AgentIdentityRecord.id == identity_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return {
            "id": record.id,
            "role": record.role,
            "name": record.name,
            "reputation_score": record.reputation_score,
            "session_count": record.session_count,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

async def get_all_agent_identities() -> list[dict]:
    """List all agent identities."""
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(select(AgentIdentityRecord))
        records = result.scalars().all()
        return [
            {
                "id": record.id,
                "role": record.role,
                "name": record.name,
                "reputation_score": record.reputation_score,
                "session_count": record.session_count,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            }
            for record in records
        ]

async def update_agent_reputation(identity_id: str, session_final_score: float) -> None:
    """Update agent reputation using exponential recency weighting."""
    if not identity_id:
        return
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(AgentIdentityRecord).where(AgentIdentityRecord.id == identity_id)
        )
        record = result.scalar_one_or_none()
        if record:
            new_reputation = (0.7 * session_final_score) + (0.3 * record.reputation_score)
            record.reputation_score = new_reputation
            record.session_count += 1
            record.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(
                "Updated reputation for %s to %.2f (session_count: %d)",
                identity_id, new_reputation, record.session_count
            )

async def get_agent_reputation(agent_id: str) -> dict:
    """Load an AgentReputation by ID, or return default values if missing."""
    if not agent_id:
        raise ValueError("Agent ID is required")
        
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(AgentReputationRecord).where(AgentReputationRecord.agent_id == agent_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            # Return default representation
            now = datetime.now(timezone.utc)
            return {
                "agent_id": agent_id,
                "trust_score": 0.75,
                "total_sessions": 0,
                "violations_count": 0,
                "last_updated": now,
            }
        return {
            "agent_id": record.agent_id,
            "trust_score": record.trust_score,
            "total_sessions": record.total_sessions,
            "violations_count": record.violations_count,
            "last_updated": record.last_updated,
        }

async def update_agent_reputation_v2(agent_id: str, session_violations: int) -> None:
    """Update cross-session agent reputation using flat penalty or slow recovery."""
    if not agent_id:
        return
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(AgentReputationRecord).where(AgentReputationRecord.agent_id == agent_id)
        )
        record = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        
        if record is None:
            record = AgentReputationRecord(
                agent_id=agent_id,
                trust_score=0.75,
                total_sessions=0,
                violations_count=0,
                last_updated=now,
            )
            db.add(record)
            
        if session_violations > 0:
            # Flat penalty per session with violations
            record.trust_score = max(0.0, record.trust_score - 0.1)
        else:
            # Clean session -> slow recovery
            record.trust_score = min(1.0, record.trust_score + 0.02)
            
        record.total_sessions += 1
        record.violations_count += session_violations
        record.last_updated = now
        await db.commit()
        logger.info(
            "Updated v2 reputation for %s to %.2f (total_sessions: %d, violations_count: %d)",
            agent_id, record.trust_score, record.total_sessions, record.violations_count
        )


async def claim_tamper_alert(session_id: str, alerted_at: Optional[datetime] = None) -> bool:
    """
    Atomically attempts to claim tamper alert ownership for a session in the database.
    Executes an atomic UPDATE SessionRecord SET tamper_alerted_at = :dt WHERE id = :session_id AND tamper_alerted_at IS NULL.
    Returns True if this call successfully claimed the alert (rowcount == 1), False if already claimed (existing tamper_alerted_at is not None).
    If session record does not exist in DB (e.g. synthetic test session), returns True on first claim.
    """
    factory = get_session_factory()
    dt = alerted_at or datetime.now(timezone.utc)
    async with factory() as db:
        res = await db.execute(
            update(SessionRecord)
            .where(SessionRecord.id == session_id, SessionRecord.tamper_alerted_at.is_(None))
            .values(tamper_alerted_at=dt)
        )
        await db.commit()
        if res.rowcount > 0:
            return True

        # Check if row exists with tamper_alerted_at already set
        check = await db.execute(
            select(SessionRecord.tamper_alerted_at).where(SessionRecord.id == session_id)
        )
        row = check.first()
        if row is not None:
            # Session exists in DB and tamper_alerted_at is already non-None
            return False

        # Session does not exist in DB (synthetic session) -> allow first claim
        return True

