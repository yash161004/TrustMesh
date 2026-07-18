import sys
import asyncio
from sqlalchemy import select
from app.db import get_session_factory, User
from app.auth.clerk import verify_jwt

async def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_real_token.py <token>")
        sys.exit(1)
        
    token = sys.argv[1]
    
    print(f"Verifying token: {token[:10]}...{token[-10:] if len(token) > 20 else ''}")
    
    try:
        claims = verify_jwt(token)
        print("\nToken is valid!")
        print(f"Claims parsed successfully.")
        print(f"Subject (Clerk User ID): {claims.get('sub')}")
    except Exception as e:
        print(f"\nFailed to verify JWT: {e}")
        sys.exit(1)
        
    clerk_id = claims.get("sub")
    
    print("\nLooking up user in local database...")
    from app.db import init_db
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(select(User).where(User.clerk_user_id == clerk_id))
        user = result.scalar_one_or_none()
        
        if user:
            print("User found!")
            print(f"- Internal ID: {user.id}")
            print(f"- Email: {user.email}")
            print(f"- Role: {user.role}")
            print(f"- Org ID: {user.org_id}")
        else:
            print("User NOT found in local database.")
            print("This means the user exists in Clerk but the webhook hasn't successfully created them here yet.")

if __name__ == "__main__":
    asyncio.run(main())
