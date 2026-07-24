"""
TrustMesh API Routers — Phase 1: Agent Logic

Registers all route groups. New phases will add their own routers here.
"""
from fastapi import APIRouter
from .routes import health, sessions, identities, webhooks, admin, metrics, agent_cards, fleet_anomaly

api_router = APIRouter()

# Phase 1: Infrastructure / health + negotiation sessions
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(identities.router, prefix="/identities", tags=["Identities"])
api_router.include_router(agent_cards.router, prefix="/agent-cards", tags=["AgentCards"])
api_router.include_router(agent_cards.router, prefix="/agents", tags=["Agents"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(admin.router, tags=["Admin"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])
api_router.include_router(fleet_anomaly.router, prefix="/fleet", tags=["Fleet"])

# Phase 2+: Trust engine, ledger
# api_router.include_router(trust.router,    prefix="/trust",    tags=["Trust"])
# api_router.include_router(ledger.router,   prefix="/ledger",   tags=["Ledger"])
