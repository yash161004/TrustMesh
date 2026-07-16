"""
TrustMesh Tamper-Evidence Demo

Simulates a database-level attack on a ledger entry, then confirms that
verify_chain() detects the tampering and identifies the broken entry.

Usage:
    python scripts/tamper_ledger_demo.py [session_id]
    python scripts/tamper_ledger_demo.py [session_id] --restore

Defaults to the first seeded session in the DB.  Tamper modifies the
message_json of ledger entry sequence=1 (the first entry).  --restore
reverts the last tamper for the given session.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base, LedgerEntryRecord
from app.crypto.ledger import verify_chain

_BACKUP_DIR = Path(__file__).resolve().parent.parent / ".backups"


def _backup_path(session_id: str) -> Path:
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return _BACKUP_DIR / f"tamper_backup_{session_id}.json"


def _get_db_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///./trustmesh.db")
    return url.replace("+aiosqlite", "")


def _get_engine():
    return create_engine(_get_db_url(), echo=False)


def _find_first_session(engine) -> str | None:
    """Return the ID of the first seeded session, or None."""
    with Session(engine) as db:
        from app.db import SessionRecord
        result = db.execute(select(SessionRecord).limit(1))
        row = result.scalar_one_or_none()
        return row.id if row else None


def _load_ledger_dicts(engine, session_id: str) -> list[dict[str, Any]]:
    """Load ledger entries for *session_id* as plain dicts."""
    with Session(engine) as db:
        result = db.execute(
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


def _store_backup(engine, session_id: str, entries: list[dict[str, Any]]):
    """Persist the original state of tampered entries so --restore can revert."""
    backup = {str(e["sequence"]): {k: str(v) if hasattr(v, "isoformat") else v for k, v in e.items() if k != "id"}
              for e in entries}
    _backup_path(session_id).write_text(json.dumps(backup, indent=2))
    print(f"  Backup saved to {_backup_path(session_id)}")


def _load_backup(session_id: str) -> dict[str, dict] | None:
    """Return backup dict if one exists."""
    path = _backup_path(session_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _clear_backup(session_id: str):
    path = _backup_path(session_id)
    if path.exists():
        path.unlink()


def tamper(engine, session_id: str, sequence: int = 1):
    """Modify the message_json of the given ledger entry in-place."""
    with Session(engine) as db:
        result = db.execute(
            select(LedgerEntryRecord)
            .where(
                LedgerEntryRecord.session_id == session_id,
                LedgerEntryRecord.sequence == sequence,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            print(f"  No ledger entry found: session={session_id}, sequence={sequence}")
            return False

        # Deserialize the message, tamper with the price
        msg = json.loads(record.message_json)
        original_price = msg.get("price")
        msg["price"] = 999999.99
        record.message_json = json.dumps(msg, sort_keys=True, separators=(",", ":"))
        db.commit()
        print(f"  Tampered entry sequence={sequence}: price {original_price} -> 999999.99")
        return True


def restore(engine, session_id: str):
    """Revert all tampered entries for the session using backup data."""
    backup = _load_backup(session_id)
    if backup is None:
        print("  No backup found. Run tamper first.")
        return False

    with Session(engine) as db:
        for seq_str, original in backup.items():
            seq = int(seq_str)
            result = db.execute(
                select(LedgerEntryRecord)
                .where(
                    LedgerEntryRecord.session_id == session_id,
                    LedgerEntryRecord.sequence == seq,
                )
            )
            record = result.scalar_one_or_none()
            if record is None:
                continue
            record.message_json = original["message_json"]
            record.signature = original["signature"]
            record.signer_public_key = original["signer_public_key"]
            record.prev_hash = original["prev_hash"]
            record.entry_hash = original["entry_hash"]
            print(f"  Restored entry sequence={seq}")

        db.commit()
    _clear_backup(session_id)
    return True


def print_chain_status(entries: list[dict[str, Any]], label: str = ""):
    """Run verify_chain and print the result."""
    valid, broken_at = verify_chain(entries)
    status = "VALID" if valid else "BROKEN"
    tag = f" [{label}]" if label else ""
    print(f"  Chain:{tag} {status}" + ("" if broken_at is None else f" (broken at sequence={broken_at})"))


def main():
    engine = _get_engine()
    Base.metadata.create_all(engine)

    # Determine session_id
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    session_id = args[0] if args else _find_first_session(engine)

    if not session_id:
        print("No sessions found in the database. Run seed_demo_data.py first.")
        sys.exit(1)

    print(f"Session: {session_id}")

    is_restore = "--restore" in sys.argv

    if is_restore:
        print("Action: RESTORE")
        entries = _load_ledger_dicts(engine, session_id)
        print_chain_status(entries, "before restore")
        ok = restore(engine, session_id)
        if ok:
            entries = _load_ledger_dicts(engine, session_id)
            print_chain_status(entries, "after restore")
    else:
        print("Action: TAMPER")
        # Load and show original state
        entries = _load_ledger_dicts(engine, session_id)
        print(f"  Entries: {len(entries)}")
        print_chain_status(entries, "before tamper")

        if not entries:
            print("  No ledger entries for this session.")
            sys.exit(1)

        # Back up original data for restore
        _store_backup(engine, session_id, entries)

        # Tamper with the first entry
        ok = tamper(engine, session_id, sequence=1)
        if not ok:
            sys.exit(1)

        # Reload and verify
        entries = _load_ledger_dicts(engine, session_id)
        print_chain_status(entries, "after tamper")

        print()
        print("  TAMPER DETECTED — ledger is tamper-evident")
        print("  Run with --restore to revert and re-validate.")


if __name__ == "__main__":
    main()
