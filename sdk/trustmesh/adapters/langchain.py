"""LangChain adapter — audit every LLM output and agent action in a chain.

Attach a :class:`TrustMeshCallbackHandler` to any LangChain runnable and each
LLM generation, agent action, and agent finish is Ed25519-signed and appended
to the watcher's hash chain — so the whole run is tamper-evident afterwards.

This module imports ``langchain_core`` lazily; the core ``trustmesh`` package
does not depend on LangChain. Install LangChain (``pip install langchain-core``)
to use this adapter.

Usage::

    from trustmesh import TrustMeshWatcher
    from trustmesh.adapters.langchain import TrustMeshCallbackHandler

    watcher = TrustMeshWatcher(agent_id="my-agent", session_id="run-1")
    handler = TrustMeshCallbackHandler(watcher)

    result = my_chain.invoke(inputs, config={"callbacks": [handler]})

    ok, broken_at = handler.verify()   # prove the run was not altered
    for turn in handler.turns:
        print(turn.sequence, turn.message["source"], turn.is_flagged)
"""
from __future__ import annotations

from typing import Any, Optional

try:
    from langchain_core.callbacks.base import BaseCallbackHandler
except ImportError as exc:  # pragma: no cover - environment guard
    raise ImportError(
        "trustmesh.adapters.langchain requires langchain-core. "
        "Install it with `pip install langchain-core`."
    ) from exc

from ..watcher import AuditedTurn, TrustMeshWatcher


class TrustMeshCallbackHandler(BaseCallbackHandler):
    """A LangChain callback handler that signs and chains every agent turn.

    Parameters
    ----------
    watcher:
        The :class:`TrustMeshWatcher` to record turns into.
    capture_llm:
        If True (default), audit each LLM generation (``on_llm_end``).
    capture_agent:
        If True (default), audit agent actions and finishes
        (``on_agent_action`` / ``on_agent_finish``) — this is where
        unauthorized tool calls / commitments show up.
    """

    # LangChain checks this to allow the handler to run inline.
    raise_error: bool = False

    def __init__(
        self,
        watcher: TrustMeshWatcher,
        *,
        capture_llm: bool = True,
        capture_agent: bool = True,
    ) -> None:
        super().__init__()
        self.watcher = watcher
        self.capture_llm = capture_llm
        self.capture_agent = capture_agent
        self.turns: list[AuditedTurn] = []

    # ------------------------------------------------------------------
    def _audit(self, message: dict[str, Any]) -> AuditedTurn:
        turn = self.watcher.audit_and_sign(message)
        self.turns.append(turn)
        return turn

    # ------------------------------------------------------------------
    # LangChain callback hooks
    # ------------------------------------------------------------------
    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        if not self.capture_llm:
            return
        for generation_list in getattr(response, "generations", []) or []:
            for generation in generation_list or []:
                text = getattr(generation, "text", None)
                if text:
                    self._audit({"source": "llm", "text": text})

    def on_agent_action(self, action: Any, **kwargs: Any) -> None:
        if not self.capture_agent:
            return
        self._audit({
            "source": "agent_action",
            "tool": getattr(action, "tool", None),
            "tool_input": getattr(action, "tool_input", None),
            "log": getattr(action, "log", None),
        })

    def on_agent_finish(self, finish: Any, **kwargs: Any) -> None:
        if not self.capture_agent:
            return
        self._audit({
            "source": "agent_finish",
            "return_values": getattr(finish, "return_values", None),
            "log": getattr(finish, "log", None),
        })

    # ------------------------------------------------------------------
    def verify(self) -> tuple[bool, Optional[int]]:
        """Verify the whole recorded chain — ``(is_valid, broken_at_sequence)``."""
        return self.watcher.verify()
