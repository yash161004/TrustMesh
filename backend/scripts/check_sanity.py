import asyncio
from sqlalchemy import select, func, text
from app.db import init_db, get_session_factory, User, TrustReportRecord

async def main():
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        # Check org_id for the admin user
        user = await db.execute(select(User).where(User.id == '9e8733b7-bd06-4857-bcd4-26816989d6b8'))
        admin_user = user.scalar_one_or_none()
        if admin_user:
            print(f"Admin User org_id in DB: {admin_user.org_id}")
        else:
            print("Admin user not found in DB.")

        # Check total number of trust_reports
        count_result = await db.execute(select(func.count(TrustReportRecord.id)))
        total_reports = count_result.scalar()
        print(f"Total rows in trust_reports: {total_reports}")

if __name__ == "__main__":
    asyncio.run(main())
