import asyncio
from dotenv import load_dotenv
load_dotenv()
from app.db import init_db
import sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    print("Starting init_db with Postgres")
    try:
        await init_db()
        print("Finished init_db successfully")
    except Exception as e:
        print("Exception in init_db:", e)

if __name__ == "__main__":
    asyncio.run(main())
