"""
TrustMesh Hash-Chained Ledger — append-only, tamper-evident.

Each signed message becomes a ledger entry containing the message, its
Ed25519 signature, a hash of the previous entry (prev_hash), and its own
hash (computed over the serialized contents + prev_hash).
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from .signing import canonical_json

logger = logging.getLogger(__name__)

_HASH_ALGO = "sha256"
_GENESIS_HASH = "0" * 64  # sentinel for the first entry


def _compute_entry_hash(
    message_json: str,
    signature: str,
    signer_public_key: str,
    prev_hash: str,
    sequence: int,
) -> str:
    """Deterministic hash over the entry's immutable fields."""
    blob = canonical_json({
        "message_json": message_json,
        "signature": signature,
        "signer_public_key": signer_public_key,
        "prev_hash": prev_hash,
        "sequence": sequence,
    })
    return hashlib.sha256(blob).hexdigest()


def compute_entry_hash_from_dict(entry: dict[str, Any]) -> str:
    """Recompute the entry hash from a ledger-entry dict (for verification)."""
    return _compute_entry_hash(
        message_json=entry["message_json"],
        signature=entry["signature"],
        signer_public_key=entry["signer_public_key"],
        prev_hash=entry["prev_hash"],
        sequence=entry["sequence"],
    )


def verify_chain(entries: list[dict[str, Any]]) -> tuple[bool, int | None]:
    """Walk the chain and confirm each hash matches.

    Returns (is_valid, broken_at_sequence_or_None).
    """
    expected_prev = _GENESIS_HASH
    for idx, entry in enumerate(entries):
        # Check prev_hash links
        if entry["prev_hash"] != expected_prev:
            return False, entry["sequence"]
        # Check own hash
        recomputed = compute_entry_hash_from_dict(entry)
        if recomputed != entry["entry_hash"]:
            return False, entry["sequence"]
        expected_prev = entry["entry_hash"]
    return True, None


def build_entry(
    message_dict: dict[str, Any],
    signature: str,
    signer_public_key: str,
    prev_hash: str,
    sequence: int,
    created_at: datetime | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Build a ledger entry dict (not yet persisted)."""
    message_json = json.dumps(message_dict, sort_keys=True, separators=(",", ":"), default=str)
    entry_hash = _compute_entry_hash(message_json, signature, signer_public_key, prev_hash, sequence)
    return {
        "session_id": session_id or message_dict.get("session_id"),
        "sequence": sequence,
        "message_json": message_json,
        "signature": signature,
        "signer_public_key": signer_public_key,
        "prev_hash": prev_hash,
        "entry_hash": entry_hash,
        "created_at": created_at or datetime.now(timezone.utc),
    }
