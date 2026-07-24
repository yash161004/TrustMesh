"""AutoGen Adapter Example: Audit agent-to-agent message exchanges.

Run from the repo root:

    python sdk/examples/autogen_adapter_demo.py

Demonstrates how TrustMeshAutoGenHandler hooks into AutoGen message pipelines,
signing each exchanged message and verifying the conversation transcript.
"""
import sys
from pathlib import Path

# Make `trustmesh` importable when run directly from a checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trustmesh import TrustMeshWatcher

try:
    from trustmesh.adapters.autogen import TrustMeshAutoGenHandler
except ImportError as err:
    print(f"Notice: {err}")
    print("This example demonstrates AutoGen integration when `autogen-agentchat` is installed (`pip install 'trustmesh-sdk[autogen]'`).")
    sys.exit(0)


def main() -> None:
    watcher = TrustMeshWatcher(agent_id="autogen-team", session_id="autogen-demo-01")
    handler = TrustMeshAutoGenHandler(watcher)

    simulated_messages = [
        {
            "role": "user",
            "name": "BuyerAgent",
            "content": "Requesting quote for 200 industrial display units",
        },
        {
            "role": "assistant",
            "name": "SellerAgent",
            "content": "Initial price quote $180/unit with 14-day delivery",
        },
        {
            "role": "user",
            "name": "BuyerAgent",
            "content": "URGENT: Can you match $165 if we order 300 units today?",
        },
        {
            "role": "assistant",
            "name": "SellerAgent",
            "content": "Agreed at $168/unit for 300 units",
        },
    ]

    print("Auditing AutoGen agent messages:")
    for msg in simulated_messages:
        handler.on_message(msg, sender=msg["name"])
        turn = handler.turns[-1]
        print(f"  [MSG] turn={turn.sequence} sender={msg['name']:12} hash={turn.entry_hash[:12]}...")

    ok, broken_at = handler.verify()
    print(f"\nLedger Verification Result: chain_valid={ok} (broken_at={broken_at})")
    print("Conversation history is tamper-evident and cryptographically signed.")


if __name__ == "__main__":
    main()
