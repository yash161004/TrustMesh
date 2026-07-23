import asyncio
import json
import os
import sys
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from app.db import init_db, get_session_factory, SessionRecord, MessageRecord

async def run():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        # Check sample messages from data_source = 'real'
        res = await db.execute(text(
            "SELECT s.id, s.status, s.outcome, s.created_at, s.buyer_agent_id, m.sender, m.notes, m.message_type "
            "FROM negotiation_sessions s "
            "LEFT JOIN negotiation_messages m ON s.id = m.session_id "
            "WHERE s.data_source = 'real' AND s.status = 'COMPLETED' "
            "LIMIT 20;"
        ))
        rows = res.all()
        print("SAMPLE MESSAGES FROM data_source='real' COMPLETED SESSIONS:")
        for r in rows[:10]:
            print(f"Session {r[0][:8]} | status={r[1]} | outcome={r[2]} | buyer={r[4]} | sender={r[5]} | notes={r[6]}")

        # Check total count of sessions with mock-like notes or agent IDs
        res_mock = await db.execute(text(
            "SELECT count(DISTINCT s.id) "
            "FROM negotiation_sessions s "
            "JOIN negotiation_messages m ON s.id = m.session_id "
            "WHERE s.data_source = 'real' AND (m.notes LIKE '%Mock%' OR s.buyer_agent_id LIKE '%mock%' OR s.buyer_agent_id LIKE '%buyer-agent-001%');"
        ))
        mock_count = res_mock.scalar()
        print(f"\nSessions with data_source='real' that use mock agent IDs or mock notes: {mock_count}")

if __name__ == "__main__":
    asyncio.run(run())
