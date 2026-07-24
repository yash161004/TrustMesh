import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.llm_client import get_llm_client

async def main():
    print("Testing Groq...")
    client = get_llm_client("groq")
    try:
        res = await client.generate([{"role": "user", "content": "say hello"}])
        print(f"Groq response: {repr(res)}")
    except Exception as e:
        print(f"Groq exception: {e}")

    print("Testing Gemini...")
    client = get_llm_client("gemini")
    try:
        res = await client.generate([{"role": "user", "content": "say hello"}])
        print(f"Gemini response: {repr(res)}")
    except Exception as e:
        print(f"Gemini exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
