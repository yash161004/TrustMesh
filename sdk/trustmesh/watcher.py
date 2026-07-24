"""TrustMeshWatcher — a thin, framework-agnostic audit wrapper.

Drop the watcher into any agent loop (CrewAI, AutoGen, LangChain, OpenAI Swarm,
or a plain function) and call :meth:`TrustMeshWatcher.audit_and_sign` on each
turn. Every message is Ed25519-signed and appended to an append-only,
SHA-256 hash-chained ledger, so afterwards you can *prove* — not just claim —
that no turn was altered or dropped.

Design notes:
- Reuses the TrustMesh backend's exact signing/chain primitives (see
  ``_crypto``), so records produced here verify under the backend and vice
  versa. There is no forked crypto to drift.
- Holds its own in-memory Ed25519 keypair rather than touching the backend's
  on-disk ``.keys/`` store — the SDK stays self-contained middleware and never
  mutates global state. Pass an existing private key to reuse an identity.
- Auditing is pluggable via ``policy_hook`` and is entirely optional. The SDK
  forces no LLM dependency: bring your own detector (or the TrustMesh trust
  engine) if you want per-turn policy flags; omit it for sign-only operation.
- Local-first. This does not call a hosted TrustMesh service; there is no
  ``api_key`` because there is no remote to authenticate to yet. Keeping the
  claim honest: this is designed to integrate with any agent framework, not a
  client for a service that does not exist.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from ._crypto import GENESIS_HASH, build_entry, canonical_json, verify_chain, verify_signature

# A policy hook takes the message dict and returns a list of string flags
# (e.g. ["urgency_pressure", "unauthorized_commitment"]). Empty list = clean.
PolicyHook = Callable[[dict[str, Any]], list[str]]


@dataclass(frozen=True)
class AuditedTurn:
    """The immutable result of auditing and signing one turn.

    ``entry`` is the exact ledger-entry dict appended to the chain; it is what
    verifies under :func:`app.crypto.ledger.verify_chain`.
    """

    message: dict[str, Any]
    sender: str
    session_id: Optional[str]
    sequence: int
    signature: str          # base64 Ed25519 signature over canonical_json(message)
    public_key: str         # base64 Ed25519 public key of the signer
    prev_hash: str
    entry_hash: str
    created_at: datetime
    flags: list[str] = field(default_factory=list)
    entry: dict[str, Any] = field(default_factory=dict)

    @property
    def is_flagged(self) -> bool:
        """True if the optional policy hook raised any flag for this turn."""
        return bool(self.flags)

    def verify(self) -> bool:
        """Re-check this turn's signature against its own message and key."""
        return verify_signature(self.message, self.signature, self.public_key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sender": self.sender,
            "session_id": self.session_id,
            "sequence": self.sequence,
            "signature": self.signature,
            "public_key": self.public_key,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
            "created_at": self.created_at.isoformat(),
            "flags": list(self.flags),
            "message": self.message,
        }


class TrustMeshWatcher:
    """Sign and hash-chain each turn of an agent conversation.

    Example::

        from trustmesh import TrustMeshWatcher

        watcher = TrustMeshWatcher(agent_id="buyer-agent-001", session_id="sess-42")
        turn = watcher.audit_and_sign({"role": "buyer", "text": "I offer $90/unit"})
        ...
        ok, broken_at = watcher.verify()
        assert ok  # the whole negotiation is tamper-evident
    """

    def __init__(
        self,
        agent_id: str,
        *,
        session_id: Optional[str] = None,
        private_key: Optional[Ed25519PrivateKey] = None,
        policy_hook: Optional[PolicyHook] = None,
    ) -> None:
        if not agent_id:
            raise ValueError("agent_id is required")
        self.agent_id = agent_id
        self.session_id = session_id
        self._policy_hook = policy_hook
        self._private_key = private_key or Ed25519PrivateKey.generate()
        pub_bytes = self._private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        self._public_key_b64 = base64.b64encode(pub_bytes).decode("ascii")

        self._entries: list[dict[str, Any]] = []
        self._last_hash: str = GENESIS_HASH
        self._sequence: int = 0

    # ------------------------------------------------------------------
    @property
    def public_key_b64(self) -> str:
        """The signer's base64 Ed25519 public key (share this with verifiers)."""
        return self._public_key_b64

    def audit_and_sign(
        self,
        message: dict[str, Any],
        *,
        sender: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AuditedTurn:
        """Audit (optional), sign, and append one message to the ledger.

        ``message`` is signed exactly as given — include the fields you want to
        be tamper-evident (sender, turn number, price, terms) in it. Returns an
        :class:`AuditedTurn`; the message is also appended to this watcher's
        hash chain so a later :meth:`verify` covers the whole conversation.
        """
        if not isinstance(message, dict):
            raise TypeError("message must be a dict")

        sender = sender or self.agent_id
        session_id = session_id or self.session_id

        flags: list[str] = []
        if self._policy_hook is not None:
            flags = list(self._policy_hook(message))

        signature_b64 = base64.b64encode(
            self._private_key.sign(canonical_json(message))
        ).decode("ascii")

        created_at = datetime.now(timezone.utc)
        entry = build_entry(
            message_dict=message,
            signature=signature_b64,
            signer_public_key=self._public_key_b64,
            prev_hash=self._last_hash,
            sequence=self._sequence,
            created_at=created_at,
            session_id=session_id,
        )

        self._entries.append(entry)
        self._last_hash = entry["entry_hash"]
        self._sequence += 1

        return AuditedTurn(
            message=message,
            sender=sender,
            session_id=session_id,
            sequence=entry["sequence"],
            signature=signature_b64,
            public_key=self._public_key_b64,
            prev_hash=entry["prev_hash"],
            entry_hash=entry["entry_hash"],
            created_at=created_at,
            flags=flags,
            entry=entry,
        )

    def verify(self) -> tuple[bool, Optional[int]]:
        """Verify the whole ledger. Returns ``(is_valid, broken_at_sequence)``.

        ``broken_at_sequence`` is ``None`` when valid, else the sequence number
        of the first entry that fails the chain (tampered or reordered).
        """
        return verify_chain(self._entries)

    def ledger(self) -> list[dict[str, Any]]:
        """A copy of the raw ledger entries (as verified by the backend)."""
        return [dict(e) for e in self._entries]

    def __len__(self) -> int:
        return len(self._entries)
