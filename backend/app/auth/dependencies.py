import logging
from typing import Optional
from fastapi import Header, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_session_db, User
from app.auth.clerk import verify_jwt
import structlog

logger = logging.getLogger(__name__)

import os
from sqlalchemy import select

from fastapi import Request

def _system_user() -> User:
    """Return the system-level fallback user for development / screenshot mode."""
    return User(
        id="system-user-000",
        clerk_user_id="system-clerk-000",
        email="system@trustmesh.test",
        role="admin",
        org_id="system-org-000",
    )


def _auth_enforced() -> bool:
    return os.environ.get("AUTH_ENFORCED", "true").lower() == "true"


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_session_db)
) -> User:
    """
    Dependency to get the current authenticated user from Clerk JWT.
    It expects an 'Authorization: Bearer <token>' header.
    If AUTH_ENFORCED=false, falls back to a dummy system user.
    """
    if not _auth_enforced():
        user = _system_user()
        request.state.user = user
        structlog.contextvars.bind_contextvars(user_id=user.id, org_id=user.org_id)
        return user

    if not authorization:
        raise HTTPException(status_code=401, detail="Token missing")

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token missing")

    try:
        claims = verify_jwt(token)
    except Exception as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    clerk_id = claims.get("sub")
    if not clerk_id:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim")

    result = await db.execute(select(User).where(User.clerk_user_id == clerk_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    request.state.user = user
    structlog.contextvars.bind_contextvars(user_id=user.id, org_id=user.org_id)
    return user


def require_role(role: str):
    async def checker(user: User = Depends(get_current_user)):
        if user.role != role and user.role != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


async def get_current_user_ws(
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_session_db)
) -> User:
    """
    Dependency to get the current authenticated user for WebSockets via query parameter.
    """
    if not _auth_enforced():
        return _system_user()

    if not token:
        raise HTTPException(status_code=401, detail="Token missing")

    try:
        claims = verify_jwt(token)
    except Exception as e:
        logger.warning(f"JWT verification failed in WS: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    clerk_id = claims.get("sub")
    if not clerk_id:
        raise HTTPException(status_code=401, detail="Invalid token claims")

    stmt = select(User).where(User.clerk_user_id == clerk_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    structlog.contextvars.bind_contextvars(user_id=user.id, org_id=user.org_id)
    return user
