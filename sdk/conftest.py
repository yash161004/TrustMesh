"""Pytest path setup for the SDK.

Adds the SDK dir so ``import trustmesh`` works, and the sibling ``backend/`` dir
so the parity/cross-compat tests can import the backend's reference crypto
(``app.crypto.*``). The SDK *runtime* does not need the backend — only these
tests do, to assert the vendored primitives match the reference byte-for-byte.
"""
import sys
from pathlib import Path

_SDK_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SDK_DIR.parent / "backend"

sys.path.insert(0, str(_SDK_DIR))
if _BACKEND_DIR.is_dir():
    sys.path.insert(0, str(_BACKEND_DIR))
