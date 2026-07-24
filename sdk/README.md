# trustmesh-sdk

A thin, framework-agnostic Python wrapper that makes any AI-agent conversation
**tamper-evident**. Drop it into your agent loop, call `audit_and_sign` on each
turn, and afterwards you can *prove* — cryptographically, not just claim — that
no turn was altered, dropped, or reordered.

It is the same idea as the TrustMesh backend, packaged as reusable middleware:
Ed25519-sign each message, append it to an append-only SHA-256 hash chain,
verify the chain later.

## Install / use (from a repo checkout)

```bash
# The SDK currently reuses the TrustMesh backend's crypto primitives, so it is
# used from within this repository. `backend/` is added to sys.path automatically.
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

## What it is — and is not (honest scope)

- **Local-first.** There is no hosted service and therefore no `api_key`. This
  is designed to *integrate with* any agent framework (CrewAI, AutoGen,
  LangChain, OpenAI Swarm, or a plain function), not to be a client for a remote
  API that does not exist yet.
- **Same crypto as the backend, not a fork.** The signing and hash-chain
  primitives are imported directly from the TrustMesh backend
  (`trustmesh/_crypto.py`). The test suite asserts that SDK-produced records
  verify under the backend's *own* `verify_chain` / `verify_signature`, so there
  is no risk of the two drifting apart.
- **Self-contained identity.** The watcher holds its own in-memory Ed25519 key
  and never touches the backend's on-disk key store or database. Pass an
  existing `private_key` to reuse a stable identity across runs.
- **Not yet a standalone distribution.** Because it imports the backend
  primitives, it is used from a repo checkout today. Packaging it fully
  standalone — vendoring the primitives, or extracting a shared
  `trustmesh-core` both sides depend on — is deliberate follow-on work.

## Run the tests

```bash
cd sdk && python -m pytest tests/ -q
```

The suite covers signing/verification, multi-turn chain integrity, tamper and
reorder detection, cross-compatibility with the backend verifier, policy-hook
flagging, stable-identity reuse, and the LangChain adapter (which skips cleanly
if `langchain-core` is not installed).
