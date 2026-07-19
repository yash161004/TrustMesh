import asyncio
from app.db import init_db, get_session_db, User, Organization
from sqlalchemy import select

async def main():
    await init_db()
    async for session in get_session_db():
        res = await session.execute(
            select(User, Organization)
            .outerjoin(Organization, User.org_id == Organization.id)
            .where(User.org_id.is_not(None))
        )
        rows = res.all()
        print(f"Found {len(rows)} users with an org_id.")
        for u, o in rows:
            print(f"USER: clerk_id={u.clerk_user_id}, org_id={u.org_id}, email={u.email}")
            if o:
                print(f"ORG: id={o.id}, name={o.name}")
        break

if __name__ == '__main__':
    asyncio.run(main())
