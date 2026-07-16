"""
TrustMesh AgentCard Generator

Reads every row from the agent_identities table and generates a
cryptographically signed ERC-8004-style AgentCard for each one, using
the identity's own .id as the card's agent_id.

Usage:
    cd backend
    python scripts/generate_agent_cards.py
"""
from __future__ import annotations

import sys
import os
import asyncio
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import init_db, close_db, get_all_agent_identities
from app.identity.agent_card import (
    generate_agent_card,
    verify_agent_card,
    card_file_path,
    CARDS_DIR,
)


async def main() -> int:
    await init_db()

    identities = await get_all_agent_identities()

    print("=" * 52)
    print(f"  AgentCard Generator — {len(identities)} identity(ies) found")
    print("=" * 52)

    generated = []
    for ident in identities:
        iid = ident["id"]
        role = ident["role"].lower()
        name = ident["name"]
        print(f"\n  Generating card for: {iid}")
        card, sig = generate_agent_card(
            role=role,
            agent_id=iid,
            display_name=name,
        )
        path = card_file_path(card.agent_id)
        generated.append((iid, role, path))
        print(f"    agent_id   : {card.agent_id}")
        print(f"    display    : {card.display_name}")
        print(f"    role       : {card.role}")
        print(f"    capabilities: {len(card.capabilities)} entries")
        print(f"    version    : {card.version}")
        print(f"    path       : {path}")
        print(f"    signature  : {sig[:32]}...")

    # ── Verify every card ─────────────────────────────────────────────
    print("\n" + "=" * 52)
    print("  Self-verification")
    print("=" * 52)

    all_ok = True
    for iid, role, path in generated:
        result = verify_agent_card(path)
        status = "PASS" if result else "FAIL"
        if not result:
            all_ok = False
        print(f"  {role:>8s} ({iid}) -> {status}")

    print()
    if all_ok:
        print(f"  All {len(generated)} AgentCards generated and verified successfully.")
        print(f"  Cards stored in: {CARDS_DIR}")
    else:
        print("  Some verifications FAILED.")
        await close_db()
        return 1

    print("=" * 52)

    await close_db()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
