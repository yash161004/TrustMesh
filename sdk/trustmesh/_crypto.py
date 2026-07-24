"""Crypto facade for the SDK.

The primitives are vendored in ``_primitives`` so the SDK is standalone (its only
runtime dependency is ``cryptography``). They are kept byte-for-byte compatible
with the TrustMesh backend's reference implementation — ``tests/test_backend_parity.py``
imports the backend's own functions and asserts identical output, so the two
cannot silently diverge.

This module exists as a stable import surface for the rest of the package; it
simply re-exports the vendored primitives.
"""
from __future__ import annotations

from ._primitives import (
    GENESIS_HASH,
    build_entry,
    canonical_json,
    compute_entry_hash_from_dict,
    verify_chain,
    verify_signature,
)

__all__ = [
    "GENESIS_HASH",
    "canonical_json",
    "verify_signature",
    "build_entry",
    "verify_chain",
    "compute_entry_hash_from_dict",
]
