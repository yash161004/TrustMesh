import asyncio
import json
import sys
from pathlib import Path

# Add backend dir to path so imports work
sys.path.append(str(Path(__file__).parent.parent))

from app.db import init_db
from app.identity.agent_card import (
    generate_agent_card,
    verify_agent_card,
    card_file_path,
)

async def main():
    print("=== AgentCard Verification Test ===")
    
    print("\n1. Initialising DB to ensure demo agents exist...")
    await init_db()
    
    agent_id = "demo-seller-good"
    role = "seller"
    
    print(f"\n2. Generating AgentCard for {agent_id} ({role})...")
    card, sig = generate_agent_card(role=role, agent_id=agent_id)
    
    path = card_file_path(agent_id)
    print(f"Card written to {path}")
    
    print("\n3. Verifying valid AgentCard...")
    is_valid = verify_agent_card(path)
    if is_valid:
        print("[SUCCESS] Valid card verified successfully.")
    else:
        print("[FAIL] Valid card failed verification.")
        
    print("\n4. Tampering with AgentCard...")
    data = json.loads(path.read_text())
    
    # Tamper with the role
    original_role = data["card"]["role"]
    tampered_role = "admin"
    print(f"Tampering: Changing role from {original_role} to {tampered_role}")
    data["card"]["role"] = tampered_role
    
    path.write_text(json.dumps(data, indent=2))
    
    print("\n5. Verifying tampered AgentCard...")
    is_valid_tampered = verify_agent_card(path)
    if not is_valid_tampered:
        print("[SUCCESS] Tampered card correctly failed verification.")
    else:
        print("[FAIL] Tampered card was mistakenly verified as valid.")

if __name__ == "__main__":
    asyncio.run(main())
