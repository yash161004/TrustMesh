"""CrewAI adapter — audit agent steps and task completions in CrewAI workflows.

Attach a :class:`TrustMeshCrewCallback` to CrewAI agents or tasks. Each agent step,
tool invocation, and task completion is Ed25519-signed and appended to the watcher's
hash chain — so the whole run is tamper-evident afterwards.

This module imports ``crewai`` lazily; the core ``trustmesh`` package does not
depend on CrewAI. Install CrewAI (``pip install crewai``) to use this adapter.

Usage::

    from trustmesh import TrustMeshWatcher
    from trustmesh.adapters.crewai import TrustMeshCrewCallback

    watcher = TrustMeshWatcher(agent_id="crew-agent", session_id="run-1")
    handler = TrustMeshCrewCallback(watcher)

    agent = Agent(..., step_callback=handler.on_step)
    task = Task(..., callback=handler.on_task_finish)

    ok, broken_at = handler.verify()   # prove the run was not altered
"""
from __future__ import annotations

from typing import Any, Optional

try:
    import crewai  # type: ignore # noqa: F401
except ImportError as exc:  # pragma: no cover - environment guard
    raise ImportError(
        "trustmesh.adapters.crewai requires crewai. "
        "Install it with `pip install crewai`."
    ) from exc

from ..watcher import AuditedTurn, TrustMeshWatcher


class TrustMeshCrewCallback:
    """A CrewAI callback handler that signs and chains agent steps and task outputs.

    Parameters
    ----------
    watcher:
        The :class:`TrustMeshWatcher` to record turns into.
    capture_steps:
        If True (default), audit each agent execution step via :meth:`on_step`.
    capture_tasks:
        If True (default), audit each task completion via :meth:`on_task_finish`.
    """

    def __init__(
        self,
        watcher: TrustMeshWatcher,
        *,
        capture_steps: bool = True,
        capture_tasks: bool = True,
    ) -> None:
        self.watcher = watcher
        self.capture_steps = capture_steps
        self.capture_tasks = capture_tasks
        self.turns: list[AuditedTurn] = []

    def _audit(self, message: dict[str, Any], sender: Optional[str] = None) -> AuditedTurn:
        turn = self.watcher.audit_and_sign(message, sender=sender)
        self.turns.append(turn)
        return turn

    def on_step(self, step: Any) -> None:
        """Callback for CrewAI ``Agent(step_callback=...)``.

        Accepts an AgentStep object, dict, or text payload emitted during execution.
        """
        if not self.capture_steps:
            return

        message: dict[str, Any] = {"source": "crewai_step"}
        sender = None

        if isinstance(step, dict):
            message.update(step)
            sender = step.get("agent") or step.get("role")
        else:
            # Duck-type AgentStep / AgentAction from CrewAI
            agent = getattr(step, "agent", None) or getattr(step, "agent_role", None)
            if agent:
                sender = str(agent)
                message["agent"] = sender
            output = getattr(step, "output", None) or getattr(step, "result", None) or getattr(step, "text", None)
            if output is not None:
                message["output"] = str(output)
            action = getattr(step, "action", None) or getattr(step, "tool", None)
            if action:
                message["tool"] = str(action)
            tool_input = getattr(step, "tool_input", None)
            if tool_input is not None:
                message["tool_input"] = tool_input
            thought = getattr(step, "thought", None)
            if thought:
                message["thought"] = str(thought)

            # Fallback if no specific attributes found
            if len(message) == 1:
                message["raw"] = str(step)

        self._audit(message, sender=sender)

    def on_task_finish(self, task_output: Any) -> None:
        """Callback for CrewAI ``Task(callback=...)`` or ``Crew(task_callback=...)``.

        Accepts TaskOutput, dict, or string return value.
        """
        if not self.capture_tasks:
            return

        message: dict[str, Any] = {"source": "crewai_task_finish"}
        sender = None

        if isinstance(task_output, dict):
            message.update(task_output)
            sender = task_output.get("agent") or task_output.get("role")
        elif isinstance(task_output, str):
            message["raw_output"] = task_output
        else:
            description = getattr(task_output, "description", None)
            if description:
                message["task_description"] = str(description)
            raw = getattr(task_output, "raw", None) or getattr(task_output, "output", None)
            if raw is not None:
                message["raw_output"] = str(raw)
            agent = getattr(task_output, "agent", None)
            if agent:
                sender = str(agent)
                message["agent"] = sender
            summary = getattr(task_output, "summary", None)
            if summary:
                message["summary"] = str(summary)

            if len(message) == 1:
                message["raw"] = str(task_output)

        self._audit(message, sender=sender)

    def verify(self) -> tuple[bool, Optional[int]]:
        """Verify the whole recorded chain — ``(is_valid, broken_at_sequence)``."""
        return self.watcher.verify()
