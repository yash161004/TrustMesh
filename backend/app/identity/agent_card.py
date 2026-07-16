"""
TrustMesh AgentCard — local implementation of the ERC-8004 AgentCard pattern.

An AgentCard is a machine-readable identity descriptor that binds an agent's
public key to its stated role, capabilities, and metadata.  This module
generates, signs, persists, and verifies AgentCards on the local filesystem
as a proof-of-concept analog of the on-chain ERC-8004 standard.
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from ..crypto.signing import canonical_json, load_or_generate_keypair

logger = logging.getLogger(__name__)

CARDS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "agent_cards"
AGENT_CARD_VERSION = "1.0.0"


class AgentCard(BaseModel):
    """A cryptographically-signed identity descriptor for an agent role."""

    agent_id: str = Field(default_factory=lambda: str(uuid4()))
    role: str
    display_name: str
    capabilities: list[str] = Field(default_factory=list)
    public_key: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = AGENT_CARD_VERSION

    def serialize(self) -> bytes:
        """Deterministic canonical JSON bytes of card payload (for signing)."""
        return canonical_json(self.model_dump(mode="json"))


def sign_agent_card(card: AgentCard, role: str) -> tuple[AgentCard, str]:
    """Sign an AgentCard's contents using the agent's Ed25519 private key.

    Returns (card, signature_b64).  The private key is loaded by role name
    from the existing .keys/ directory managed by app.crypto.signing.
    """
    from ..crypto.signing import get_signing_key

    private_key = get_signing_key(role)
    payload = card.serialize()
    sig_bytes = private_key.sign(payload)
    signature_b64 = base64.b64encode(sig_bytes).decode("ascii")
    return card, signature_b64


def card_file_path(agent_id: str) -> Path:
    """Return the local filesystem path for an AgentCard."""
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    return CARDS_DIR / f"{agent_id}.json"


def write_agent_card(card: AgentCard, signature_b64: str) -> Path:
    """Persist a signed AgentCard to a local JSON file.

    The output file contains both the card payload and its detached
    signature, mirroring the ERC-8004 convention of a resolvable
    identity document.
    """
    path = card_file_path(card.agent_id)
    payload = {
        "card": card.model_dump(mode="json"),
        "signature": signature_b64,
    }
    path.write_text(json.dumps(payload, indent=2, default=str))
    logger.info("Wrote AgentCard for %s (%s) to %s", card.role, card.agent_id, path)
    return path


def verify_agent_card(card_path: str | Path) -> bool:
    """Verify that an AgentCard's signature matches its contents.

    Loads the card file, recomputes the canonical JSON over the card
    payload, and confirms the Ed25519 signature is valid against the
    public key embedded in the card itself.

    Returns True if valid, False otherwise (never raises).
    """
    path = Path(card_path)
    if not path.exists():
        logger.error("AgentCard not found: %s", path)
        return False

    try:
        data = json.loads(path.read_text())
        card_data: dict[str, Any] = data["card"]
        signature_b64: str = data["signature"]

        # Recompute canonical bytes of the card payload
        card_bytes = canonical_json(card_data)

        # Decode signature and public key from the card itself
        sig_bytes = base64.b64decode(signature_b64)
        pub_bytes = base64.b64decode(card_data["public_key"])
        public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)

        public_key.verify(sig_bytes, card_bytes)
        return True

    except Exception as exc:
        logger.warning("AgentCard verification failed for %s: %s", path, exc)
        return False


def generate_agent_card(role: str, agent_id: str | None = None) -> tuple[AgentCard, str]:
    """Factory: build, sign, and persist an AgentCard for *role*.

    The card is returned alongside its base64-encoded signature so the
    caller can inspect or wrap it further.
    """
    _, pub_bytes = load_or_generate_keypair(role)
    public_key_b64 = base64.b64encode(pub_bytes).decode("ascii")

    role_label = role.replace("_", " ").title()
    capabilities = _default_capabilities(role)

    card_kwargs = {
        "role": role,
        "display_name": f"{role_label} Agent",
        "capabilities": capabilities,
        "public_key": public_key_b64,
    }
    if agent_id:
        card_kwargs["agent_id"] = agent_id

    card = AgentCard(**card_kwargs)
    card, sig = sign_agent_card(card, role)
    write_agent_card(card, sig)
    return card, sig


def _default_capabilities(role: str) -> list[str]:
    """Return a sensible default capability list for the given role."""
    common = ["negotiate_price", "commit_to_terms", "counter_offer"]
    if role == "buyer":
        return common + ["request_discount", "set_budget_ceiling", "evaluate_proposal"]
    if role == "seller":
        return common + ["offer_volume_discount", "adjust_delivery_terms", "provide_quote"]
    return common
