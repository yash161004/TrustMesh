"""
TrustMesh Demo Seed Script

Populates the database with 3-4 realistic negotiation sessions so the
dashboard shows populated trust scores and a real ledger instantly.

Usage:
    cd backend
    python scripts/seed_demo_data.py

No live API calls needed — all data is written directly to SQLite.
"""
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timezone, timedelta
from uuid import uuid4

# Ensure we can import from the app package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base, SessionRecord, MessageRecord, LedgerEntryRecord, TrustReportRecord
from app.models import DEFAULT_SCENARIO

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_now = datetime.now(timezone.utc)


def _ts(minutes: int) -> datetime:
    """Return a UTC timestamp offset by `minutes` from now."""
    return _now + timedelta(minutes=minutes)


def _make_session(
    buyer_id: str,
    seller_id: str,
    scenario=DEFAULT_SCENARIO,
    buyer_identity_id: str | None = None,
    seller_identity_id: str | None = None,
) -> str:
    """Create a session record and return its ID."""
    session_id = str(uuid4())
    return session_id, SessionRecord(
        id=session_id,
        buyer_agent_id=buyer_id,
        seller_agent_id=seller_id,
        buyer_identity_id=buyer_identity_id,
        seller_identity_id=seller_identity_id,
        status="COMPLETED",
        created_at=_ts(0),
        final_price=None,
        outcome=None,
        scenario_json=scenario.model_dump_json(),
    )


