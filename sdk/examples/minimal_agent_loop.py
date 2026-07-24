"""Minimal example: wrap a two-agent negotiation with TrustMeshWatcher.

Run from the repo root:

    python sdk/examples/minimal_agent_loop.py

It signs each turn, prints the running hash chain, then demonstrates that
tampering with a past turn is detected.
"""
import sys
from pathlib import Path

# Make `trustmesh` importable when run directly from a checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json

from trustmesh import TrustMeshWatcher


def simple_urgency_detector(message: dict) -> list[str]:
    """A stand-in policy hook. In production, pass your own detector here
    (or the TrustMesh trust engine)."""
    text = message.get("text", "").lower()
    return ["urgency_pressure"] if ("urgent" in text or "right now" in text) else []


def main() -> None:
    watcher = TrustMeshWatcher(
        agent_id="buyer-agent-001",
        session_id="demo-session",
        policy_hook=simple_urgency_detector,
    )

    conversation = [
        {"role": "buyer", "text": "I can offer $90 per unit for 1,000 units."},
        {"role": "seller", "text": "I can do $95, delivery in 30 days."},
        {"role": "buyer", "text": "Meet me at $92 and we have a deal."},
        {"role": "seller", "text": "URGENT: accept $94 right now or I withdraw."},
        {"role": "buyer", "text": "Agreed at $93, net-30."},
    ]

    print("Signing and auditing each turn:\n")
    for msg in conversation:
        turn = watcher.audit_and_sign(msg, sender=msg["role"])
        flag = f"  [FLAG] flags={turn.flags}" if turn.is_flagged else ""
        print(f"  #{turn.sequence} {msg['role']:6} entry_hash={turn.entry_hash[:12]}...{flag}")

    ok, broken_at = watcher.verify()
    print(f"\nChain valid: {ok} (broken_at={broken_at})")

    # Now tamper with a past turn and show the chain catches it.
    entries = watcher.ledger()
    forged = json.loads(entries[2]["message_json"])
    forged["text"] = "Meet me at $50 and we have a deal."  # buyer never said this
    entries[2]["message_json"] = json.dumps(forged, sort_keys=True, separators=(",", ":"))

    from trustmesh._crypto import verify_chain

    ok_after, broken_after = verify_chain(entries)
    print(f"After forging turn #2 -> Chain valid: {ok_after} (broken_at={broken_after})")
    print("\nThe forged turn is provably detected -- that is the whole point.")


if __name__ == "__main__":
    main()
