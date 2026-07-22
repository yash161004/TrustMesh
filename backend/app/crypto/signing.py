"""
TrustMesh Signing Module — Ed25519 key management and message signing.

Provides deterministic serialization (canonical JSON), Ed25519 keypair
generation/loading per agent role or per agent_id, and sign/verify helpers.
"""
from __future__ import annotations

import json
import logging
import os
import threading
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

# Module-level cache: key_identifier -> (private_key, public_key_bytes)
_keypairs: dict[str, tuple[Ed25519PrivateKey, bytes]] = {}
_key_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Canonical JSON serialization
# ---------------------------------------------------------------------------

def canonical_json(obj: Any) -> bytes:
    """Serialize *obj* to deterministic JSON bytes (sorted keys, no whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


# ---------------------------------------------------------------------------
# Keypair management
# ---------------------------------------------------------------------------

def _key_path(identifier: str) -> Path:
    safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in identifier)
    return _KEYS_DIR / f"{safe_id}.key"


def _pub_path(identifier: str) -> Path:
    safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in identifier)
    return _KEYS_DIR / f"{safe_id}.pub"


def generate_keypair(role: str) -> tuple[Ed25519PrivateKey, bytes]:
    """Generate a fresh Ed25519 keypair, persist it, and return (private_key, pub_bytes)."""
    return generate_keypair_for_identifier(role)


def generate_keypair_for_identifier(identifier: str) -> tuple[Ed25519PrivateKey, bytes]:
    """Generate an Ed25519 keypair for role or agent_id under thread lock."""
    return load_or_generate_keypair_for_identifier(identifier)


def load_or_generate_keypair(role: str) -> tuple[Ed25519PrivateKey, bytes]:
    """Load an existing keypair from disk, or generate one if missing."""
    return load_or_generate_keypair_for_identifier(role)


def load_or_generate_keypair_for_agent(agent_id: str) -> tuple[Ed25519PrivateKey, bytes]:
    """Load an existing keypair for agent_id from disk, or generate one if missing (thread-safe)."""
    return load_or_generate_keypair_for_identifier(agent_id)


def load_or_generate_keypair_for_identifier(identifier: str) -> tuple[Ed25519PrivateKey, bytes]:
    """Load an existing keypair for any identifier (role or agent_id) thread-safely."""
    with _key_lock:
        if identifier in _keypairs:
            return _keypairs[identifier]

        priv_path = _key_path(identifier)
        pub_path = _pub_path(identifier)

        if priv_path.exists() and pub_path.exists():
            private_key = Ed25519PrivateKey.from_private_bytes(priv_path.read_bytes())
            public_bytes = pub_path.read_bytes()
            logger.info("Loaded Ed25519 keypair for identifier=%s", identifier)
            _keypairs[identifier] = (private_key, public_bytes)
            return private_key, public_bytes

        # Inline generation inside _key_lock to guarantee zero race condition window
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

        priv_path.write_bytes(private_bytes)
        pub_path.write_bytes(public_bytes)
        _keypairs[identifier] = (private_key, public_bytes)
        logger.info("Generated Ed25519 keypair for identifier=%s", identifier)
        return private_key, public_bytes


def get_public_key_b64(role_or_agent_id: str) -> str:
    """Return the base64-encoded public key for role or agent_id."""
    import base64

    _, pub_bytes = load_or_generate_keypair_for_identifier(role_or_agent_id)
    return base64.b64encode(pub_bytes).decode("ascii")


def get_signing_key(role_or_agent_id: str) -> Ed25519PrivateKey:
    """Return the Ed25519 private key for role or agent_id."""
    private_key, _ = load_or_generate_keypair_for_identifier(role_or_agent_id)
    return private_key


# ---------------------------------------------------------------------------
# Sign / verify
# ---------------------------------------------------------------------------

def sign_message(message_dict: dict[str, Any], role_or_agent_id: str) -> tuple[str, str]:
    """Sign a message dict using the Ed25519 key for role or agent_id.

    Returns (signature_b64, public_key_b64).
    """
    import base64

    private_key = get_signing_key(role_or_agent_id)
    _, public_bytes = load_or_generate_keypair_for_identifier(role_or_agent_id)

    payload = canonical_json(message_dict)
    signature = private_key.sign(payload)
    return (
        base64.b64encode(signature).decode("ascii"),
        base64.b64encode(public_bytes).decode("ascii"),
    )


def sign_message_for_agent(message_dict: dict[str, Any], agent_id: str) -> tuple[str, str]:
    """Sign a message dict using per-agent key for agent_id."""
    return sign_message(message_dict, agent_id)


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
