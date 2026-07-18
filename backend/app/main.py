"""
TrustMesh FastAPI Application Factory — Phase 1: Agent Logic

Creates and configures the FastAPI app instance with:
- CORS middleware (allows the Vite dev server on :5173)
- API router mounting
- OpenAPI / Swagger docs customisation
- Database initialisation on startup
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import close_db, init_db
from .router import api_router
from .logging_config import setup_logging

setup_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup: initialise the database
    import sys; sys.stderr.write('Lifespan: before init_db\n'); sys.stderr.flush(); await init_db(); sys.stderr.write('Lifespan: after init_db\n'); sys.stderr.flush()
    yield
    # Shutdown: close the database
    await close_db()


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
        version="0.2.0",
        contact={
            "name": "TrustMesh Dev",
            "url": "https://github.com/your-org/trustmesh",
        },
        license_info={"name": "MIT"},
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    import uuid
    import structlog
    from fastapi.responses import JSONResponse
    from fastapi import Request
    from .limiter import limiter

    async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
        response = JSONResponse(
            {"detail": f"Rate limit exceeded: {exc.detail}"}, status_code=429
        )
        # Always add a retry-after header (dummy 60s if not extractable)
        response.headers["Retry-After"] = "60"
        return response

    logger = structlog.get_logger("api.access")

    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        structlog.contextvars.clear_contextvars()
        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        response = await call_next(request)
        
        user = getattr(request.state, "user", None)
        if user:
            structlog.contextvars.bind_contextvars(user_id=user.id, org_id=user.org_id)
        
        # Log the request details with structlog so the contextvars are attached
        logger.info(
            "Request processed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )
        return response

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

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
