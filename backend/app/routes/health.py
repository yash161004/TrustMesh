"""
Health-check endpoint for TrustMesh backend.

GET /health  →  200 with service metadata.
"""
from datetime import datetime, timezone
from fastapi import APIRouter

from ..config import get_settings

router = APIRouter()


@router.get("", summary="Health Check", response_description="Service status")
async def health_check() -> dict:
    """
    Returns the current health status of the TrustMesh backend.

    This endpoint is intentionally dependency-free so that infrastructure
    probes (load balancers, CI pipelines, Kubernetes liveness probes) can
    call it without triggering database or LLM connections.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "service": "TrustMesh Backend",
        "phase": settings.current_phase,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.app_version,
    }
