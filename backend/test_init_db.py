import asyncio
import os
from app.db import init_db

async def main():
    print("Starting init_db")
    try:
        await init_db()
        print("Finished init_db successfully")
    except Exception as e:
        print(f"Error in init_db: {e}")

if __name__ == "__main__":
    asyncio.run(main())
