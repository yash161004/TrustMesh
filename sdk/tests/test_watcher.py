"""Tests for the TrustMeshWatcher SDK.

These prove the SDK's records are tamper-evident and — critically — that they
verify under the *backend's* own crypto, not a forked copy.
"""
import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from trustmesh import AuditedTurn, TrustMeshWatcher

# The backend primitives the SDK claims to be compatible with. Importing them
# here (not through the SDK) is the point: the cross-compat tests below assert
# the SDK output verifies under the exact functions the TrustMesh backend uses.
from app.crypto.ledger import verify_chain as backend_verify_chain
from app.crypto.signing import verify_signature as backend_verify_signature


def test_single_turn_signs_and_verifies():
    w = TrustMeshWatcher(agent_id="buyer-agent-001", session_id="sess-1")
    turn = w.audit_and_sign({"role": "buyer", "text": "I offer $90/unit"})

    assert isinstance(turn, AuditedTurn)
    assert turn.sequence == 0
    assert turn.sender == "buyer-agent-001"
    assert turn.session_id == "sess-1"
    assert turn.verify() is True


def test_multi_turn_chain_is_valid():
    w = TrustMeshWatcher(agent_id="a", session_id="s")
    for i in range(5):
        w.audit_and_sign({"turn": i, "text": f"msg {i}"})

    ok, broken_at = w.verify()
    assert ok is True
    assert broken_at is None
    assert len(w) == 5
    # sequences are contiguous from 0
    assert [e["sequence"] for e in w.ledger()] == [0, 1, 2, 3, 4]


def test_sdk_chain_verifies_under_backend():
    """Cross-compat: SDK-produced ledger verifies with the backend's verify_chain."""
    w = TrustMeshWatcher(agent_id="a")
    for i in range(3):
        w.audit_and_sign({"turn": i})

    ok, broken_at = backend_verify_chain(w.ledger())
    assert ok is True and broken_at is None


def test_sdk_signature_verifies_under_backend():
    """Cross-compat: a turn's signature verifies with the backend's verify_signature."""
    w = TrustMeshWatcher(agent_id="a")
    msg = {"role": "seller", "price": 88.5, "terms": "net-30"}
    turn = w.audit_and_sign(msg)

    assert backend_verify_signature(msg, turn.signature, turn.public_key) is True
    # a different message must not verify against the same signature
    assert backend_verify_signature({"role": "seller", "price": 1.0},
                                    turn.signature, turn.public_key) is False


def test_tampering_with_a_message_breaks_the_chain():
    w = TrustMeshWatcher(agent_id="a")
    w.audit_and_sign({"turn": 0, "text": "clean"})
    w.audit_and_sign({"turn": 1, "text": "clean"})
    w.audit_and_sign({"turn": 2, "text": "clean"})

    entries = w.ledger()
    # Forge the middle entry's payload, leaving its stored hash intact.
    tampered = json.loads(entries[1]["message_json"])
    tampered["text"] = "I never agreed to this"
    entries[1]["message_json"] = json.dumps(
        tampered, sort_keys=True, separators=(",", ":")
    )

    ok, broken_at = backend_verify_chain(entries)
    assert ok is False
    assert broken_at == 1


def test_reordering_turns_breaks_the_chain():
    w = TrustMeshWatcher(agent_id="a")
    for i in range(4):
        w.audit_and_sign({"turn": i})

    entries = w.ledger()
    entries[1], entries[2] = entries[2], entries[1]  # swap

    ok, broken_at = backend_verify_chain(entries)
    assert ok is False


def test_policy_hook_flags_surface_on_turn():
    def hook(message):
        flags = []
        if "urgent" in message.get("text", "").lower():
            flags.append("urgency_pressure")
        return flags

    w = TrustMeshWatcher(agent_id="a", policy_hook=hook)
    clean = w.audit_and_sign({"text": "here is my offer"})
    flagged = w.audit_and_sign({"text": "URGENT: accept in 5 minutes or lose the deal"})

    assert clean.is_flagged is False
    assert clean.flags == []
    assert flagged.is_flagged is True
    assert "urgency_pressure" in flagged.flags
    # flags never break the chain — auditing and integrity are independent
    assert w.verify()[0] is True


def test_provided_private_key_is_reused_as_stable_identity():
    key = Ed25519PrivateKey.generate()
    w1 = TrustMeshWatcher(agent_id="a", private_key=key)
    w2 = TrustMeshWatcher(agent_id="a", private_key=key)
    assert w1.public_key_b64 == w2.public_key_b64

    # a freshly-generated identity differs
    w3 = TrustMeshWatcher(agent_id="a")
    assert w3.public_key_b64 != w1.public_key_b64


def test_public_key_is_valid_ed25519_raw():
    w = TrustMeshWatcher(agent_id="a")
    raw = base64.b64decode(w.public_key_b64)
    assert len(raw) == 32  # Ed25519 raw public keys are 32 bytes


def test_empty_agent_id_rejected():
    with pytest.raises(ValueError):
        TrustMeshWatcher(agent_id="")


def test_non_dict_message_rejected():
    w = TrustMeshWatcher(agent_id="a")
    with pytest.raises(TypeError):
        w.audit_and_sign("not a dict")  # type: ignore[arg-type]
