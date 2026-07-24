# trustmesh-sdk

A thin, framework-agnostic Python wrapper that makes any AI-agent conversation
**tamper-evident**. Drop it into your agent loop, call `audit_and_sign` on each
turn, and afterwards you can *prove* — cryptographically, not just claim — that
no turn was altered, dropped, or reordered.

It is the same idea as the TrustMesh backend, packaged as reusable middleware:
Ed25519-sign each message, append it to an append-only SHA-256 hash chain,
verify the chain later.

## Install / use

The SDK is standalone — its only runtime dependency is `cryptography`. It does
not need the TrustMesh backend on the path to sign, chain, or verify.

```bash
pip install ./sdk          # or: pip install "trustmesh-sdk[langchain]"
python sdk/examples/minimal_agent_loop.py
```

```python
from trustmesh import TrustMeshWatcher

watcher = TrustMeshWatcher(agent_id="buyer-agent-001", session_id="sess-42")

turn = watcher.audit_and_sign({"role": "buyer", "text": "I offer $90/unit"})
print(turn.entry_hash, turn.is_flagged)

# ... more turns ...

ok, broken_at = watcher.verify()      # (True, None) if the whole chain is intact
```

### Pluggable auditing (no LLM forced)

Auditing is optional and bring-your-own. Pass a `policy_hook` — any callable
`(message: dict) -> list[str]` returning flag strings. Use your own detector,
your framework's guardrails, or the TrustMesh trust engine:

```python
def my_detector(message: dict) -> list[str]:
    return ["urgency_pressure"] if "urgent" in message.get("text", "").lower() else []

watcher = TrustMeshWatcher(agent_id="a", policy_hook=my_detector)
turn = watcher.audit_and_sign({"text": "URGENT: accept now"})
assert turn.is_flagged and "urgency_pressure" in turn.flags
```

Flags are independent of integrity: a flagged turn is still signed and chained,
and flags never break `verify()`. Auditing tells you *what was said*; the chain
proves *that it was not changed afterwards*.

## Framework adapters

Adapters live in `trustmesh/adapters/` and are **optional** — the core package
never imports a framework. Import the one you need explicitly.

### LangChain

`TrustMeshCallbackHandler` attaches to any LangChain runnable and signs every
LLM generation, agent action, and agent finish (the last is where unauthorized
tool calls / commitments surface):

```python
from trustmesh import TrustMeshWatcher
from trustmesh.adapters.langchain import TrustMeshCallbackHandler

watcher = TrustMeshWatcher(agent_id="my-agent", session_id="run-1")
handler = TrustMeshCallbackHandler(watcher)

result = my_chain.invoke(inputs, config={"callbacks": [handler]})

ok, broken_at = handler.verify()      # prove the run was not altered
for turn in handler.turns:
    print(turn.sequence, turn.message["source"], turn.is_flagged)
```

Install the extra: `pip install "trustmesh-sdk[langchain]"`. Toggle capture with
`TrustMeshCallbackHandler(watcher, capture_llm=..., capture_agent=...)`.

### CrewAI

`TrustMeshCrewCallback` binds to CrewAI agent steps (`step_callback`) and task completions (`callback`), signing each tool invocation and output:

```python
from trustmesh import TrustMeshWatcher
from trustmesh.adapters.crewai import TrustMeshCrewCallback

watcher = TrustMeshWatcher(agent_id="crew-agent", session_id="run-1")
handler = TrustMeshCrewCallback(watcher)

agent = Agent(..., step_callback=handler.on_step)
task = Task(..., callback=handler.on_task_finish)

ok, broken_at = handler.verify()
```

Install the extra: `pip install "trustmesh-sdk[crewai]"`. See `sdk/examples/crewai_adapter_demo.py` for a runnable demonstration.

### AutoGen

`TrustMeshAutoGenHandler` attaches to AutoGen message hooks (`autogen-agentchat`):

```python
from trustmesh import TrustMeshWatcher
from trustmesh.adapters.autogen import TrustMeshAutoGenHandler

watcher = TrustMeshWatcher(agent_id="autogen-agent", session_id="run-1")
handler = TrustMeshAutoGenHandler(watcher)

agent.register_hook("process_message_before_send", handler.on_message)

ok, broken_at = handler.verify()
```

Install the extra: `pip install "trustmesh-sdk[autogen]"`. See `sdk/examples/autogen_adapter_demo.py` for a runnable demonstration.

### Any framework (OpenAI message format)

`trustmesh.adapters.generic` needs no framework install — it works with anything
that speaks the OpenAI chat-message shape (`{"role", "content"}`), which covers
raw OpenAI/Anthropic calls, AutoGen, CrewAI, and OpenAI Swarm:

```python
from trustmesh.adapters.generic import audit_messages, audit_chat_completion, audited_step

# audit an existing message list (optionally only the assistant's turns)
audit_messages(watcher, messages, roles={"assistant"})

# audit an OpenAI-style ChatCompletion (dict or SDK object)
audit_chat_completion(watcher, response)

# or wrap any step function transparently
@audited_step(watcher, extract=lambda r: {"role": "assistant", "text": r})
def agent_reply(prompt): ...
```

## What it is — and is not (honest scope)

- **Local-first.** There is no hosted service and therefore no `api_key`. This
  is designed to *integrate with* any agent framework (CrewAI, AutoGen,
  LangChain, OpenAI Swarm, or a plain function), not to be a client for a remote
  API that does not exist yet.
- **Same crypto as the backend, guaranteed — not a fork that drifts.** The
  signing and hash-chain primitives are vendored (`trustmesh/_primitives.py`) so
  the SDK is standalone, but `tests/test_backend_parity.py` imports the backend's
  *own* reference implementation and asserts byte-for-byte identical output
  (canonical JSON, entry hashes) plus cross-verification of signatures. If the
  backend's crypto ever changes, that test fails — so the two provably cannot
  diverge silently.
- **Self-contained identity.** The watcher holds its own in-memory Ed25519 key
  and never touches the backend's on-disk key store or database. Pass an
  existing `private_key` to reuse a stable identity across runs.

## Run the tests

```bash
cd sdk && python -m pytest tests/ -q
```

The suite covers signing/verification, multi-turn chain integrity, tamper and
reorder detection, cross-compatibility with the backend verifier, policy-hook
flagging, stable-identity reuse, and the LangChain adapter (which skips cleanly
if `langchain-core` is not installed).
