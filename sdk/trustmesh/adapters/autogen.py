"""AutoGen adapter — audit messages and agent events in autogen-agentchat workflows.

Attach a :class:`TrustMeshAutoGenHandler` or message hook to AutoGen agents or
teams. Each message exchanged between AutoGen agents is Ed25519-signed and
appended to the watcher's hash chain.

This module imports ``autogen_agentchat`` (or fallback ``autogen``) lazily; the
core ``trustmesh`` package does not depend on AutoGen. Install AutoGen
(``pip install autogen-agentchat``) to use this adapter.

Usage::

    from trustmesh import TrustMeshWatcher
    from trustmesh.adapters.autogen import TrustMeshAutoGenHandler

    watcher = TrustMeshWatcher(agent_id="autogen-agent", session_id="run-1")
    handler = TrustMeshAutoGenHandler(watcher)

    # Use as a message hook or event listener in autogen-agentchat
    agent.register_hook("process_message_before_send", handler.on_message)

    ok, broken_at = handler.verify()   # prove the run was not altered
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

try:
    import autogen_agentchat  # type: ignore # noqa: F401
except ImportError:
    try:
        import autogen  # type: ignore # noqa: F401
    except ImportError as exc:  # pragma: no cover - environment guard
        raise ImportError(
            "trustmesh.adapters.autogen requires autogen-agentchat (or autogen). "
            "Install it with `pip install autogen-agentchat`."
        ) from exc

from ..watcher import AuditedTurn, TrustMeshWatcher


class TrustMeshAutoGenHandler:
    """An AutoGen message handler that signs and chains agent messages and events.

    Parameters
    ----------
    watcher:
        The :class:`TrustMeshWatcher` to record turns into.
    capture_roles:
        Optional set/list of roles/senders to capture (e.g. ``{"assistant", "user"}``).
        If None, all messages are captured.
    """

    def __init__(
        self,
        watcher: TrustMeshWatcher,
        *,
        capture_roles: Optional[Iterable[str]] = None,
    ) -> None:
        self.watcher = watcher
        self.capture_roles = set(capture_roles) if capture_roles is not None else None
        self.turns: list[AuditedTurn] = []

    def _audit(self, message: dict[str, Any], sender: Optional[str] = None) -> Optional[AuditedTurn]:
        if self.capture_roles is not None:
            check_role = sender or message.get("role") or message.get("sender")
            if check_role and check_role not in self.capture_roles:
                return None

        turn = self.watcher.audit_and_sign(message, sender=sender)
        self.turns.append(turn)
        return turn

    def on_message(
        self,
        message: Any,
        sender: Any = None,
        recipient: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Message hook callback compatible with AutoGen agent hooks.

        Accepts dicts, TextMessage, MultiModalMessage, or custom AutoGen event objects.
        Returns the original message un-modified so it functions transparently as a hook.
        """
        parsed_msg: dict[str, Any] = {"source": "autogen"}
        resolved_sender = None

        if sender:
            resolved_sender = str(getattr(sender, "name", sender))

        if isinstance(message, dict):
            parsed_msg.update(message)
            if not resolved_sender:
                resolved_sender = message.get("sender") or message.get("role") or message.get("name")
        elif isinstance(message, str):
            parsed_msg["content"] = message
        else:
            # Duck-type AutoGen message/event objects (e.g. TextMessage, ToolCallMessage)
            content = getattr(message, "content", None)
            if content is not None:
                parsed_msg["content"] = str(content)

            msg_sender = getattr(message, "source", None) or getattr(message, "sender", None) or getattr(message, "role", None)
            if msg_sender:
                resolved_sender = str(msg_sender)

            msg_type = getattr(message, "type", None)
            if msg_type:
                parsed_msg["type"] = str(msg_type)

            tool_calls = getattr(message, "tool_calls", None)
            if tool_calls:
                parsed_msg["tool_calls"] = tool_calls

            if len(parsed_msg) == 1:
                parsed_msg["raw"] = str(message)

        if recipient:
            parsed_msg["recipient"] = str(getattr(recipient, "name", recipient))

        self._audit(parsed_msg, sender=resolved_sender)
        return message

    def verify(self) -> tuple[bool, Optional[int]]:
        """Verify the whole recorded chain — ``(is_valid, broken_at_sequence)``."""
        return self.watcher.verify()
