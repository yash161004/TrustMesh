"""Framework-neutral adapters.

No framework import at all — these work with any agent library that speaks the
OpenAI chat-message shape (``{"role": ..., "content": ...}``), which in practice
covers raw OpenAI/Anthropic calls, AutoGen, CrewAI, and OpenAI Swarm — or with
any plain callable via the ``audited_step`` decorator.

Because there is nothing framework-specific to import, this module has no extra
dependency and is fully exercised by the test suite.
"""
from __future__ import annotations

import functools
from typing import Any, Callable, Iterable, Optional

from ..watcher import AuditedTurn, TrustMeshWatcher

# Maps a wrapped callable's return value to the message dict that should be
# signed. Defaults to identity (the return value must already be a dict).
Extract = Callable[[Any], Optional[dict[str, Any]]]


def audited_step(
    watcher: TrustMeshWatcher,
    *,
    extract: Optional[Extract] = None,
    sender: Optional[str] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: audit the message a step function produces, transparently.

    The wrapped function's return value is passed through unchanged; a signed
    turn is appended to ``watcher`` as a side effect. ``extract`` maps the return
    value to a message dict (defaults to identity — the return value must be a
    dict). If ``extract`` returns ``None``, nothing is audited for that call.

    Example::

        @audited_step(watcher, extract=lambda r: {"role": "assistant", "text": r})
        def agent_reply(prompt: str) -> str:
            return llm(prompt)
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = fn(*args, **kwargs)
            message = extract(result) if extract is not None else result
            if isinstance(message, dict):
                watcher.audit_and_sign(message, sender=sender)
            return result

        return wrapper

    return decorator


def audit_messages(
    watcher: TrustMeshWatcher,
    messages: Iterable[dict[str, Any]],
    *,
    roles: Optional[Iterable[str]] = None,
) -> list[AuditedTurn]:
    """Audit a sequence of OpenAI-style message dicts in order.

    Each message is signed and chained as given. Optionally restrict to certain
    ``roles`` (e.g. only ``{"assistant"}``) — a common choice when you only want
    to bind what the agent *emitted*, not the prompts fed to it. The message's
    ``role`` becomes the turn's ``sender``.
    """
    role_filter = set(roles) if roles is not None else None
    turns: list[AuditedTurn] = []
    for message in messages:
        if not isinstance(message, dict):
            raise TypeError("each message must be a dict")
        role = message.get("role")
        if role_filter is not None and role not in role_filter:
            continue
        turns.append(watcher.audit_and_sign(message, sender=role))
    return turns


def audit_chat_completion(
    watcher: TrustMeshWatcher,
    completion: Any,
) -> list[AuditedTurn]:
    """Audit the assistant message(s) of an OpenAI-style chat completion.

    Accepts either a response dict (``{"choices": [{"message": {...}}]}``) or an
    SDK object exposing ``.choices[i].message`` with ``.role`` / ``.content``.
    Returns the audited assistant turns.
    """
    choices = _get(completion, "choices") or []
    turns: list[AuditedTurn] = []
    for choice in choices:
        message = _get(choice, "message")
        if message is None:
            continue
        role = _get(message, "role") or "assistant"
        content = _get(message, "content")
        turns.append(
            watcher.audit_and_sign({"role": role, "content": content}, sender=role)
        )
    return turns


def _get(obj: Any, key: str) -> Any:
    """Read ``key`` from a dict or an attribute from an object (duck-typed)."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
