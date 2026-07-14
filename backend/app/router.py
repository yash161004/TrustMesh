"""
TrustMesh API Routers — Phase 0

Registers all route groups. New phases will add their own routers here.
"""
from fastapi import APIRouter
from .routes import health

api_router = APIRouter()

# Phase 0: Infrastructure / health
api_router.include_router(health.router, prefix="/health", tags=["Health"])

# Phase 1+: Negotiation sessions, agents, trust engine, ledger
# api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
# api_router.include_router(trust.router,    prefix="/trust",    tags=["Trust"])
# api_router.include_router(ledger.router,   prefix="/ledger",   tags=["Ledger"])
