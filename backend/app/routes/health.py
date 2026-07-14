"""
Health-check endpoint for TrustMesh backend.

GET /health  →  200 with service metadata.
"""
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter()


@router.get("", summary="Health Check", response_description="Service status")
async def health_check() -> dict:
    """
    Returns the current health status of the TrustMesh backend.

    This endpoint is intentionally dependency-free so that infrastructure
    probes (load balancers, CI pipelines, Kubernetes liveness probes) can
    call it without triggering database or LLM connections.
    """
    return {
        "status": "ok",
        "service": "TrustMesh Backend",
        "phase": "0 — Foundation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0",
    }
