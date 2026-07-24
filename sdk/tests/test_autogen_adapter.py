"""Tests for the AutoGen adapter.

These tests skip cleanly if autogen_agentchat / autogen is not installed — the adapter is an optional integration.
"""
from dataclasses import dataclass
from typing import Any, Optional
import pytest

from trustmesh import TrustMeshWatcher

try:
    import autogen_agentchat  # noqa: F401
except ImportError:
    pytest.importorskip("autogen", reason="AutoGen adapter is optional")

from trustmesh.adapters.autogen import TrustMeshAutoGenHandler  # noqa: E402
from app.crypto.ledger import verify_chain as backend_verify_chain  # noqa: E402


@dataclass
class DummyAutoGenMessage:
    content: str
    source: str
    type: str = "text"


def test_on_message_audits_dict():
    watcher = TrustMeshWatcher(agent_id="autogen-agent-1", session_id="run-ag-1")
    handler = TrustMeshAutoGenHandler(watcher)

    msg = {"role": "assistant", "content": "I accept terms at $95/unit", "name": "BuyerAgent"}
    res = handler.on_message(msg, sender="BuyerAgent", recipient="SellerAgent")

    # Transparent passthrough of original message
    assert res == msg
    assert len(handler.turns) == 1

    turn = handler.turns[0]
    assert turn.message["source"] == "autogen"
    assert turn.message["content"] == "I accept terms at $95/unit"
    assert turn.message["recipient"] == "SellerAgent"

    ok, broken_at = handler.verify()
    assert ok is True and broken_at is None


def test_on_message_audits_object():
    watcher = TrustMeshWatcher(agent_id="autogen-agent-2", session_id="run-ag-2")
    handler = TrustMeshAutoGenHandler(watcher)

    msg = DummyAutoGenMessage(content="Counter-offer $92/unit", source="SellerAgent")
    handler.on_message(msg)

    assert len(handler.turns) == 1
    turn = handler.turns[0]
    assert turn.message["content"] == "Counter-offer $92/unit"
    assert turn.sender == "SellerAgent"

    ok, broken_at = backend_verify_chain(handler.watcher.ledger())
    assert ok is True and broken_at is None


def test_role_filtering():
    watcher = TrustMeshWatcher(agent_id="a")
    handler = TrustMeshAutoGenHandler(watcher, capture_roles={"assistant"})

    handler.on_message({"role": "system", "content": "system prompt"})
    assert len(handler.turns) == 0

    handler.on_message({"role": "assistant", "content": "agent turn"})
    assert len(handler.turns) == 1


def test_policy_hook_flows_through_autogen_adapter():
    def hook(message):
        content = str(message.get("content", ""))
        return ["urgency_pressure"] if "urgent" in content.lower() else []

    watcher = TrustMeshWatcher(agent_id="a", policy_hook=hook)
    handler = TrustMeshAutoGenHandler(watcher)

    handler.on_message({"role": "assistant", "content": "URGENT: confirm now"})
    assert handler.turns[0].is_flagged is True
    assert "urgency_pressure" in handler.turns[0].flags