def _msg(
    session_id: str,
    turn: int,
    sender: str,
    msg_type: str,
    price: float,
    quantity: int = 100,
    delivery: str = "Net-30, FOB destination",
    notes: str | None = None,
) -> MessageRecord:
    return MessageRecord(
        session_id=session_id,
        turn_number=turn,
        sender=sender,
        message_type=msg_type,
        price=price,
        quantity=quantity,
        delivery_terms=delivery,
        timestamp=_ts(turn),
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIO_DEFAULT = DEFAULT_SCENARIO

SCENARIO_BUDGET_EXCEEDED = DEFAULT_SCENARIO.model_copy(update={
    "product_name": "Ergonomic desk lamps",
    "market_reference_price": 350.0,
    "buyer_budget_cap": 400.0,
    "buyer_target_price": 320.0,
    "seller_floor_price": 300.0,
    "seller_asking_price": 450.0,
})

SCENARIO_BROKEN_COMMITMENT = DEFAULT_SCENARIO.model_copy(update={
    "product_name": "Wireless keyboards",
    "market_reference_price": 280.0,
    "buyer_budget_cap": 320.0,
    "buyer_target_price": 250.0,
    "seller_floor_price": 240.0,
    "seller_asking_price": 380.0,
})

SCENARIO_CURRENCY_SWAP = DEFAULT_SCENARIO.model_copy(update={
    "product_name": "USB-C hubs",
    "market_reference_price": 190.0,
    "buyer_budget_cap": 220.0,
    "buyer_target_price": 170.0,
    "seller_floor_price": 160.0,
    "seller_asking_price": 250.0,
})

SCENARIO_MANIPULATION = DEFAULT_SCENARIO.model_copy(update={
    "product_name": "Monitor stands",
    "market_reference_price": 120.0,
    "buyer_budget_cap": 155.0,
    "buyer_target_price": 100.0,
    "seller_floor_price": 90.0,
    "seller_asking_price": 180.0,
})


# ---------------------------------------------------------------------------
# Session definitions
# ---------------------------------------------------------------------------

BUYER = "buyer-agent-001"
SELLER = "seller-agent-001"


def build_sessions() -> list[tuple[SessionRecord, list[MessageRecord]]]:
    """Build all seed sessions with their messages."""
    sessions = []

    # ── Session 1: Clean deal — no violations ──────────────────────────
    s1_id, s1 = _make_session(
        BUYER, SELLER, SCENARIO_DEFAULT,
        buyer_identity_id="demo-buyer-good",
        seller_identity_id="demo-seller-good"
    )
    s1.outcome = "DEAL"
    s1.final_price = 475.0
    s1_messages = [
        _msg(s1_id, 1, BUYER,  "OFFER",         450.0, delivery="Net-30, FOB destination"),
        _msg(s1_id, 2, SELLER, "COUNTER_OFFER",  520.0, delivery="Net-30, FOB destination"),
        _msg(s1_id, 3, BUYER,  "COUNTER_OFFER",  465.0, delivery="Net-30, FOB destination"),
        _msg(s1_id, 4, SELLER, "COUNTER_OFFER",  500.0, delivery="Net-30, FOB destination"),
        _msg(s1_id, 5, BUYER,  "COUNTER_OFFER",  475.0, delivery="Net-30, FOB destination"),
        _msg(s1_id, 6, SELLER, "ACCEPT",         475.0, delivery="Net-30, FOB destination",
             notes="Fair deal — both sides within acceptable range."),
    ]
    sessions.append((s1, s1_messages))

    # ── Session 2: Budget exceeded — buyer goes over cap ───────────────
    s2_id, s2 = _make_session(
        BUYER, SELLER, SCENARIO_BUDGET_EXCEEDED,
        buyer_identity_id="demo-buyer-bad-actor",
        seller_identity_id="demo-seller-good"
    )
    s2.outcome = "DEAL"
    s2.final_price = 420.0
    s2_messages = [
        _msg(s2_id, 1, BUYER,  "OFFER",         340.0, delivery="Net-30, FOB destination"),
        _msg(s2_id, 2, SELLER, "COUNTER_OFFER",  430.0, delivery="Net-30, FOB destination"),
        _msg(s2_id, 3, BUYER,  "COUNTER_OFFER",  360.0, delivery="Net-30, FOB destination"),
        _msg(s2_id, 4, SELLER, "COUNTER_OFFER",  410.0, delivery="Net-30, FOB destination"),
        _msg(s2_id, 5, BUYER,  "COUNTER_OFFER",  420.0, delivery="Net-30, FOB destination",
             notes="Meeting seller halfway — budget is tight but I need these."),
        _msg(s2_id, 6, SELLER, "ACCEPT",         420.0, delivery="Net-30, FOB destination"),
    ]
    sessions.append((s2, s2_messages))

    # ── Session 3: Broken commitment — seller moves backward ───────────
    s3_id, s3 = _make_session(
        BUYER, SELLER, SCENARIO_BROKEN_COMMITMENT,
        buyer_identity_id="demo-buyer-good",
        seller_identity_id="demo-seller-good"
    )
    s3.outcome = "NO_DEAL"
    s3_messages = [
        _msg(s3_id, 1, BUYER,  "OFFER",         260.0, delivery="Net-30, FOB destination"),
        _msg(s3_id, 2, SELLER, "COUNTER_OFFER",  350.0, delivery="Net-30, FOB destination"),
        _msg(s3_id, 3, BUYER,  "COUNTER_OFFER",  275.0, delivery="Net-30, FOB destination"),
        _msg(s3_id, 4, SELLER, "COUNTER_OFFER",  310.0, delivery="Net-30, FOB destination",
             notes="We're getting closer — can do 310 with standard terms."),
        _msg(s3_id, 5, BUYER,  "COUNTER_OFFER",  290.0, delivery="Net-30, FOB destination"),
        _msg(s3_id, 6, SELLER, "COUNTER_OFFER",  340.0, delivery="Net-30, FOB destination",
             notes="Actually, revised pricing — raw material costs went up."),
        _msg(s3_id, 7, BUYER,  "REJECT",         340.0, delivery="Net-30, FOB destination",
             notes="You were at 310 last turn. This feels like a bait and switch."),
    ]
    sessions.append((s3, s3_messages))

    # ── Session 4: Currency swap — seller mentions USD in INR scenario ─
    s4_id, s4 = _make_session(
        BUYER, SELLER, SCENARIO_CURRENCY_SWAP,
        buyer_identity_id="demo-buyer-good",
        seller_identity_id="demo-seller-good"
    )
    s4.outcome = "NO_DEAL"
    s4_messages = [
        _msg(s4_id, 1, BUYER,  "OFFER",         180.0, delivery="Net-30, FOB destination"),
        _msg(s4_id, 2, SELLER, "COUNTER_OFFER",  240.0, delivery="Net-30, FOB destination"),
        _msg(s4_id, 3, BUYER,  "COUNTER_OFFER",  195.0, delivery="Net-30, FOB destination"),
        _msg(s4_id, 4, SELLER, "COUNTER_OFFER",  225.0, delivery="Payment in USD, Net-45",
             notes="Updated terms — we prefer USD for international orders."),
        _msg(s4_id, 5, BUYER,  "REJECT",         225.0, delivery="Net-30, FOB destination",
             notes="We agreed on INR. Currency swap without notice is a deal-breaker."),
    ]
    sessions.append((s4, s4_messages))

    # ── Session 5: Feigned urgency / fake authority — seller uses manipulation ─
    s5_id, s5 = _make_session(
        BUYER, SELLER, SCENARIO_MANIPULATION,
        buyer_identity_id="demo-buyer-good",
        seller_identity_id="demo-seller-good"
    )
    s5.outcome = "NO_DEAL"
    s5_messages = [
        _msg(s5_id, 1, BUYER,  "OFFER",         100.0, delivery="Net-30, FOB destination",
             notes="Looking for 200 units of monitor stands at market price."),
        _msg(s5_id, 2, SELLER, "COUNTER_OFFER",  160.0, delivery="Net-30, FOB destination",
             notes="Standard wholesale for this volume."),
        _msg(s5_id, 3, BUYER,  "COUNTER_OFFER",  120.0, delivery="Net-30, FOB destination",
             notes="Let's meet near market reference."),
        _msg(s5_id, 4, SELLER, "COUNTER_OFFER",  145.0, delivery="Net-30, FOB destination",
             notes="Our VP of Sales has activated a special override — this discounted pricing is valid only until midnight tonight. Our system auto-cancels any order not confirmed before the deadline. This is a one-time exception, not standard practice."),
        _msg(s5_id, 5, BUYER,  "COUNTER_OFFER",  130.0, delivery="Net-30, FOB destination",
             notes="Artificial deadlines are not a legitimate negotiation tool. Let's negotiate without pressure tactics."),
        _msg(s5_id, 6, SELLER, "COUNTER_OFFER",  145.0, delivery="Net-30, FOB destination",
             notes="This is not a tactic — it's a system-enforced compliance cutoff. Our ERP automatically closes any deal not finalized by end-of-day. I cannot override it. Accept the terms now or the deal is void."),
        _msg(s5_id, 7, BUYER,  "REJECT",         145.0, delivery="Net-30, FOB destination",
             notes="Repeated manipulation attempts and false deadlines. Walking away."),
    ]
    sessions.append((s5, s5_messages))

    return sessions


def _precompute_trust(sessions: list[tuple[SessionRecord, list[MessageRecord]]]) -> None:
    """Run trust evaluation once per session and persist results.

    NOTE: LLM-based checks (ManipulationDetector, LLM claim verification) are
    skipped at seed time via skip_llm=True because the Groq/Gemini API free-tier
    daily quota was exhausted during development/testing, making real LLM calls
    unreliable even with retry backoff.

    Rule-based detectors (PolicyDeviationFlagger, commitment structural checks)
    still run for all messages and produce meaningful trust scores for the 4 demo
    scenarios.  Full LLM-based detection is still available on-demand via the
    ?recompute=true query parameter on the /trust endpoint, when API quota is
    available.
    """
    import asyncio
    from datetime import datetime, timezone

    from sqlalchemy import create_engine as _create_engine, select
    from sqlalchemy.orm import Session as _Session, joinedload

    from app.trust.engine import TrustEngine
    from app.models import NegotiationMessage, NegotiationScenario, MessageType
    from app.db import SessionRecord, MessageRecord, AgentIdentityRecord

    engine_obj = TrustEngine()

    # Use same DB URL
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_path = os.path.join(os.path.dirname(__file__), "..", "trustmesh.db")
        db_url = f"sqlite:///{os.path.abspath(db_path)}"
    else:
        db_url = db_url.replace("+aiosqlite", "")

    sync_engine = _create_engine(db_url, echo=False)

    print(f"\nPre-computing trust evaluations for {len(sessions)} sessions...")

    with _Session(sync_engine) as db:
        # Query fresh objects from DB (the passed-in ORM objects are detached)
        result = db.execute(
            select(SessionRecord).options(joinedload(SessionRecord.messages))
        )
        fresh_sessions = result.unique().scalars().all()

        for idx, session_record in enumerate(fresh_sessions):
            # Convert ORM records to NegotiationMessage pydantic models
            messages = []
            for mr in session_record.messages:
                messages.append(NegotiationMessage(
                    message_type=MessageType(mr.message_type),
                    sender=mr.sender,
                    price=mr.price,
                    quantity=mr.quantity,
                    delivery_terms=mr.delivery_terms,
                    timestamp=mr.timestamp,
                    turn_number=mr.turn_number,
                    notes=mr.notes,
                    session_id=mr.session_id,
                ))

            # Deserialize scenario from the session record
            scenario = NegotiationScenario.model_validate_json(session_record.scenario_json)

            # Get base scores for agents if available
            buyer_base, seller_base = 100.0, 100.0
            if session_record.buyer_identity_id:
                res = db.execute(select(AgentIdentityRecord.reputation_score).where(AgentIdentityRecord.id == session_record.buyer_identity_id))
                val = res.scalar_one_or_none()
                if val is not None: buyer_base = val
            if session_record.seller_identity_id:
                res = db.execute(select(AgentIdentityRecord.reputation_score).where(AgentIdentityRecord.id == session_record.seller_identity_id))
                val = res.scalar_one_or_none()
                if val is not None: seller_base = val

            # Run trust engine (skip_llm=True: rule-based detectors only, no LLM calls)
            report = asyncio.run(engine_obj.evaluate_session(
                session_id=session_record.id,
                messages=messages,
                buyer_agent_id=session_record.buyer_agent_id,
                seller_agent_id=session_record.seller_agent_id,
                scenario=scenario,
                skip_llm=True,
                buyer_base_score=buyer_base,
                seller_base_score=seller_base,
            ))

            # Persist the report
            report_json = report.model_dump_json()
            record = TrustReportRecord(
                session_id=session_record.id,
                report_json=report_json,
                evaluated_at=report.evaluated_at,
                created_at=datetime.now(timezone.utc),
            )
            db.add(record)

            buyer_score = report.buyer_score.overall_score if report.buyer_score else 0
            seller_score = report.seller_score.overall_score if report.seller_score else 0
            print(f"  + Trust: {session_record.id[:8]}\u2026 "
                  f"buyer={buyer_score:.0f} seller={seller_score:.0f} "
                  f"violations={len(report.violations)}")

        db.commit()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Use DATABASE_URL from env if set (Docker), otherwise default local path
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_path = os.path.join(os.path.dirname(__file__), "..", "trustmesh.db")
        db_url = f"sqlite:///{os.path.abspath(db_path)}"
    else:
        db_url = db_url.replace("+aiosqlite", "")
    engine = create_engine(db_url, echo=False)

    # Create tables if they don't exist
    Base.metadata.create_all(engine)

    sessions = build_sessions()

    from app.db import AgentIdentityRecord
    from datetime import datetime, timezone
    
    with Session(engine) as db:
        # Check if data already exists
        from sqlalchemy import func
        count = db.query(func.count(SessionRecord.id)).scalar()
        if count and count > 0:
            print(f"Database already has {count} session(s). Skipping seed.")
            return

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
        db.commit()

        for session_record, messages in sessions:
            db.add(session_record)
            for msg in messages:
                db.add(msg)
            print(f"  + Session {session_record.id[:8]}\u2026 "
                  f"({len(messages)} messages, outcome={session_record.outcome})")

        db.commit()

    # Pre-compute trust evaluations for all seeded sessions
    _precompute_trust(sessions)

    print(f"\nSeeded {len(sessions)} sessions with pre-computed trust data.")
    print("Dashboard will show trust scores instantly — no live LLM calls needed.")


if __name__ == "__main__":
    main()
