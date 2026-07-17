from fastapi import APIRouter, HTTPException
from ..db import get_agent_identity, get_all_agent_identities
from ..models import AgentIdentity

router = APIRouter()

@router.get("", response_model=list[AgentIdentity], summary="List Agent Identities")
async def list_identities():
    """List all agent identities."""
    identities = await get_all_agent_identities()
    return identities

@router.get("/{identity_id}", response_model=AgentIdentity, summary="Get Agent Identity")
async def get_identity(identity_id: str):
    """Get an agent identity by ID."""
    identity = await get_agent_identity(identity_id)
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")
    return identity
