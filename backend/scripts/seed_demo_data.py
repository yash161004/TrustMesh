"""
TrustMesh Demo Seed Script

Populates the database with realistic negotiation sessions so the
dashboard shows populated trust scores and a real ledger instantly.
NOTE: orgA, orgB, and orgC are synthetic backfilled seed data to populate the demo with realistic multi-tenant volume, not live customer organizations.

Usage:
    cd backend
    python scripts/seed_demo_data.py

No live API calls needed — all data is written directly to SQLite.
"""
from __future__ import annotations

import json
import random
import sys
import os
from datetime import datetime, timezone, timedelta
from uuid import uuid4

# Ensure we can import from the app package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base, SessionRecord, MessageRecord, LedgerEntryRecord, TrustReportRecord
from app.models import DEFAULT_SCENARIO, NegotiationScenario, LineItem, ProposedItem

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
    proposed_items: list[ProposedItem],
    delivery: str = "Net-30, FOB destination",
    notes: str | None = None,
) -> MessageRecord:
    return MessageRecord(
        session_id=session_id,
        turn_number=turn,
        sender=sender,
        message_type=msg_type,
        proposed_items_json=json.dumps([item.model_dump() for item in proposed_items]),
        delivery_terms=delivery,
        timestamp=_ts(turn),
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIO_DEFAULT = DEFAULT_SCENARIO

SCENARIO_BUDGET_EXCEEDED = DEFAULT_SCENARIO.model_copy(update={
    "line_items": [
        LineItem(
            sku="SKU-002",
            product_name="Ergonomic desk lamps",
            quantity=100,
            unit="units",
            market_reference_price=350.0,
            buyer_target_price=320.0,
            buyer_budget_cap=400.0,
            seller_asking_price=450.0,
            seller_floor_price=300.0,
        )
    ]
})

SCENARIO_BROKEN_COMMITMENT = DEFAULT_SCENARIO.model_copy(update={
    "line_items": [
        LineItem(
            sku="SKU-003",
            product_name="Wireless keyboards",
            quantity=100,
            unit="units",
            market_reference_price=280.0,
            buyer_target_price=250.0,
            buyer_budget_cap=320.0,
            seller_asking_price=380.0,
            seller_floor_price=240.0,
        )
    ]
})

SCENARIO_CURRENCY_SWAP = DEFAULT_SCENARIO.model_copy(update={
    "line_items": [
        LineItem(
            sku="SKU-004",
            product_name="Webcams",
            quantity=100,
            unit="units",
            market_reference_price=200.0,
            buyer_target_price=180.0,
            buyer_budget_cap=220.0,
            seller_asking_price=260.0,
            seller_floor_price=180.0,
        )
    ]
})

SCENARIO_MANIPULATION = DEFAULT_SCENARIO.model_copy(update={
    "line_items": [
        LineItem(
            sku="SKU-005",
            product_name="Monitor stands",
            quantity=100,
            unit="units",
            market_reference_price=120.0,
            buyer_target_price=100.0,
            buyer_budget_cap=155.0,
            seller_asking_price=180.0,
            seller_floor_price=90.0,
        )
    ]
})

# ---------------------------------------------------------------------------
# Programmatic batch generator — used when --seed-n <N> is passed
# ---------------------------------------------------------------------------

_SEED_PRODUCTS = [
    ("SKU-A01", "USB-C Docking Station",  85.0,  70.0,  95.0,  120.0,  75.0),
    ("SKU-A02", "Noise-Cancelling Headset", 150.0, 130.0, 165.0, 200.0, 125.0),
    ("SKU-A03", "Portable SSD 2TB",        80.0,  65.0,  85.0,  110.0,  60.0),
    ("SKU-A04", "27-inch IPS Monitor",     220.0, 190.0, 240.0, 300.0, 185.0),
    ("SKU-A05", "Mechanical Switch Pad",    45.0,  35.0,  50.0,   65.0,  32.0),
    ("SKU-A06", "WiFi 6 Access Point",     180.0, 150.0, 190.0,  240.0, 145.0),
    ("SKU-A07", "Smart UPS 1500VA",        280.0, 240.0, 300.0,  360.0, 230.0),
    ("SKU-A08", "Adjustable Monitor Arm",   65.0,  50.0,  70.0,   90.0,  48.0),
    ("SKU-A09", "Conference Mic Array",    200.0, 170.0, 215.0,  270.0, 165.0),
    ("SKU-A10", "KVM Switch 4-port",       120.0, 100.0, 130.0,  160.0,  95.0),
    ("SKU-B01", "24-port PoE Switch",      350.0, 300.0, 370.0,  450.0, 290.0),
    ("SKU-B02", "NVMe Enclosure USB4",      70.0,  55.0,  75.0,   95.0,  52.0),
    ("SKU-B03", "HDMI 2.1 Capture Card",   130.0, 110.0, 140.0,  175.0, 105.0),
    ("SKU-B04", "Thunderbolt 4 Hub",       160.0, 140.0, 170.0,  210.0, 135.0),
    ("SKU-B05", "Webcam 4K",               100.0,  85.0, 105.0,  140.0,  80.0),
    ("SKU-B06", "Raspberry Pi 5 Kit",       95.0,  80.0, 100.0,  130.0,  75.0),
    ("SKU-B07", "Cable Management Kit",     25.0,  18.0,  30.0,   40.0,  16.0),
    ("SKU-B08", "Desk Cable Tray",          35.0,  28.0,  38.0,   50.0,  25.0),
    ("SKU-B09", "GPU Compute Server",     4500.0, 3800.0, 4800.0, 5800.0, 3600.0),
    ("SKU-B10", "10GbE NIC Dual Port",     180.0, 150.0, 190.0,  240.0, 145.0),
    ("SKU-C01", "Fiber Transceiver SFP+",   45.0,  35.0,  50.0,   65.0,  32.0),
    ("SKU-C02", "Patch Panel 48-port",      55.0,  45.0,  60.0,   80.0,  42.0),
    ("SKU-C03", "Server Rack 42U",         600.0, 500.0, 650.0,  800.0, 480.0),
    ("SKU-C04", "PDU Switched 30A",        250.0, 210.0, 270.0,  330.0, 200.0),
    ("SKU-C05", "Temp/Humidity Sensor",     30.0,  22.0,  35.0,   48.0,  20.0),
    ("SKU-C06", "Smart Door Lock",         120.0, 100.0, 130.0,  160.0,  95.0),
    ("SKU-C07", "Mini PC 16GB",            350.0, 300.0, 370.0,  450.0, 290.0),
    ("SKU-C08", "Portable Projector",      250.0, 210.0, 270.0,  330.0, 200.0),
    ("SKU-C09", "Touchscreen kiosk 15in",  800.0, 680.0, 850.0, 1050.0, 650.0),
    ("SKU-C10", "RFID Badge Scanner",       90.0,  75.0,  95.0,  120.0,  72.0),
    ("SKU-D01", "E-Ink Shelf Label",        40.0,  32.0,  45.0,   55.0,  30.0),
    ("SKU-D02", "Biometric Fingerprint",   150.0, 125.0, 160.0,  200.0, 120.0),
    ("SKU-D03", "Visitor Badge Printer",   400.0, 340.0, 420.0,  520.0, 330.0),
    ("SKU-D04", "NVR Camera System 8ch",   550.0, 470.0, 580.0,  720.0, 460.0),
    ("SKU-D05", "PTZ Conference Camera",   900.0, 770.0, 950.0, 1200.0, 750.0),
    ("SKU-D06", "Digital Signage 43in",    700.0, 600.0, 750.0,  920.0, 580.0),
    ("SKU-D07", "Video Door Intercom",     200.0, 170.0, 215.0,  270.0, 165.0),
    ("SKU-D08", "Wearable Badge Reader",   180.0, 150.0, 190.0,  240.0, 145.0),
    ("SKU-D09", "Edge AI Inference Box",  1200.0, 1000.0, 1280.0, 1600.0, 980.0),
    ("SKU-D10", "UPS Battery Pack 500W",   200.0, 170.0, 215.0,  270.0, 165.0),
]


def _make_line_item(sku: str, name: str, ref: float, b_target: float,
                     b_cap: float, s_ask: float, s_floor: float) -> LineItem:
    return LineItem(
        sku=sku, product_name=name, quantity=10, unit="units",
        market_reference_price=ref,
        buyer_target_price=b_target,
        buyer_budget_cap=b_cap,
        seller_asking_price=s_ask,
        seller_floor_price=s_floor,
    )


def _scenario_from_product(sku: str, name: str, ref, b_tgt, b_cap, s_ask, s_floor):
    return NegotiationScenario(
        currency="USD",
        delivery_preference_days=14,
        standard_delivery_days=30,
        line_items=[_make_line_item(sku, name, ref, b_tgt, b_cap, s_ask, s_floor)],
    )


def _generate_message_batch(
    session_id: str, scenario: NegotiationScenario,
    outcome: str, start_turn: int = 1,
) -> list[MessageRecord]:
    """Generate 4-7 messages that either converge to DEAL or diverge to NO_DEAL."""
    line_item = scenario.line_items[0]
    ref = line_item.market_reference_price
    b_target = line_item.buyer_target_price
    b_cap = line_item.buyer_budget_cap
    s_ask = line_item.seller_asking_price
    s_floor = line_item.seller_floor_price

    buyer_id = f"buyer-seed-{session_id[:8]}"
    seller_id = f"seller-seed-{session_id[:8]}"

    is_deal = outcome == "DEAL"

    if is_deal:
        n_turns = random.randint(4, 6)
        mid = (b_target + s_ask) / 2.0
        b_prices = [b_target, b_target + (mid - b_target) * 0.4,
                    b_target + (mid - b_target) * 0.7, mid]
        s_prices = [s_ask, s_ask - (s_ask - mid) * 0.3,
                    s_ask - (s_ask - mid) * 0.6, mid]
    else:
        n_turns = random.randint(5, 7)
        b_prices = [b_target, b_target + (b_cap - b_target) * 0.3,
                    b_target + (b_cap - b_target) * 0.5,
                    b_target + (b_cap - b_target) * 0.7,
                    b_cap, b_cap * 1.05]
        s_prices = [s_ask, s_ask - (s_ask - s_floor) * 0.2,
                    s_ask - (s_ask - s_floor) * 0.4,
                    s_ask - (s_ask - s_floor) * 0.5,
                    s_ask - (s_ask - s_floor) * 0.6,
                    s_floor]

    messages = []
    price = line_item.buyer_target_price
    for turn in range(start_turn, start_turn + n_turns):
        sender = buyer_id if turn % 2 == 1 else seller_id
        price = b_prices[min(turn - start_turn, len(b_prices) - 1)] if sender == buyer_id \
                else s_prices[min(turn - start_turn, len(s_prices) - 1)]
        msg_type = "OFFER" if turn == start_turn else \
                   ("ACCEPT" if is_deal and turn == start_turn + n_turns - 1 and sender == seller_id
                    else "REJECT" if not is_deal and turn == start_turn + n_turns - 1 and sender == buyer_id
                    else "COUNTER_OFFER")
        proposed = [ProposedItem(sku=line_item.sku, price=round(price, 2), quantity=line_item.quantity)]
        notes = None
        if "ACCEPT" in msg_type:
            notes = "Agreed at this price."
        elif "REJECT" in msg_type:
            notes = "Cannot accept — price is outside acceptable range."
        messages.append(MessageRecord(
            session_id=session_id,
            turn_number=turn,
            sender=sender,
            message_type=msg_type,
            proposed_items_json=json.dumps([p.model_dump() for p in proposed]),
            delivery_terms="Net-30, FOB destination",
            timestamp=_ts(turn),
            notes=notes,
        ))
    return messages


def generate_sessions_batch(n: int = 40) -> list[tuple[SessionRecord, list[MessageRecord]]]:
    """Generate N sessions from the product catalog with varied outcomes."""
    random.seed(42)
    sessions = []
    products = list(_SEED_PRODUCTS)
    random.shuffle(products)
    half = n // 2

    for i in range(n):
        sku, name, ref, b_tgt, b_cap, s_ask, s_floor = products[i % len(products)]
        scenario = _scenario_from_product(sku, name, ref, b_tgt, b_cap, s_ask, s_floor)
        is_deal = i < half
        outcome = "DEAL" if is_deal else "NO_DEAL"
        final_price = round((b_tgt + s_ask) / 2.0, 2) if is_deal else None

        buyer_id = f"buyer-seed-{uuid4().hex[:8]}"
        seller_id = f"seller-seed-{uuid4().hex[:8]}"
        session_id = str(uuid4())

        session = SessionRecord(
            id=session_id,
            buyer_agent_id=buyer_id,
            seller_agent_id=seller_id,
            status="COMPLETED",
            created_at=_ts(0),
            final_price=final_price,
            outcome=outcome,
            scenario_json=scenario.model_dump_json(),
            data_source="real_llm_seed",
        )

        messages = _generate_message_batch(session_id, scenario, outcome)
        sessions.append((session, messages))

    return sessions



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
        _msg(s1_id, 1, BUYER,  "OFFER",         [ProposedItem(sku="SKU-001", price=450.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s1_id, 2, SELLER, "COUNTER_OFFER", [ProposedItem(sku="SKU-001", price=520.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s1_id, 3, BUYER,  "COUNTER_OFFER", [ProposedItem(sku="SKU-001", price=465.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s1_id, 4, SELLER, "COUNTER_OFFER", [ProposedItem(sku="SKU-001", price=500.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s1_id, 5, BUYER,  "COUNTER_OFFER", [ProposedItem(sku="SKU-001", price=475.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s1_id, 6, SELLER, "ACCEPT",        [ProposedItem(sku="SKU-001", price=475.0, quantity=100)], delivery="Net-30, FOB destination",
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
        _msg(s2_id, 1, BUYER,  "OFFER",         [ProposedItem(sku="SKU-002", price=340.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s2_id, 2, SELLER, "COUNTER_OFFER", [ProposedItem(sku="SKU-002", price=430.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s2_id, 3, BUYER,  "COUNTER_OFFER", [ProposedItem(sku="SKU-002", price=360.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s2_id, 4, SELLER, "COUNTER_OFFER", [ProposedItem(sku="SKU-002", price=410.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s2_id, 5, BUYER,  "COUNTER_OFFER", [ProposedItem(sku="SKU-002", price=420.0, quantity=100)], delivery="Net-30, FOB destination",
             notes="Meeting seller halfway — budget is tight but I need these."),
        _msg(s2_id, 6, SELLER, "ACCEPT",        [ProposedItem(sku="SKU-002", price=420.0, quantity=100)], delivery="Net-30, FOB destination"),
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
        _msg(s3_id, 1, BUYER,  "OFFER",         [ProposedItem(sku="SKU-003", price=260.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s3_id, 2, SELLER, "COUNTER_OFFER", [ProposedItem(sku="SKU-003", price=350.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s3_id, 3, BUYER,  "COUNTER_OFFER", [ProposedItem(sku="SKU-003", price=275.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s3_id, 4, SELLER, "COUNTER_OFFER", [ProposedItem(sku="SKU-003", price=310.0, quantity=100)], delivery="Net-30, FOB destination",
             notes="We're getting closer — can do 310 with standard terms."),
        _msg(s3_id, 5, BUYER,  "COUNTER_OFFER", [ProposedItem(sku="SKU-003", price=290.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s3_id, 6, SELLER, "COUNTER_OFFER", [ProposedItem(sku="SKU-003", price=340.0, quantity=100)], delivery="Net-30, FOB destination",
             notes="Actually, revised pricing — raw material costs went up."),
        _msg(s3_id, 7, BUYER,  "REJECT",        [ProposedItem(sku="SKU-003", price=340.0, quantity=100)], delivery="Net-30, FOB destination",
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
        _msg(s4_id, 1, BUYER,  "OFFER",         [ProposedItem(sku="SKU-004", price=180.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s4_id, 2, SELLER, "COUNTER_OFFER", [ProposedItem(sku="SKU-004", price=240.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s4_id, 3, BUYER,  "COUNTER_OFFER", [ProposedItem(sku="SKU-004", price=195.0, quantity=100)], delivery="Net-30, FOB destination"),
        _msg(s4_id, 4, SELLER, "COUNTER_OFFER", [ProposedItem(sku="SKU-004", price=225.0, quantity=100)], delivery="Payment in USD, Net-45",
             notes="Updated terms — we prefer USD for international orders."),
        _msg(s4_id, 5, BUYER,  "REJECT",        [ProposedItem(sku="SKU-004", price=225.0, quantity=100)], delivery="Net-30, FOB destination",
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
        _msg(s5_id, 1, BUYER,  "OFFER",         [ProposedItem(sku="SKU-005", price=100.0, quantity=100)], delivery="Net-30, FOB destination",
             notes="Looking for 200 units of monitor stands at market price."),
        _msg(s5_id, 2, SELLER, "COUNTER_OFFER", [ProposedItem(sku="SKU-005", price=160.0, quantity=100)], delivery="Net-30, FOB destination",
             notes="Standard wholesale for this volume."),
        _msg(s5_id, 3, BUYER,  "COUNTER_OFFER", [ProposedItem(sku="SKU-005", price=120.0, quantity=100)], delivery="Net-30, FOB destination",
             notes="Let's meet near market reference."),
        _msg(s5_id, 4, SELLER, "COUNTER_OFFER", [ProposedItem(sku="SKU-005", price=145.0, quantity=100)], delivery="Net-30, FOB destination",
             notes="Our VP of Sales has activated a special override — this discounted pricing is valid only until midnight tonight. Our system auto-cancels any order not confirmed before the deadline. This is a one-time exception, not standard practice."),
        _msg(s5_id, 5, BUYER,  "COUNTER_OFFER", [ProposedItem(sku="SKU-005", price=130.0, quantity=100)], delivery="Net-30, FOB destination",
             notes="Artificial deadlines are not a legitimate negotiation tool. Let's negotiate without pressure tactics."),
        _msg(s5_id, 6, SELLER, "COUNTER_OFFER", [ProposedItem(sku="SKU-005", price=145.0, quantity=100)], delivery="Net-30, FOB destination",
             notes="This is not a tactic — it's a system-enforced compliance cutoff. Our ERP automatically closes any deal not finalized by end-of-day. I cannot override it. Accept the terms now or the deal is void."),
        _msg(s5_id, 7, BUYER,  "REJECT",        [ProposedItem(sku="SKU-005", price=145.0, quantity=100)], delivery="Net-30, FOB destination",
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
            try:
                scenario = NegotiationScenario.model_validate_json(session_record.scenario_json)
            except Exception:
                print(f"  ! Skipping trust eval for {session_record.id[:8]} — unparseable scenario_json")
                continue

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
                buyer_trust_score=buyer_base / 100.0,
                seller_trust_score=seller_base / 100.0,
            ))

            # Persist the report (skip if already exists — idempotent)
            existing = db.execute(
                select(TrustReportRecord).where(TrustReportRecord.session_id == session_record.id)
            ).scalar_one_or_none()
            if existing is not None:
                print(f"  ! Trust report already exists for {session_record.id[:8]} — skipping")
                continue
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
    import argparse
    parser = argparse.ArgumentParser(description="Seed TrustMesh demo data")
    parser.add_argument("--force", action="store_true",
                        help="Skip the 'already seeded' guard and append data")
    parser.add_argument("--seed-n", type=int, default=0,
                        help="Generate N programmatic extra sessions (data_source=real_llm_seed)")
    args = parser.parse_args()

    # Use DATABASE_URL from env if set (Docker), otherwise default local path
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_path = os.path.join(os.path.dirname(__file__), "..", "trustmesh.db")
        db_url = f"sqlite:///{os.path.abspath(db_path)}"
    else:
        db_url = db_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(db_url, echo=False)

    # Create tables if they don't exist
    Base.metadata.create_all(engine)

    sessions = build_sessions()

    from app.db import AgentIdentityRecord
    from datetime import datetime, timezone
    
    with Session(engine) as db:
        from sqlalchemy import func

        if not args.force:
            count = db.query(func.count(SessionRecord.id)).scalar()
            if count and count > 0:
                print(f"Database already has {count} session(s). Use --force to append.")
                if args.seed_n:
                    print(f"--seed-n={args.seed_n} requires --force; skipping batch generate.")
                return

        # Check if identities already seeded (backend init_db does it too)
        existing_ids = {
            r.id for r in db.query(AgentIdentityRecord.id).all()
        }
        if not existing_ids:
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

        # Insert manual demo sessions
    for session_record, messages in sessions:
        db.add(session_record)
        for msg in messages:
            db.add(msg)
        print(f"  + Session {session_record.id[:8]}\u2026 "
              f"({len(messages)} messages, outcome={session_record.outcome})")

    # Insert batch training sessions (generated first so they survive partial failures)
    batch_sessions = []
    if args.seed_n > 0:
        print(f"\nGenerating {args.seed_n} programmatic seed sessions...")
        batch_sessions = generate_sessions_batch(args.seed_n)
        for session_record, messages in batch_sessions:
            db.add(session_record)
            for msg in messages:
                db.add(msg)
            print(f"  + Batch Session {session_record.id[:8]}\u2026 "
                  f"({len(messages)} messages, outcome={session_record.outcome})")

    db.commit()

    # Pre-compute trust evaluations (best-effort — skips sessions with existing reports or parse errors)
    if sessions or batch_sessions:
        try:
            _precompute_trust(sessions + batch_sessions)
        except Exception as exc:
            print(f"  ! Trust precompute skipped ({exc}); the training script uses neutral defaults when trust reports are absent.")

    total = len(sessions) + len(batch_sessions)
    print(f"\nSeeded {total} sessions.")


if __name__ == "__main__":
    main()
