"""
TrustMesh AgentCard — local implementation of the ERC-8004 AgentCard pattern.

An AgentCard is a machine-readable identity descriptor that binds an agent's
public key to its stated role, capabilities, org tenancy, and metadata.
This module generates, signs, persists, and verifies AgentCards on the local filesystem.
"""
from __future__ import annotations

import base64
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from ..crypto.signing import (
    canonical_json,
    load_or_generate_keypair_for_agent,
    load_or_generate_keypair_for_identifier,
)

logger = logging.getLogger(__name__)

CARDS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "agent_cards"
AGENT_CARD_VERSION = "1.0.0"

_card_lock = threading.Lock()


class AgentCard(BaseModel):
    """A cryptographically-signed identity descriptor for an agent role."""

    agent_id: str = Field(default_factory=lambda: str(uuid4()))
    role: str
    display_name: str
    capabilities: list[str] = Field(default_factory=list)
    public_key: str
    org_id: str | None = None
    owner_user_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = AGENT_CARD_VERSION

    def serialize(self) -> bytes:
        """Deterministic canonical JSON bytes of card payload (for signing)."""
        return canonical_json(self.model_dump(mode="json"))


def sign_agent_card(card: AgentCard, role_or_agent_id: str | None = None) -> tuple[AgentCard, str]:
    """Sign an AgentCard's contents using the agent's Ed25519 private key.

    Returns (card, signature_b64). The private key is loaded by agent_id or role name
    from the existing .keys/ directory.
    """
    from ..crypto.signing import get_signing_key

    identifier = role_or_agent_id or card.agent_id
    private_key = get_signing_key(identifier)
    payload = card.serialize()
    sig_bytes = private_key.sign(payload)
    signature_b64 = base64.b64encode(sig_bytes).decode("ascii")
    return card, signature_b64


def card_file_path(agent_id: str, org_id: str | None = None) -> Path:
    """Return the local filesystem path for an AgentCard.

    Scopes the card path as '{org_id}__{agent_id}.json' if org_id is provided,
    or '{agent_id}.json' if org_id is None. If org_id is None and an un-scoped
    path does not exist, searches for an existing '{any_org}__{agent_id}.json' file.
    """
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in agent_id)
    if org_id:
        safe_org = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in org_id)
        return CARDS_DIR / f"{safe_org}__{safe_id}.json"

    default_path = CARDS_DIR / f"{safe_id}.json"
    if not default_path.exists():
        matches = list(CARDS_DIR.glob(f"*__{safe_id}.json"))
        if matches:
            return matches[0]
    return default_path


def write_agent_card(card: AgentCard, signature_b64: str) -> Path:
    """Persist a signed AgentCard to a local JSON file."""
    path = card_file_path(card.agent_id, card.org_id)
    payload = {
        "card": card.model_dump(mode="json"),
        "signature": signature_b64,
    }
    path.write_text(json.dumps(payload, indent=2, default=str))
    logger.info("Wrote AgentCard for %s (%s, org=%s) to %s", card.role, card.agent_id, card.org_id, path)
    return path


def verify_agent_card(card_path: str | Path, expected_org_id: str | None = None) -> bool:
    """Verify that an AgentCard's signature matches its contents and org tenancy.

    Loads the card file, recomputes the canonical JSON over the card
    payload, confirms Ed25519 signature validity against the card's public key,
    and optionally validates that org_id matches expected_org_id.

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

        if expected_org_id is not None and card_data.get("org_id") != expected_org_id:
            logger.warning(
                "AgentCard org mismatch for %s: expected %s, got %s",
                path,
                expected_org_id,
                card_data.get("org_id"),
            )
            return False

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


def generate_agent_card(
    role: str,
    agent_id: str | None = None,
    display_name: str | None = None,
    org_id: str | None = None,
    owner_user_id: str | None = None,
) -> tuple[AgentCard, str]:
    """Factory: build, sign, and persist an AgentCard for *role* and *agent_id*."""
    target_id = agent_id or str(uuid4())
    _, pub_bytes = load_or_generate_keypair_for_agent(target_id)
    public_key_b64 = base64.b64encode(pub_bytes).decode("ascii")

    role_label = role.replace("_", " ").title()
    capabilities = _default_capabilities(role)

    card_kwargs: dict[str, Any] = {
        "role": role,
        "agent_id": target_id,
        "display_name": display_name or f"{role_label} Agent",
        "capabilities": capabilities,
        "public_key": public_key_b64,
        "org_id": org_id,
        "owner_user_id": owner_user_id,
    }

    card = AgentCard(**card_kwargs)
    card, sig = sign_agent_card(card, target_id)
    write_agent_card(card, sig)
    return card, sig


def get_or_create_agent_card(
    agent_id: str,
    role: str,
    org_id: str | None = None,
    owner_user_id: str | None = None,
    display_name: str | None = None,
) -> tuple[AgentCard, str]:
    """Idempotently fetch or lazily provision an AgentCard under thread lock.

    Ensures no concurrent duplicate card creation / key clobbering.
    Binds org_id and owner_user_id from caller's authenticated context.
    """
    path = card_file_path(agent_id, org_id)
    with _card_lock:
        if path.exists():
            try:
                data = json.loads(path.read_text())
                card = AgentCard(**data["card"])
                sig = data["signature"]
                return card, sig
            except Exception as e:
                logger.warning("Failed to load existing AgentCard for %s (org=%s): %s", agent_id, org_id, e)

        return generate_agent_card(
            role=role,
            agent_id=agent_id,
            display_name=display_name,
            org_id=org_id,
            owner_user_id=owner_user_id,
        )


def _default_capabilities(role: str) -> list[str]:
    """Return a sensible default capability list for the given role."""
    common = ["negotiate_price", "commit_to_terms", "counter_offer"]
    if role == "buyer":
        return common + ["request_discount", "set_budget_ceiling", "evaluate_proposal"]
    if role == "seller":
        return common + ["offer_volume_discount", "adjust_delivery_terms", "provide_quote"]
    return common
