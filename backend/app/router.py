"""
TrustMesh API Routers — Phase 1: Agent Logic

Registers all route groups. New phases will add their own routers here.
"""
from fastapi import APIRouter
from .routes import health, sessions, identities

api_router = APIRouter()

# Phase 1: Infrastructure / health + negotiation sessions
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(identities.router, prefix="/identities", tags=["Identities"])

# Phase 2+: Trust engine, ledger
# api_router.include_router(trust.router,    prefix="/trust",    tags=["Trust"])
# api_router.include_router(ledger.router,   prefix="/ledger",   tags=["Ledger"])
