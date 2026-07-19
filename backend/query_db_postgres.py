import asyncio
from app.db import init_db, get_session_db, User, Organization
from sqlalchemy import select

async def main():
    await init_db()
    async for session in get_session_db():
        print(f"URL: {session.bind.engine.url}")
        res = await session.execute(
            select(User, Organization)
            .outerjoin(Organization, User.org_id == Organization.id)
            .order_by(User.created_at.desc())
            .limit(1)
        )
        row = res.first()
        if row:
            u, o = row
            updated_at = getattr(u, 'updated_at', None)
            if not updated_at:
                updated_at = u.created_at
            print(f"USER: clerk_user_id={u.clerk_user_id}, org_id={u.org_id}, email={u.email}, updated_at={updated_at}")
            if o:
                print(f"ORG: id={o.id}, name={o.name}")
            else:
                print("ORG: None")
        break

if __name__ == '__main__':
    asyncio.run(main())
