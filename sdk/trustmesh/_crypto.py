"""Crypto bridge — reuse the TrustMesh backend's primitives, do not fork them.

The whole point of the SDK is to produce audit records that verify under the
*same* signing and hash-chain logic the TrustMesh backend uses. Re-implementing
Ed25519 signing or the SHA-256 chain here would risk silent divergence (a
reviewer's fair question: "are these really the same primitives?"). So instead
of vendoring a copy, this module imports the reference implementation directly
from the backend package.

That means the backend must be importable. In the repo it lives at
``<repo>/backend``; we add that to ``sys.path`` as a convenience so the SDK works
from a checkout with no extra configuration. Packaging the SDK as a fully
standalone distribution (vendoring these primitives, or splitting them into a
shared ``trustmesh-core`` package both sides depend on) is deliberate follow-on
work — see sdk/README.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if _BACKEND_DIR.is_dir() and str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

try:
    from app.crypto.signing import canonical_json, verify_signature
    from app.crypto.ledger import build_entry, verify_chain, _GENESIS_HASH
except ImportError as exc:  # pragma: no cover - environment guard
    raise ImportError(
        "trustmesh-sdk reuses the TrustMesh backend crypto primitives, but the "
        "backend package could not be imported. Ensure the repository's `backend/` "
        "directory is importable (it is added to sys.path automatically when the "
        "SDK is used from a repo checkout). Standalone packaging is planned — see "
        "sdk/README.md."
    ) from exc

GENESIS_HASH = _GENESIS_HASH

__all__ = [
    "canonical_json",
    "verify_signature",
    "build_entry",
    "verify_chain",
    "GENESIS_HASH",
]
