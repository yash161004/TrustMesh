"""
TrustMesh FastAPI Application Factory — Phase 0: Foundation

Creates and configures the FastAPI app instance with:
- CORS middleware (allows the Vite dev server on :5173)
- API router mounting
- OpenAPI / Swagger docs customisation
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .router import api_router

settings = get_settings()


def create_app() -> FastAPI:
    """Application factory — returns a fully configured FastAPI instance."""
    app = FastAPI(
        title="TrustMesh",
        summary="Verification and anti-manipulation trust layer for AI-to-AI negotiation.",
        description=(
            "TrustMesh sits between two LLM negotiating agents (Buyer & Seller), "
            "checks for manipulation and policy violations, and records every "
            "exchange on a tamper-evident cryptographic ledger."
        ),
        version="0.1.0",
        contact={
            "name": "TrustMesh Dev",
            "url": "https://github.com/your-org/trustmesh",
        },
        license_info={"name": "MIT"},
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    app.include_router(api_router, prefix="/api/v1")

    # ------------------------------------------------------------------
    # Root redirect
    # ------------------------------------------------------------------
    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "message": "TrustMesh API is running. Visit /docs for interactive documentation.",
            "health": "/api/v1/health",
            "docs": "/docs",
        }

    return app


app = create_app()
