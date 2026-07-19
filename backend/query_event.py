import asyncio
from app.db import init_db, get_session_db, User, Organization
from sqlalchemy import select

async def main():
    await init_db()
    async for s in get_session_db():
        org = (await s.execute(select(Organization).where(Organization.clerk_org_id == 'org_3Gf5yjZvOZEjxJ2UexWS4mmOHhh'))).scalar_one_or_none()
        if not org:
            print("Org not found")
            return
            
        print(f"ORG: id={org.id}, name={org.name}, clerk_org_id={org.clerk_org_id}")
        
        users = (await s.execute(select(User).where(User.org_id == org.id))).scalars().all()
        for u in users:
            print(f"USER: clerk_user_id={u.clerk_user_id}, email={u.email}, org_id={u.org_id}")
        break

if __name__ == '__main__':
    asyncio.run(main())
