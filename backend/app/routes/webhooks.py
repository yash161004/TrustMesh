import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from svix.webhooks import Webhook, WebhookVerificationError
from app.db import get_session_db, User, Organization
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/clerk")
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_session_db)):
    settings = get_settings()
    secret = settings.clerk_webhook_secret

    if not secret:
        raise HTTPException(status_code=500, detail="CLERK_WEBHOOK_SECRET not configured")

    headers = dict(request.headers)
    payload = await request.body()
    
    # Verify the signature
    try:
        wh = Webhook(secret)
        evt = wh.verify(payload, headers)
    except WebhookVerificationError as e:
        logger.warning(f"Invalid webhook signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error verifying webhook: {e}")
        raise HTTPException(status_code=400, detail="Webhook error")
    
    evt_type = evt.get("type")
    data = evt.get("data", {})

    if evt_type == "user.created":
        clerk_id = data.get("id")
        email_addresses = data.get("email_addresses", [])
        email = email_addresses[0].get("email_address") if email_addresses else ""
        
        # Upsert User
        result = await db.execute(select(User).where(User.clerk_user_id == clerk_id))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                clerk_user_id=clerk_id,
                email=email,
                role="standard"
            )
            db.add(user)
        else:
            user.email = email
            
        await db.commit()
        logger.info(f"Handled user.created for {clerk_id}")

    elif evt_type in ("organization.created", "organization.membership.created"):
        org_data = data.get("organization", data) if evt_type == "organization.membership.created" else data
        clerk_org_id = org_data.get("id")
        name = org_data.get("name", "")
        
        # Upsert Organization
        result = await db.execute(select(Organization).where(Organization.clerk_org_id == clerk_org_id))
        org = result.scalar_one_or_none()
        
        if not org:
            org = Organization(
                clerk_org_id=clerk_org_id,
                name=name,
                plan_tier="free"
            )
            db.add(org)
            await db.flush() # To get the UUID
        else:
            org.name = name

        # If it's a membership event, also update the user
        if evt_type == "organization.membership.created":
            public_user_data = data.get("public_user_data", {})
            clerk_user_id = public_user_data.get("user_id")
            if clerk_user_id:
                user_result = await db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
                user = user_result.scalar_one_or_none()
                if user:
                    user.org_id = org.id
                    if data.get("role") == "org:admin":
                        user.role = "admin"
                    
        await db.commit()
        logger.info(f"Handled {evt_type} for org {clerk_org_id}")

    return {"success": True}
