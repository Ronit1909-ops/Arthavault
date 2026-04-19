"""
app/main.py – FastAPI application entry point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import connect_db, close_db
from app.utils.redis import connect_redis, close_redis
from app.routers import auth
from app.routers import statements
from app.routers import ml as ml_router
from app.routers import uploads as uploads_router
from app.services.transaction_service import ensure_transaction_indexes
from app.services.ml_service import ml_service

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

settings = get_settings()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database and Redis connections for the app's lifetime."""
    logger.info("🚀  Starting UPI Finance Tracker API …")
    await connect_db()
    await connect_redis()
    await ensure_transaction_indexes()

    # ── ML model health check ─────────────────────────────────────────────
    ml_health = ml_service.health()
    if ml_health["models_loaded"]:
        logger.info("🤖  ML models loaded successfully ✓")
    else:
        missing = [k for k, v in ml_health["models"].items() if not v]
        logger.warning("⚠   ML models partially loaded. Missing: %s", missing)

    yield
    logger.info("🛑  Shutting down …")
    await close_db()
    await close_redis()


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="UPI Finance Tracker API",
    description="Track personal UPI transactions with Google OAuth authentication.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,   # Required for cookie-based auth
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(statements.router)
app.include_router(ml_router.router)
app.include_router(uploads_router.router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": app.version}


# ── Dev entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=not settings.is_production,
        log_level="info",
    )
