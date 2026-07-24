"""Tests for the framework-neutral adapters (generic.py). No framework needed."""
from trustmesh import TrustMeshWatcher
from trustmesh.adapters.generic import (
    audit_chat_completion,
    audit_messages,
    audited_step,
)


def test_audited_step_signs_and_passes_value_through():
    w = TrustMeshWatcher(agent_id="a")

    @audited_step(w, extract=lambda r: {"role": "assistant", "text": r})
    def reply(prompt: str) -> str:
        return f"echo:{prompt}"

    out = reply("hello")
    assert out == "echo:hello"       # return value untouched
    assert len(w) == 1               # one turn recorded
    assert w.ledger()[0]["sequence"] == 0
    assert w.verify()[0] is True


def test_audited_step_identity_default_requires_dict():
    w = TrustMeshWatcher(agent_id="a")

    @audited_step(w)
    def step() -> dict:
        return {"role": "assistant", "content": "hi"}

    step()
    assert len(w) == 1


def test_audited_step_extract_none_skips():
    w = TrustMeshWatcher(agent_id="a")

    @audited_step(w, extract=lambda r: None)  # nothing to audit this call
    def step() -> str:
        return "ignored"

    assert step() == "ignored"
    assert len(w) == 0


def test_audit_messages_orders_and_chains():
    w = TrustMeshWatcher(agent_id="a")
    msgs = [
        {"role": "user", "content": "offer?"},
        {"role": "assistant", "content": "$90"},
        {"role": "user", "content": "deal"},
    ]
    turns = audit_messages(w, msgs)
    assert [t.sender for t in turns] == ["user", "assistant", "user"]
    assert len(w) == 3
    assert w.verify()[0] is True


def test_audit_messages_role_filter():
    w = TrustMeshWatcher(agent_id="a")
    msgs = [
        {"role": "user", "content": "offer?"},
        {"role": "assistant", "content": "$90"},
        {"role": "system", "content": "be nice"},
        {"role": "assistant", "content": "$88"},
    ]
    turns = audit_messages(w, msgs, roles={"assistant"})
    assert len(turns) == 2
    assert all(t.sender == "assistant" for t in turns)
    assert [t.message["content"] for t in turns] == ["$90", "$88"]


def test_audit_chat_completion_from_dict():
    w = TrustMeshWatcher(agent_id="a")
    response = {
        "choices": [
            {"message": {"role": "assistant", "content": "final offer $91"}},
        ]
    }
    turns = audit_chat_completion(w, response)
    assert len(turns) == 1
    assert turns[0].message["content"] == "final offer $91"
    assert turns[0].sender == "assistant"
    assert w.verify()[0] is True


def test_audit_chat_completion_from_objects():
    # Mimic the OpenAI SDK's attribute-based response objects.
    class _Msg:
        role = "assistant"
        content = "counter at $92"

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    w = TrustMeshWatcher(agent_id="a")
    turns = audit_chat_completion(w, _Resp())
    assert len(turns) == 1
    assert turns[0].message["content"] == "counter at $92"
