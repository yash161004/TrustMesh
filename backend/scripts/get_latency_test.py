import asyncio
import aiohttp
import time
import json

API_BASE = "http://127.0.0.1:8001/api/v1"

async def test_get_latency():
    print("Testing GET /sessions latency...")
    async with aiohttp.ClientSession() as session:
        latencies = []
        for _ in range(50):
            start = time.time()
            async with session.get(f"{API_BASE}/sessions") as response:
                await response.json()
            latencies.append(time.time() - start)
            
        lat_count = len(latencies)
        latencies.sort()
        print(f"Total GET Requests: {lat_count}")
        print(f"  Min: {latencies[0]:.3f}s")
        print(f"  Avg: {sum(latencies)/lat_count:.3f}s")
        print(f"  P95: {latencies[int(lat_count*0.95)]:.3f}s")
        print(f"  Max: {latencies[-1]:.3f}s")

if __name__ == "__main__":
    asyncio.run(test_get_latency())
