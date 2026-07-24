"""
Tests for tamper detection in the hash-chained ledger (crypto commitment layer).

Verifies that any modification to a persisted ledger entry — whether to
message_json, signature, or entry_hash — is detected by verify_chain()
and reflected in the API response.

Test sequence per scenario:
  1. Create a session via API
  2. Build and persist a valid 3-entry chain
  3. GET ledger — assert chain_valid=True
  4. Tamper with one field (message_json / signature / entry_hash)
  5. GET ledger — assert chain_valid=False, broken_at matches
  6. Restore the field — GET ledger — assert chain_valid=True
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.crypto.ledger import _GENESIS_HASH, build_entry, verify_chain
from app.crypto.signing import canonical_json
from app.db import User
from app.main import app
from app.auth.dependencies import get_current_user

from fastapi import Request

def dummy_user(request: Request):
    user = User(id="test-user-1", role="standard", org_id="test-org-1")
    request.state.user = user
    return user

@pytest.fixture(autouse=True)
def mock_auth():
    app.dependency_overrides[get_current_user] = dummy_user
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_MSG = {
    "message_type": "OFFER",
    "sender": "buyer-agent-001",
    "price": 149.99,
    "quantity": 500,
}


async def _build_and_save_chain(session_id: str, count: int = 3):
    """Build and persist *count* valid ledger entries, returning the dicts."""
    from app.db import save_ledger_entry

    entries = []
    prev = _GENESIS_HASH
    now = datetime.now(timezone.utc)

    for i in range(count):
        msg = {**SAMPLE_MSG, "turn_number": i + 1}
        entry = build_entry(
            message_dict=msg,
            signature=f"test-sig-{i}",
            signer_public_key="test-pub-key",
            prev_hash=prev,
            sequence=i + 1,
            created_at=now,
            session_id=session_id,
        )
        await save_ledger_entry(**entry)
        entries.append(entry)
        prev = entry["entry_hash"]

    return entries


async def _get_async_session():
    """Get an async DB session (from the conftest in-memory engine)."""
    import app.db as db_module

    factory = db_module._async_session_factory
    if factory is None:
        raise RuntimeError("DB not initialised — conftest should have set up _async_session_factory")
    async with factory() as session:
        return session


async def _tamper_field(session_id: str, sequence: int, field: str, new_value):
    """Directly update a ledger entry field in the database."""
    async with await _get_async_session() as db:
        result = await db.execute(
            select(db_module.LedgerEntryRecord)  # noqa: F821
            .where(
                db_module.LedgerEntryRecord.session_id == session_id,
                db_module.LedgerEntryRecord.sequence == sequence,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise AssertionError(f"No ledger entry for {session_id}:{sequence}")

        if field == "message_json":
            # Tamper with the price inside the message JSON
            msg = json.loads(record.message_json)
            msg["price"] = 999999.99
            record.message_json = json.dumps(msg, sort_keys=True, separators=(",", ":"))
        elif field == "signature":
            record.signature = "tampered-signature"
        elif field == "entry_hash":
            record.entry_hash = "t" + record.entry_hash[1:]
        elif field == "signer_public_key":
            record.signer_public_key = "tampered-pub-key"
        else:
            setattr(record, field, new_value)

        await db.commit()


async def _restore_field(session_id: str, sequence: int, field: str, original: dict):
    """Revert a ledger entry field to the original dict value."""
    async with await _get_async_session() as db:
        result = await db.execute(
            select(db_module.LedgerEntryRecord)
            .where(
                db_module.LedgerEntryRecord.session_id == session_id,
                db_module.LedgerEntryRecord.sequence == sequence,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise AssertionError(f"No ledger entry for {session_id}:{sequence}")

        setattr(record, field, original[field])
        await db.commit()


# Lazy import to avoid conftest ordering issues
import app.db as db_module  # noqa: E402


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTamperDetectionDirect:
    """Verify chain integrity at the verify_chain() level (unit)."""

    def test_tamper_message_json_breaks_chain_direct(self):
        entries = []
        prev = _GENESIS_HASH
        for i in range(3):
            msg = {**SAMPLE_MSG, "turn_number": i + 1}
            entry = build_entry(msg, f"sig{i}", f"pub{i}", prev, i + 1)
            entries.append(entry)
            prev = entry["entry_hash"]

        assert verify_chain(entries) == (True, None)

        # Tamper with message_json
        tampered_msg = {**SAMPLE_MSG, "turn_number": 1, "price": 999999.99}
        entries[0]["message_json"] = json.dumps(tampered_msg, sort_keys=True, separators=(",", ":"))
        valid, broken = verify_chain(entries)
        assert valid is False
        assert broken == 1

    def test_tamper_entry_hash_breaks_chain_direct(self):
        entries = []
        prev = _GENESIS_HASH
        for i in range(2):
            msg = {**SAMPLE_MSG, "turn_number": i + 1}
            entry = build_entry(msg, f"sig{i}", f"pub{i}", prev, i + 1)
            entries.append(entry)
            prev = entry["entry_hash"]

        assert verify_chain(entries) == (True, None)

        # Tamper with entry_hash of first entry
        entries[0]["entry_hash"] = "a" * 64
        valid, broken = verify_chain(entries)
        assert valid is False
        assert broken == 1

    def test_tamper_signature_does_not_break_hash_chain(self):
        """The hash chain is computed over (message_json, signature, signer_public_key, prev_hash, sequence).

        Changing signature changes the computed hash → chain breaks.
        """
        entries = []
        prev = _GENESIS_HASH
        for i in range(2):
            msg = {**SAMPLE_MSG, "turn_number": i + 1}
            entry = build_entry(msg, f"sig{i}", f"pub{i}", prev, i + 1)
            entries.append(entry)
            prev = entry["entry_hash"]

        # Tamper with signature
        entries[0]["signature"] = "tampered-signature"
        valid, broken = verify_chain(entries)
        assert valid is False
        assert broken == 1

    def test_prev_hash_tamper_breaks_link(self):
        entries = []
        prev = _GENESIS_HASH
        for i in range(3):
            msg = {**SAMPLE_MSG, "turn_number": i + 1}
            entry = build_entry(msg, f"sig{i}", f"pub{i}", prev, i + 1)
            entries.append(entry)
            prev = entry["entry_hash"]

        # Tamper with prev_hash of second entry (points to non-existent hash)
        entries[1]["prev_hash"] = "b" * 64
        valid, broken = verify_chain(entries)
        assert valid is False
        assert broken == 2


class TestTamperDetectionViaAPI:
    """End-to-end: insert valid chain, tamper via DB, verify API reports break."""

    @pytest.mark.asyncio
    async def test_ledger_valid_after_insert(self, test_client):
        """Freshly inserted valid chain returns chain_valid=True."""
        resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
        assert resp.status_code == 200
        sid = resp.json()["session_id"]

        await _build_and_save_chain(sid, 3)

        ledger_resp = test_client.get(f"/api/v1/sessions/{sid}/ledger")
        assert ledger_resp.status_code == 200
        data = ledger_resp.json()
        assert data["chain_valid"] is True
        assert data["broken_at"] is None
        assert len(data["entries"]) == 3

    @pytest.mark.asyncio
    async def test_tamper_message_json_via_api(self, test_client):
        """Tampering with message_json in DB causes chain_valid=False via API."""
        resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
        sid = resp.json()["session_id"]

        await _build_and_save_chain(sid, 3)

        # Confirm valid before tamper
        ledger_resp = test_client.get(f"/api/v1/sessions/{sid}/ledger")
        assert ledger_resp.json()["chain_valid"] is True

        # Tamper with message_json of entry 1
        await _tamper_field(sid, 1, "message_json", None)

        # Confirm chain is now broken
        ledger_resp = test_client.get(f"/api/v1/sessions/{sid}/ledger")
        data = ledger_resp.json()
        assert data["chain_valid"] is False
        assert data["broken_at"] == 1

    @pytest.mark.asyncio
    async def test_tamper_entry_hash_via_api(self, test_client):
        """Tampering with entry_hash in DB causes chain_valid=False."""
        resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
        sid = resp.json()["session_id"]

        entries = await _build_and_save_chain(sid, 2)

        # Confirm valid before tamper
        ledger_resp = test_client.get(f"/api/v1/sessions/{sid}/ledger")
        assert ledger_resp.json()["chain_valid"] is True

        # Tamper with entry_hash of entry 1
        await _tamper_field(sid, 1, "entry_hash", None)

        ledger_resp = test_client.get(f"/api/v1/sessions/{sid}/ledger")
        data = ledger_resp.json()
        assert data["chain_valid"] is False
        assert data["broken_at"] == 1

    @pytest.mark.asyncio
    async def test_middle_entry_tamper_detected(self, test_client):
        """Tampering with a middle entry in a longer chain is also detected."""
        resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
        sid = resp.json()["session_id"]

        await _build_and_save_chain(sid, 5)

        # Confirm valid
        ledger_resp = test_client.get(f"/api/v1/sessions/{sid}/ledger")
        assert ledger_resp.json()["chain_valid"] is True

        # Tamper with entry 3 (middle of 5)
        await _tamper_field(sid, 3, "message_json", None)

        ledger_resp = test_client.get(f"/api/v1/sessions/{sid}/ledger")
        data = ledger_resp.json()
        assert data["chain_valid"] is False
        assert data["broken_at"] == 3

    @pytest.mark.asyncio
    async def test_restore_after_tamper(self, test_client):
        """Restoring the tampered field returns chain to valid."""
        resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
        sid = resp.json()["session_id"]

        entries = await _build_and_save_chain(sid, 3)

        # Capture original for restoration
        original_msg_json = entries[0]["message_json"]

        # Tamper
        await _tamper_field(sid, 1, "message_json", None)

        ledger_resp = test_client.get(f"/api/v1/sessions/{sid}/ledger")
        assert ledger_resp.json()["chain_valid"] is False

        # Restore
        await _restore_field(sid, 1, "message_json", {"message_json": original_msg_json})

        ledger_resp = test_client.get(f"/api/v1/sessions/{sid}/ledger")
        assert ledger_resp.json()["chain_valid"] is True
        assert ledger_resp.json()["broken_at"] is None

    @pytest.mark.asyncio
    async def test_empty_ledger_is_valid(self, test_client):
        """A session with no ledger entries should show chain_valid=True."""
        resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
        sid = resp.json()["session_id"]

        ledger_resp = test_client.get(f"/api/v1/sessions/{sid}/ledger")
        data = ledger_resp.json()
        assert data["chain_valid"] is True
        assert data["broken_at"] is None
        assert data["entries"] == []


class TestTamperAlertWiring:
    """A tamper detected on a ledger *read* (not just at write time) must fire
    the same alert path. Covers the two read-side verify_chain() call sites:
    GET /ledger and GET /export (PDF)."""

    @pytest.mark.asyncio
    async def test_ledger_read_fires_alert_on_tamper(self, test_client, monkeypatch):
        from unittest.mock import AsyncMock
        import app.routes.sessions as sessions_route

        spy = AsyncMock(return_value=True)
        monkeypatch.setattr(sessions_route, "trigger_tamper_alert", spy)

        resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
        sid = resp.json()["session_id"]
        await _build_and_save_chain(sid, 3)

        # Valid read -> no alert.
        assert test_client.get(f"/api/v1/sessions/{sid}/ledger").json()["chain_valid"] is True
        spy.assert_not_awaited()

        # Tamper, then read -> alert fires with the read-path reason.
        await _tamper_field(sid, 2, "message_json", None)
        data = test_client.get(f"/api/v1/sessions/{sid}/ledger").json()
        assert data["chain_valid"] is False

        spy.assert_awaited_once()
        kwargs = spy.await_args.kwargs
        assert kwargs["session_id"] == sid
        assert kwargs["reason"] == "ledger_read_integrity_check"
        assert kwargs["broken_at"] == 2
        assert kwargs["org_id"] == "test-org-1"

    @pytest.mark.asyncio
    async def test_pdf_export_fires_alert_on_tamper(self, test_client, monkeypatch):
        from unittest.mock import AsyncMock
        import app.routes.sessions as sessions_route

        spy = AsyncMock(return_value=True)
        monkeypatch.setattr(sessions_route, "trigger_tamper_alert", spy)

        resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
        sid = resp.json()["session_id"]
        await _build_and_save_chain(sid, 3)
        await _tamper_field(sid, 1, "entry_hash", None)

        export_resp = test_client.get(f"/api/v1/sessions/{sid}/export")
        assert export_resp.status_code == 200

        spy.assert_awaited_once()
        kwargs = spy.await_args.kwargs
        assert kwargs["session_id"] == sid
        assert kwargs["reason"] == "pdf_export_integrity_check"
        assert kwargs["broken_at"] == 1

    @pytest.mark.asyncio
    async def test_alert_dedups_across_repeated_reads(self, test_client):
        """The real alert path claims each session once, so repeated reads of a
        tampered ledger don't re-page. Uses the genuine trigger_tamper_alert."""
        from app.crypto.ledger_alerts import clear_alerted_sessions_cache
        from app.db import get_agent_reputation  # noqa: F401  (ensures db module loaded)

        clear_alerted_sessions_cache()

        resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
        sid = resp.json()["session_id"]
        await _build_and_save_chain(sid, 3)
        await _tamper_field(sid, 2, "message_json", None)

        # Two reads of the same tampered ledger — both report broken, no error.
        for _ in range(2):
            data = test_client.get(f"/api/v1/sessions/{sid}/ledger").json()
            assert data["chain_valid"] is False
            assert data["broken_at"] == 2

        # The DB claim was taken exactly once.
        import app.db as db_module
        from sqlalchemy import select
        factory = db_module._async_session_factory
        async with factory() as db:
            row = (
                await db.execute(
                    select(db_module.SessionRecord.tamper_alerted_at).where(
                        db_module.SessionRecord.id == sid
                    )
                )
            ).first()
        assert row is not None and row[0] is not None, "tamper_alerted_at should be claimed once"

        clear_alerted_sessions_cache()
