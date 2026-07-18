import asyncio
import httpx
from app.auth.clerk import create_test_token

async def main():
    base_url = "http://127.0.0.1:8000/api/v1"
    
    # 1. Test unauthenticated access to newly gated routes
    print("Testing unauthenticated access...")
    async with httpx.AsyncClient() as client:
        # We need a fake session ID for the URL, it will fail auth before checking DB
        fake_id = "12345678-1234-5678-1234-567812345678"
        r1 = await client.get(f"{base_url}/sessions/{fake_id}/trust")
        print(f"GET /trust without auth -> Status: {r1.status_code}")
        
        r2 = await client.get(f"{base_url}/sessions/{fake_id}/ledger")
        print(f"GET /ledger without auth -> Status: {r2.status_code}")

    # 2. Test Org-Shared Visibility
    print("\nTesting Org-Shared Visibility...")
    # Tokens for users in same org
    token_a = create_test_token(user_id="user_a", org_id="org_1", role="standard")
    token_b = create_test_token(user_id="user_b", org_id="org_1", role="standard")
    # Token for user in different org
    token_c = create_test_token(user_id="user_c", org_id="org_2", role="standard")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    headers_c = {"Authorization": f"Bearer {token_c}"}

    async with httpx.AsyncClient() as client:
        # Create session as User A
        r_create = await client.post(
            f"{base_url}/sessions",
            json={"buyer_agent_id": "b1", "seller_agent_id": "s1"},
            headers=headers_a
        )
        if r_create.status_code != 200:
            print(f"Failed to create session: {r_create.text}")
            return
            
        session_id = r_create.json()["session_id"]
        print(f"User A created session: {session_id}")

        # User A fetches their own session
        r_a = await client.get(f"{base_url}/sessions/{session_id}", headers=headers_a)
        print(f"User A GET session -> Status: {r_a.status_code}")

        # User B (same org) fetches session
        r_b = await client.get(f"{base_url}/sessions/{session_id}", headers=headers_b)
        print(f"User B (same org) GET session -> Status: {r_b.status_code}")

        # User C (different org) fetches session
        r_c = await client.get(f"{base_url}/sessions/{session_id}", headers=headers_c)
        print(f"User C (diff org) GET session -> Status: {r_c.status_code}")

if __name__ == "__main__":
    asyncio.run(main())
