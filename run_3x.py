import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv('backend/.env')

sys.path.insert(0, os.path.abspath('backend'))
from scripts.run_manipulation_holdout import run_holdout

async def main():
    for i in range(1, 4):
        print(f"=== RUN {i} ===")
        await run_holdout()

asyncio.run(main())
