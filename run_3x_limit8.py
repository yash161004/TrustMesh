import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv('backend/.env')

sys.path.insert(0, os.path.abspath('backend'))
from scripts.run_manipulation_holdout import run_holdout

# Override sys.argv for the parser in run_holdout
sys.argv = ['run_holdout.py', '--limit', '8', '--prompt-version', 'post-few-shot-expansion-swap']

async def main():
    for i in range(1, 4):
        print(f"=== RUN {i} ===")
        await run_holdout()

asyncio.run(main())
