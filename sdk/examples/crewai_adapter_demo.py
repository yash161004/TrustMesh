"""CrewAI Adapter Example: Audit agent steps and task completions.

Run from the repo root:

    python sdk/examples/crewai_adapter_demo.py

Demonstrates how TrustMeshCrewCallback hooks into agent steps and task outputs,
signing each turn and verifying chain integrity.
"""
import sys
from pathlib import Path

# Make `trustmesh` importable when run directly from a checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trustmesh import TrustMeshWatcher

try:
    from trustmesh.adapters.crewai import TrustMeshCrewCallback
except ImportError as err:
    print(f"Notice: {err}")
    print("This example demonstrates CrewAI integration when `crewai` is installed (`pip install 'trustmesh-sdk[crewai]'`).")
    sys.exit(0)


def main() -> None:
    watcher = TrustMeshWatcher(agent_id="procurement-buyer", session_id="crewai-demo-01")
    handler = TrustMeshCrewCallback(watcher)

    # Simulated CrewAI agent steps and task outputs
    simulated_steps = [
        {
            "agent": "buyer-agent",
            "output": "Analyzing market reference price for memory chips",
            "action": "lookup_market_price",
            "tool_input": {"sku": "MEM-16G", "qty": 500},
            "thought": "Supplier asking price is $45, target is $38",
        },
        {
            "agent": "buyer-agent",
            "output": "Proposing counter-offer at $40/unit with Net-30 terms",
            "action": "propose_offer",
            "tool_input": {"price": 40, "delivery": "Net-30"},
        },
    ]

    simulated_task_finish = {
        "task_description": "Negotiate 500 memory chip units",
        "raw_output": "Deal closed at $41.50/unit, total $20,750",
        "agent": "buyer-agent",
        "summary": "Successful negotiation within budget cap",
    }

    print("Auditing CrewAI agent steps:")
    for step in simulated_steps:
        handler.on_step(step)
        turn = handler.turns[-1]
        print(f"  [STEP] turn={turn.sequence} hash={turn.entry_hash[:12]}... tool={step['action']}")

    print("\nAuditing CrewAI task completion:")
    handler.on_task_finish(simulated_task_finish)
    task_turn = handler.turns[-1]
    print(f"  [TASK] turn={task_turn.sequence} hash={task_turn.entry_hash[:12]}... summary='{simulated_task_finish['summary']}'")

    ok, broken_at = handler.verify()
    print(f"\nLedger Verification Result: chain_valid={ok} (broken_at={broken_at})")
    print("All agent steps and task outputs are cryptographically bound to the Ed25519 hash chain.")


if __name__ == "__main__":
    main()
