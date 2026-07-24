"""Vendored crypto primitives — self-contained, byte-compatible with the backend.

The SDK signs and hash-chains records that must verify under the TrustMesh
backend's own logic. Historically this module imported the backend package
directly (adding ``backend/`` to ``sys.path``) so there was provably no
divergence. That coupling meant the SDK could not be installed or used outside
the repository.

These primitives are now vendored here so the SDK is standalone. To keep the
"provably the same crypto" guarantee, ``tests/test_backend_parity.py`` imports
the backend's reference implementation alongside these and asserts byte-for-byte
identical output (canonical JSON, entry hashes) plus cross-verification of
signatures. That parity test runs in-repo; the runtime SDK depends only on
``cryptography``.

Reference: backend ``app/crypto/signing.py`` and ``app/crypto/ledger.py``.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)

GENESIS_HASH = "0" * 64  # sentinel prev_hash for the first entry


# ---------------------------------------------------------------------------
# Canonical JSON (must match backend exactly)
# ---------------------------------------------------------------------------
def canonical_json(obj: Any) -> bytes:
    """Serialize *obj* to deterministic JSON bytes (sorted keys, no whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _message_json(message_dict: dict[str, Any]) -> str:
    """The string form stored in a ledger entry (matches backend build_entry)."""
    return json.dumps(message_dict, sort_keys=True, separators=(",", ":"), default=str)


# ---------------------------------------------------------------------------
# Signature verification (signing is done by the watcher's own key object)
# ---------------------------------------------------------------------------
def verify_signature(
    message_dict: dict[str, Any],
    signature_b64: str,
    public_key_b64: str,
) -> bool:
    """Verify an Ed25519 signature over canonical_json(message). Never raises."""
    try:
        pub_bytes = base64.b64decode(public_key_b64)
        public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
        sig_bytes = base64.b64decode(signature_b64)
        public_key.verify(sig_bytes, canonical_json(message_dict))
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Hash-chained ledger (must match backend exactly)
# ---------------------------------------------------------------------------
def _compute_entry_hash(
    message_json: str,
    signature: str,
    signer_public_key: str,
    prev_hash: str,
    sequence: int,
) -> str:
    blob = canonical_json({
        "message_json": message_json,
        "signature": signature,
        "signer_public_key": signer_public_key,
        "prev_hash": prev_hash,
        "sequence": sequence,
    })
    return hashlib.sha256(blob).hexdigest()


def compute_entry_hash_from_dict(entry: dict[str, Any]) -> str:
    return _compute_entry_hash(
        message_json=entry["message_json"],
        signature=entry["signature"],
        signer_public_key=entry["signer_public_key"],
        prev_hash=entry["prev_hash"],
        sequence=entry["sequence"],
    )


def build_entry(
    message_dict: dict[str, Any],
    signature: str,
    signer_public_key: str,
    prev_hash: str,
    sequence: int,
    created_at: Optional[datetime] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """Build a ledger entry dict (not yet persisted)."""
    message_json = _message_json(message_dict)
    entry_hash = _compute_entry_hash(
        message_json, signature, signer_public_key, prev_hash, sequence
    )
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


def verify_chain(entries: list[dict[str, Any]]) -> tuple[bool, Optional[int]]:
    """Walk the chain and confirm each hash matches.

    Returns ``(is_valid, broken_at_sequence_or_None)``.
    """
    expected_prev = GENESIS_HASH
    for entry in entries:
        if entry["prev_hash"] != expected_prev:
            return False, entry["sequence"]
        if compute_entry_hash_from_dict(entry) != entry["entry_hash"]:
            return False, entry["sequence"]
        expected_prev = entry["entry_hash"]
    return True, None


__all__ = [
    "GENESIS_HASH",
    "canonical_json",
    "verify_signature",
    "build_entry",
    "verify_chain",
    "compute_entry_hash_from_dict",
]
