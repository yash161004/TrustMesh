import asyncio
from app.db import init_db, get_session_db, User
from sqlalchemy import select

async def main():
    await init_db()
    async for session in get_session_db():
        res = await session.execute(select(User).order_by(User.created_at.desc()).limit(1))
        u = res.scalar_one_or_none()
        if u:
            print(f'USER: {u.email} | ORG_ID: {u.org_id} | CREATED_AT: {u.created_at}')
        else:
            print('No users found.')
        break

if __name__ == '__main__':
    asyncio.run(main())
