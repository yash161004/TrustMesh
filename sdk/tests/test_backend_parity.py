"""Parity: the SDK's vendored primitives must match the backend byte-for-byte.

This is what lets the SDK be standalone *and* still guarantee its records verify
under the TrustMesh backend. If the backend's crypto ever changes, one of these
assertions fails and we know the vendored copy drifted. Skips cleanly if the
backend package is not importable (e.g. SDK checked out on its own).
"""
import base64

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from trustmesh import _primitives as sdk

backend_signing = pytest.importorskip(
    "app.crypto.signing", reason="backend not importable; parity check skipped"
)
backend_ledger = pytest.importorskip(
    "app.crypto.ledger", reason="backend not importable; parity check skipped"
)


@pytest.mark.parametrize("obj", [
    {"b": 1, "a": 2},
    {"text": "I offer $90", "price": 90.5, "nested": {"z": 1, "a": [3, 2, 1]}},
    {"unicode": "café — naïve", "empty": {}, "null": None},
    {},
])
def test_canonical_json_is_byte_identical(obj):
    assert sdk.canonical_json(obj) == backend_signing.canonical_json(obj)


def test_genesis_hash_matches():
    assert sdk.GENESIS_HASH == backend_ledger._GENESIS_HASH


def test_entry_hash_is_identical_for_same_inputs():
    msg = {"turn": 1, "text": "hello", "session_id": "s"}
    kwargs = dict(
        signature="sig-b64",
        signer_public_key="pub-b64",
        prev_hash=sdk.GENESIS_HASH,
        sequence=0,
        session_id="s",
    )
    sdk_entry = sdk.build_entry(message_dict=msg, **kwargs)
    backend_entry = backend_ledger.build_entry(message_dict=msg, **kwargs)

    assert sdk_entry["message_json"] == backend_entry["message_json"]
    assert sdk_entry["entry_hash"] == backend_entry["entry_hash"]


def test_signature_cross_verifies_both_directions():
    key = Ed25519PrivateKey.generate()
    pub_bytes = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    pub_b64 = base64.b64encode(pub_bytes).decode()

    msg = {"role": "buyer", "text": "final offer $91"}
    sig_b64 = base64.b64encode(key.sign(sdk.canonical_json(msg))).decode()

    # SDK-made signature verifies under the backend, and vice versa.
    assert backend_signing.verify_signature(msg, sig_b64, pub_b64) is True
    assert sdk.verify_signature(msg, sig_b64, pub_b64) is True


def test_backend_built_chain_verifies_under_sdk_and_vice_versa():
    # Build a 2-entry chain with the backend, verify it with the SDK's verify_chain.
    e0 = backend_ledger.build_entry(
        message_dict={"turn": 0}, signature="s0", signer_public_key="p",
        prev_hash=backend_ledger._GENESIS_HASH, sequence=0,
    )
    e1 = backend_ledger.build_entry(
        message_dict={"turn": 1}, signature="s1", signer_public_key="p",
        prev_hash=e0["entry_hash"], sequence=1,
    )
    chain = [e0, e1]

    assert sdk.verify_chain(chain) == (True, None)
    assert backend_ledger.verify_chain(chain) == (True, None)
