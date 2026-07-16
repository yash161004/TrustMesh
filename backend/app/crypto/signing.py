"""
TrustMesh Signing Module — Ed25519 key management and message signing.

Provides deterministic serialization (canonical JSON), Ed25519 keypair
generation/loading per agent role, and sign/verify helpers.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

logger = logging.getLogger(__name__)

_KEYS_DIR = Path(__file__).resolve().parent.parent.parent / ".keys"

# Module-level cache: role -> (private_key, public_key_bytes)
_keypairs: dict[str, tuple[Ed25519PrivateKey, bytes]] = {}


# ---------------------------------------------------------------------------
# Canonical JSON serialization
# ---------------------------------------------------------------------------

def canonical_json(obj: Any) -> bytes:
    """Serialize *obj* to deterministic JSON bytes (sorted keys, no whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


# ---------------------------------------------------------------------------
# Keypair management
# ---------------------------------------------------------------------------

def _key_path(role: str) -> Path:
    return _KEYS_DIR / f"{role}.key"


def _pub_path(role: str) -> Path:
    return _KEYS_DIR / f"{role}.pub"


def generate_keypair(role: str) -> tuple[Ed25519PrivateKey, bytes]:
    """Generate a fresh Ed25519 keypair, persist it, and return (private_key, pub_bytes)."""
    _KEYS_DIR.mkdir(parents=True, exist_ok=True)

    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=Encoding.Raw,
        format=PublicFormat.Raw,
    )

    _key_path(role).write_bytes(private_bytes)
    _pub_path(role).write_bytes(public_bytes)
    logger.info("Generated Ed25519 keypair for role=%s", role)

    return private_key, public_bytes


def load_or_generate_keypair(role: str) -> tuple[Ed25519PrivateKey, bytes]:
    """Load an existing keypair from disk, or generate one if missing."""
    if role in _keypairs:
        return _keypairs[role]

    priv_path = _key_path(role)
    pub_path = _pub_path(role)

    if priv_path.exists() and pub_path.exists():
        private_key = Ed25519PrivateKey.from_private_bytes(priv_path.read_bytes())
        public_bytes = pub_path.read_bytes()
        logger.info("Loaded Ed25519 keypair for role=%s", role)
    else:
        private_key, public_bytes = generate_keypair(role)

    _keypairs[role] = (private_key, public_bytes)
    return private_key, public_bytes


def get_public_key_b64(role: str) -> str:
    """Return the base64-encoded public key for *role*."""
    import base64

    _, pub_bytes = load_or_generate_keypair(role)
    return base64.b64encode(pub_bytes).decode("ascii")


def get_signing_key(role: str) -> Ed25519PrivateKey:
    """Return the Ed25519 private key for *role*."""
    private_key, _ = load_or_generate_keypair(role)
    return private_key


# ---------------------------------------------------------------------------
# Sign / verify
# ---------------------------------------------------------------------------

def sign_message(message_dict: dict[str, Any], role: str) -> tuple[str, str]:
    """Sign a message dict using the Ed25519 key for *role*.

    Returns (signature_b64, public_key_b64).
    """
    import base64

    private_key = get_signing_key(role)
    _, public_bytes = load_or_generate_keypair(role)

    payload = canonical_json(message_dict)
    signature = private_key.sign(payload)
    return (
        base64.b64encode(signature).decode("ascii"),
        base64.b64encode(public_bytes).decode("ascii"),
    )


def verify_signature(
    message_dict: dict[str, Any],
    signature_b64: str,
    public_key_b64: str,
) -> bool:
    """Verify an Ed25519 signature against a message dict and public key.

    Returns True if valid, False otherwise (never raises).
    """
    import base64

    try:
        pub_bytes = base64.b64decode(public_key_b64)
        public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
        sig_bytes = base64.b64decode(signature_b64)
        payload = canonical_json(message_dict)
        public_key.verify(sig_bytes, payload)
        return True
    except Exception:
        return False
