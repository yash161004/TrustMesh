"""
Tests for the TrustMesh cryptographic commitment layer.

Covers:
- Ed25519 signing / verification round-trip
- Tampered-message detection
- Hash-chain integrity and tamper detection
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from app.crypto.signing import (
    canonical_json,
    generate_keypair,
    load_or_generate_keypair,
    sign_message,
    verify_signature,
)
from app.crypto.ledger import (
    _GENESIS_HASH,
    build_entry,
    compute_entry_hash_from_dict,
    verify_chain,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_MSG = {
    "message_type": "OFFER",
    "sender": "buyer-agent-001",
    "price": 149.99,
    "quantity": 500,
    "delivery_terms": "Net-30, FOB destination",
    "turn_number": 1,
}


def _clean_keys():
    """Remove generated test keys after each test."""
    keys_dir = Path(__file__).resolve().parent.parent / ".keys"
    if keys_dir.exists():
        shutil.rmtree(keys_dir)


# ---------------------------------------------------------------------------
# Signing tests
# ---------------------------------------------------------------------------

class TestSigning:
    def setup_method(self):
        _clean_keys()

    def teardown_method(self):
        _clean_keys()

    def test_canonical_json_deterministic(self):
        """canonical_json produces the same bytes regardless of dict insertion order."""
        a = {"z": 1, "a": 2, "m": 3}
        b = {"a": 2, "m": 3, "z": 1}
        assert canonical_json(a) == canonical_json(b)

    def test_canonical_json_no_whitespace(self):
        out = canonical_json({"key": "value"})
        assert b" " not in out
        assert out == b'{"key":"value"}'

    def test_sign_and_verify_roundtrip(self):
        sig, pub = sign_message(SAMPLE_MSG, "buyer")
        assert isinstance(sig, str)
        assert isinstance(pub, str)
        assert verify_signature(SAMPLE_MSG, sig, pub) is True

    def test_verify_fails_on_tampered_message(self):
        sig, pub = sign_message(SAMPLE_MSG, "buyer")
        tampered = {**SAMPLE_MSG, "price": 9999.99}
        assert verify_signature(tampered, sig, pub) is False

    def test_verify_fails_on_wrong_key(self):
        sig, _ = sign_message(SAMPLE_MSG, "buyer")
        _, wrong_pub = sign_message(SAMPLE_MSG, "seller")
        assert verify_signature(SAMPLE_MSG, sig, wrong_pub) is False

    def test_verify_fails_on_bad_signature(self):
        _, pub = sign_message(SAMPLE_MSG, "buyer")
        assert verify_signature(SAMPLE_MSG, "not-a-real-sig", pub) is False

    def test_keypair_persistence(self):
        """Loading the same role twice returns the same keypair."""
        _, pub1 = load_or_generate_keypair("buyer")
        _, pub2 = load_or_generate_keypair("buyer")
        assert pub1 == pub2

    def test_different_roles_different_keys(self):
        _, pub_buyer = load_or_generate_keypair("buyer")
        _, pub_seller = load_or_generate_keypair("seller")
        assert pub_buyer != pub_seller


# ---------------------------------------------------------------------------
# Ledger / hash-chain tests
# ---------------------------------------------------------------------------

class TestLedger:
    def test_build_entry_hash_deterministic(self):
        entry = build_entry(SAMPLE_MSG, "sig123", "pub456", _GENESIS_HASH, 1)
        recomputed = compute_entry_hash_from_dict(entry)
        assert entry["entry_hash"] == recomputed

    def test_valid_chain_verifies(self):
        entries = []
        prev = _GENESIS_HASH
        for i in range(3):
            msg = {**SAMPLE_MSG, "turn_number": i + 1}
            entry = build_entry(msg, f"sig{i}", f"pub{i}", prev, i + 1)
            entries.append(entry)
            prev = entry["entry_hash"]
        valid, broken = verify_chain(entries)
        assert valid is True
        assert broken is None

    def test_tampered_message_breaks_chain(self):
        entries = []
        prev = _GENESIS_HASH
        for i in range(3):
            msg = {**SAMPLE_MSG, "turn_number": i + 1}
            entry = build_entry(msg, f"sig{i}", f"pub{i}", prev, i + 1)
            entries.append(entry)
            prev = entry["entry_hash"]

        # Tamper with the second entry's message_json
        entries[1]["message_json"] = json.dumps(
            {"tampered": True}, sort_keys=True, separators=(",", ":")
        )
        valid, broken = verify_chain(entries)
        assert valid is False
        assert broken == entries[1]["sequence"]

    def test_reordered_entry_breaks_chain(self):
        entries = []
        prev = _GENESIS_HASH
        for i in range(3):
            msg = {**SAMPLE_MSG, "turn_number": i + 1}
            entry = build_entry(msg, f"sig{i}", f"pub{i}", prev, i + 1)
            entries.append(entry)
            prev = entry["entry_hash"]

        # Swap entries 1 and 2
        entries[1], entries[2] = entries[2], entries[1]
        valid, broken = verify_chain(entries)
        assert valid is False
        assert broken is not None

    def test_tampered_hash_detected(self):
        entries = []
        prev = _GENESIS_HASH
        for i in range(2):
            msg = {**SAMPLE_MSG, "turn_number": i + 1}
            entry = build_entry(msg, f"sig{i}", f"pub{i}", prev, i + 1)
            entries.append(entry)
            prev = entry["entry_hash"]

        # Tamper with the hash itself
        entries[0]["entry_hash"] = "a" * 64
        valid, broken = verify_chain(entries)
        assert valid is False
        assert broken == entries[0]["sequence"]

    def test_empty_chain_is_valid(self):
        valid, broken = verify_chain([])
        assert valid is True
        assert broken is None

    def test_genesis_hash_constant(self):
        assert len(_GENESIS_HASH) == 64
        assert _GENESIS_HASH == "0" * 64


# ---------------------------------------------------------------------------
# DB ledger integration tests (use the test conftest in-memory DB)
# ---------------------------------------------------------------------------

class TestLedgerDB:
    @pytest.mark.asyncio
    async def test_save_and_load_ledger_entries(self):
        from datetime import datetime, timezone
        from app.db import save_ledger_entry, load_ledger_entries, get_ledger_sequence_count

        session_id = "ledger-test-session"
        now = datetime.now(timezone.utc)

        entry1 = build_entry(SAMPLE_MSG, "sig1", "pub1", _GENESIS_HASH, 1, now, session_id=session_id)
        await save_ledger_entry(**entry1)

        msg2 = {**SAMPLE_MSG, "turn_number": 2}
        entry2 = build_entry(msg2, "sig2", "pub2", entry1["entry_hash"], 2, now, session_id=session_id)
        await save_ledger_entry(**entry2)

        loaded = await load_ledger_entries(session_id)
        assert len(loaded) == 2
        assert loaded[0]["sequence"] == 1
        assert loaded[1]["sequence"] == 2
        assert loaded[1]["prev_hash"] == entry1["entry_hash"]

        count = await get_ledger_sequence_count(session_id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_ledger_chain_integrity_via_db(self):
        from datetime import datetime, timezone
        from app.db import save_ledger_entry, load_ledger_entries

        session_id = "chain-integrity-session"
        now = datetime.now(timezone.utc)

        entries = []
        prev = _GENESIS_HASH
        for i in range(5):
            msg = {**SAMPLE_MSG, "turn_number": i + 1}
            entry = build_entry(msg, f"sig{i}", f"pub{i}", prev, i + 1, now, session_id=session_id)
            await save_ledger_entry(**entry)
            entries.append(entry)
            prev = entry["entry_hash"]

        loaded = await load_ledger_entries(session_id)
        valid, broken = verify_chain(loaded)
        assert valid is True
        assert broken is None
