from fastapi import APIRouter
from pathlib import Path
import json

from ..identity.agent_card import verify_agent_card, CARDS_DIR
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
