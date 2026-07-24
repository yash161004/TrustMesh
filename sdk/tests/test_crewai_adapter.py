"""Tests for the CrewAI adapter.

These tests skip cleanly if crewai is not installed — the adapter is an optional integration.
"""
from dataclasses import dataclass
from typing import Any, Optional
import pytest

from trustmesh import TrustMeshWatcher

pytest.importorskip("crewai", reason="CrewAI adapter is optional")

from trustmesh.adapters.crewai import TrustMeshCrewCallback  # noqa: E402
from app.crypto.ledger import verify_chain as backend_verify_chain  # noqa: E402


@dataclass
class DummyAgentStep:
    agent: str
    output: str
    action: Optional[str] = None
    tool_input: Optional[Any] = None
    thought: Optional[str] = None


@dataclass
class DummyTaskOutput:
    description: str
    raw: str
    agent: str
    summary: Optional[str] = None


def test_on_step_audits_agent_step():
    watcher = TrustMeshWatcher(agent_id="crew-buyer", session_id="run-crew-1")
    handler = TrustMeshCrewCallback(watcher)

    step = DummyAgentStep(
        agent="buyer-agent",
        output="I propose $100 for 10 units",
        action="propose_terms",
        tool_input={"price": 100, "qty": 10},
        thought="Calculating margin",
    )
    handler.on_step(step)

    assert len(handler.turns) == 1
    turn = handler.turns[0]
    assert turn.message["source"] == "crewai_step"
    assert turn.message["agent"] == "buyer-agent"
    assert turn.message["output"] == "I propose $100 for 10 units"
    assert turn.message["tool"] == "propose_terms"

    ok, broken_at = handler.verify()
    assert ok is True and broken_at is None


def test_on_task_finish_audits_task_output():
    watcher = TrustMeshWatcher(agent_id="crew-seller", session_id="run-crew-2")
    handler = TrustMeshCrewCallback(watcher)

    task_output = DummyTaskOutput(
        description="Negotiate contract terms",
        raw="Deal agreed at $95/unit",
        agent="seller-agent",
        summary="Agreement reached",
    )
    handler.on_task_finish(task_output)

    assert len(handler.turns) == 1
    turn = handler.turns[0]
    assert turn.message["source"] == "crewai_task_finish"
    assert turn.message["agent"] == "seller-agent"
    assert turn.message["raw_output"] == "Deal agreed at $95/unit"

    ok, broken_at = backend_verify_chain(handler.watcher.ledger())
    assert ok is True and broken_at is None


def test_capture_flags_disable_hooks():
    watcher = TrustMeshWatcher(agent_id="a")
    handler = TrustMeshCrewCallback(watcher, capture_steps=False, capture_tasks=True)

    handler.on_step(DummyAgentStep(agent="a", output="ignored step"))
    assert len(handler.turns) == 0

    handler.on_task_finish(DummyTaskOutput(description="task", raw="done", agent="a"))
    assert len(handler.turns) == 1


def test_policy_hook_flows_through_adapter():
    def hook(message):
        text = str(message.get("output", "")) + str(message.get("raw_output", ""))
        return ["urgency_pressure"] if "urgent" in text.lower() else []

    watcher = TrustMeshWatcher(agent_id="a", policy_hook=hook)
    handler = TrustMeshCrewCallback(watcher)

    handler.on_step(DummyAgentStep(agent="a", output="URGENT: accept immediately"))
    assert handler.turns[0].is_flagged is True
    assert "urgency_pressure" in handler.turns[0].flags
