from fastapi import APIRouter, HTTPException, Depends
from ..db import get_agent_identity, get_all_agent_identities, User
from ..auth.dependencies import get_current_user
from ..models import AgentIdentity

router = APIRouter()


def _is_admin(user: User) -> bool:
    return user.role in ("admin", "system")


@router.get("", response_model=list[AgentIdentity], summary="List Agent Identities")
async def list_identities(current_user: User = Depends(get_current_user)):
    """List agent identities visible to the caller's org.

    Org tenancy: non-admin callers only see identities bound to their own org_id
    (plus org-less/public identities); admin/system callers see all.
    """
    identities = await get_all_agent_identities()
    if _is_admin(current_user):
        return identities
    return [
        i for i in identities
        if i.get("org_id") in (None, current_user.org_id)
    ]


@router.get("/{identity_id}", response_model=AgentIdentity, summary="Get Agent Identity")
async def get_identity(
    identity_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get an agent identity by ID, enforcing org tenancy."""
    identity = await get_agent_identity(identity_id)
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")
    if not _is_admin(current_user) and identity.get("org_id") not in (None, current_user.org_id):
        raise HTTPException(status_code=403, detail="Access denied: identity belongs to another organization")
    return identity
