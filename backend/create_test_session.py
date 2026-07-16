import asyncio
from app.session_manager import session_manager
from app.db import init_db

async def main():
    await init_db()
    session = await session_manager.create_session(provider="mock")
    print("Created session:", session.session_id)
    await session_manager.start_session(session.session_id)
    print("Started session.")
    await session_manager.process_turn(session.session_id, max_turns=5)
    print("Processed turns.")

if __name__ == "__main__":
    asyncio.run(main())
