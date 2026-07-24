from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
import json

from ..identity.agent_card import verify_agent_card, CARDS_DIR, card_file_path
from ..auth.dependencies import get_current_user
from ..db import get_agent_reputation, User
from pydantic import BaseModel

router = APIRouter()

class AgentCardResponse(BaseModel):
    agent_id: str
    role: str
    display_name: str
    capabilities: list[str]
    public_key: str
    created_at: str
    version: str
    is_verified: bool
    signature: str


class AgentReputationResponse(BaseModel):
    agent_id: str
    trust_score: float
    total_sessions: int
    violations_count: int
    last_updated: datetime


@router.get("", response_model=list[AgentCardResponse], summary="List Agent Cards")
async def list_agent_cards():
    """List all AgentCards from disk and verify their signatures."""
    cards = []
    if not CARDS_DIR.exists():
        return cards

    for path in CARDS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            card_data = data.get("card", {})
            signature = data.get("signature", "")
            
            is_valid = verify_agent_card(path)
            
            cards.append(AgentCardResponse(
                agent_id=card_data.get("agent_id", ""),
                role=card_data.get("role", ""),
                display_name=card_data.get("display_name", ""),
                capabilities=card_data.get("capabilities", []),
                public_key=card_data.get("public_key", ""),
                created_at=card_data.get("created_at", ""),
                version=card_data.get("version", ""),
                is_verified=is_valid,
                signature=signature
            ))
        except Exception:
            pass

    return cards


@router.get("/{agent_id}/reputation", response_model=AgentReputationResponse, summary="Get Agent Reputation")
async def get_agent_reputation_route(
    agent_id: str,
    current_user: User = Depends(get_current_user),
):
    """Fetch cross-session reputation for a specific agent with org tenancy enforcement."""
    path = card_file_path(agent_id, current_user.org_id)
    if not path.exists():
        path = card_file_path(agent_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Agent card not found")

    try:
        data = json.loads(path.read_text())
        card_data = data.get("card", {})
        card_org_id = card_data.get("org_id")
        
        # Org tenancy check: non-admin users cannot access agents belonging to other orgs
        is_admin = current_user.role in ("admin", "system")
        if card_org_id and not is_admin and current_user.org_id != card_org_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: agent belongs to another organization"
            )
    except HTTPException:
        raise
    except Exception:
        pass

    rep = await get_agent_reputation(agent_id)
    return AgentReputationResponse(
        agent_id=rep["agent_id"],
        trust_score=rep["trust_score"],
        total_sessions=rep["total_sessions"],
        violations_count=rep["violations_count"],
        last_updated=rep["last_updated"],
    )
