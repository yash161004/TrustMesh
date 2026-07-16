"""
Generate valid Ed25519-signed ledger entries for existing seeded sessions.

Run AFTER seed_demo_data.py — reads MessageRecords and builds a
hash-chained ledger from them so the Ledger panel has data.

Usage:
    python scripts/seed_ledger_entries.py [session_id]
    (omit session_id to seed all sessions)
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base, SessionRecord, MessageRecord, LedgerEntryRecord
from app.crypto.ledger import _GENESIS_HASH, build_entry
from app.crypto.signing import sign_message

_DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./trustmesh.db").replace("+aiosqlite", "")


def _get_engine():
    engine = create_engine(_DB_URL, echo=False)
    Base.metadata.create_all(engine)
    return engine


def _message_to_dict(msg: MessageRecord) -> dict:
    return {
        "message_type": msg.message_type,
        "sender": msg.sender,
        "price": msg.price,
        "quantity": msg.quantity,
        "delivery_terms": msg.delivery_terms,
        "turn_number": msg.turn_number,
        "notes": msg.notes or "",
    }


def seed_ledger_for_session(engine, session_id: str) -> int:
    """Generate and persist ledger entries for *session_id*. Returns count."""
    with Session(engine) as db:
        # Check existing count
        existing = db.execute(
            select(LedgerEntryRecord).where(LedgerEntryRecord.session_id == session_id)
        ).scalars().all()
        if existing:
            print(f"  Session {session_id}: {len(existing)} ledger entries already exist, skipping")
            return len(existing)

        # Load messages
        result = db.execute(
            select(MessageRecord)
            .where(MessageRecord.session_id == session_id)
            .order_by(MessageRecord.turn_number)
        )
        messages = result.scalars().all()
        if not messages:
            print(f"  Session {session_id}: no messages found")
            return 0

        # Figure out role from sender field
        buyer_id = None
        seller_id = None
        session_rec = db.execute(
            select(SessionRecord).where(SessionRecord.id == session_id)
        ).scalar_one_or_none()
        if session_rec:
            buyer_id = session_rec.buyer_agent_id
            seller_id = session_rec.seller_agent_id

        prev_hash = _GENESIS_HASH
        created = 0
        for i, msg in enumerate(messages):
            msg_dict = _message_to_dict(msg)

            # Determine signing role
            role = "buyer" if "buyer" in (msg.sender or "").lower() else "seller"
            try:
                sig, pub = sign_message(msg_dict, role)
            except Exception as e:
                print(f"  Warning: sign failed for turn {msg.turn_number}: {e}")
                sig, pub = f"sig-{i}", f"pub-{i}"

            entry = build_entry(
                message_dict=msg_dict,
                signature=sig,
                signer_public_key=pub,
                prev_hash=prev_hash,
                sequence=i + 1,
                created_at=msg.timestamp,
                session_id=session_id,
            )

            record = LedgerEntryRecord(
                session_id=session_id,
                sequence=entry["sequence"],
                message_json=entry["message_json"],
                signature=entry["signature"],
                signer_public_key=entry["signer_public_key"],
                prev_hash=entry["prev_hash"],
                entry_hash=entry["entry_hash"],
                created_at=entry["created_at"],
            )
            db.add(record)
            prev_hash = entry["entry_hash"]
            created += 1

        db.commit()
        print(f"  Session {session_id}: created {created} ledger entries")
        return created


def main():
    engine = _get_engine()

    target = sys.argv[1] if len(sys.argv) > 1 else None

    with Session(engine) as db:
        result = db.execute(select(SessionRecord))
        sessions = result.scalars().all()

    if not sessions:
        print("No sessions found. Run seed_demo_data.py first.")
        sys.exit(1)

    total = 0
    for s in sessions:
        if target and s.id != target:
            continue
        total += seed_ledger_for_session(engine, s.id)

    print(f"\nDone. Created {total} total ledger entries.")


if __name__ == "__main__":
    main()
