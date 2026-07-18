import asyncio
import aiohttp

API_BASE = "http://127.0.0.1:8001/api/v1"

async def main():
    async with aiohttp.ClientSession() as session:
        # Get all sessions
        print("Fetching all sessions...")
        async with session.get(f"{API_BASE}/sessions") as resp:
            resp.raise_for_status()
            sessions = await resp.json()
            
        print(f"Found {len(sessions)} total sessions.")
        
        valid_count = 0
        invalid_count = 0
        invalid_ids = []
        
        # Check ledger for each session
        for idx, s in enumerate(sessions):
            sess_id = s["session_id"]
            async with session.get(f"{API_BASE}/sessions/{sess_id}/ledger") as resp:
                resp.raise_for_status()
                data = await resp.json()
                if data.get("chain_valid", False):
                    valid_count += 1
                else:
                    invalid_count += 1
                    invalid_ids.append(sess_id)
                    
            if (idx + 1) % 100 == 0:
                print(f"Checked {idx + 1}/{len(sessions)}...")
                
        print("\n--- RESULTS ---")
        print(f"Total Checked: {len(sessions)}")
        print(f"Valid: {valid_count}")
        print(f"Invalid: {invalid_count}")
        if invalid_count > 0:
            print("Invalid Session IDs:")
            for i in invalid_ids:
                print(f"  - {i}")

if __name__ == "__main__":
    asyncio.run(main())
