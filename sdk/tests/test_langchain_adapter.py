"""Tests for the LangChain adapter.

These use real langchain_core payload objects (LLMResult / AgentAction /
AgentFinish) fed through the callback hooks, and skip cleanly if langchain_core
is not installed — the adapter is an optional integration.
"""
import uuid

import pytest

from trustmesh import TrustMeshWatcher

pytest.importorskip("langchain_core", reason="LangChain adapter is optional")

from langchain_core.agents import AgentAction, AgentFinish  # noqa: E402
from langchain_core.outputs import Generation, LLMResult  # noqa: E402

from trustmesh.adapters.langchain import TrustMeshCallbackHandler  # noqa: E402

# The backend verifier — proving adapter-produced records verify under the
# real TrustMesh crypto, same as the core SDK tests.
from app.crypto.ledger import verify_chain as backend_verify_chain  # noqa: E402


def _handler():
    watcher = TrustMeshWatcher(agent_id="lc-agent", session_id="run-1")
    return TrustMeshCallbackHandler(watcher)


def _llm_result(*texts):
    return LLMResult(generations=[[Generation(text=t)] for t in texts])


def test_llm_end_audits_each_generation():
    h = _handler()
    h.on_llm_end(_llm_result("I offer $90/unit", "counter at $92"), run_id=uuid.uuid4())

    assert len(h.turns) == 2
    assert [t.message["source"] for t in h.turns] == ["llm", "llm"]
    assert h.turns[0].message["text"] == "I offer $90/unit"
    ok, broken_at = h.verify()
    assert ok is True and broken_at is None


def test_agent_action_and_finish_are_audited():
    h = _handler()
    h.on_agent_action(
        AgentAction(tool="commit_deal", tool_input={"price": 93}, log="deciding"),
        run_id=uuid.uuid4(),
    )
    h.on_agent_finish(
        AgentFinish(return_values={"output": "deal closed at 93"}, log="done"),
        run_id=uuid.uuid4(),
    )

    assert [t.message["source"] for t in h.turns] == ["agent_action", "agent_finish"]
    assert h.turns[0].message["tool"] == "commit_deal"
    assert h.turns[1].message["return_values"]["output"] == "deal closed at 93"
    assert h.verify()[0] is True


def test_mixed_run_chain_verifies_under_backend():
    h = _handler()
    h.on_llm_end(_llm_result("thinking about the offer"), run_id=uuid.uuid4())
    h.on_agent_action(
        AgentAction(tool="lookup_price", tool_input="widget", log=""), run_id=uuid.uuid4()
    )
    h.on_llm_end(_llm_result("final: $91"), run_id=uuid.uuid4())

    assert len(h.turns) == 3
    ok, broken_at = backend_verify_chain(h.watcher.ledger())
    assert ok is True and broken_at is None


def test_capture_flags_disable_hooks():
    watcher = TrustMeshWatcher(agent_id="a")
    h = TrustMeshCallbackHandler(watcher, capture_llm=False, capture_agent=True)
    h.on_llm_end(_llm_result("ignored"), run_id=uuid.uuid4())
    assert len(h.turns) == 0  # llm capture disabled

    h.on_agent_action(AgentAction(tool="t", tool_input="i", log=""), run_id=uuid.uuid4())
    assert len(h.turns) == 1  # agent capture still on


def test_policy_hook_flows_through_adapter():
    def hook(message):
        text = str(message.get("text", "")) + str(message.get("log", ""))
        return ["urgency_pressure"] if "urgent" in text.lower() else []

    watcher = TrustMeshWatcher(agent_id="a", policy_hook=hook)
    h = TrustMeshCallbackHandler(watcher)
    h.on_llm_end(_llm_result("URGENT: decide now"), run_id=uuid.uuid4())

    assert h.turns[0].is_flagged is True
    assert "urgency_pressure" in h.turns[0].flags
