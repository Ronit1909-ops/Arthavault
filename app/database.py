"""
app/database.py – MongoDB Atlas connection via Motor (async driver)
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, IndexModel
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Client (module-level singleton) ─────────────────────────────────────────
_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    """Return the Motor client (must call connect_db() first)."""
    if _client is None:
        raise RuntimeError("Database not initialised. Call connect_db() first.")
    return _client


def get_database() -> AsyncIOMotorDatabase:
    """Return the 'upi_tracker' database handle."""
    return get_client()[settings.mongo_db_name]


# ── Lifecycle helpers ────────────────────────────────────────────────────────
async def connect_db() -> None:
    """Open the Motor connection pool and create indexes."""
    global _client
    logger.info("Connecting to MongoDB Atlas …")
    _client = AsyncIOMotorClient(
        settings.mongo_uri,
        # Connection-pool settings (Motor defaults are sane; tune as needed)
        maxPoolSize=20,
        minPoolSize=2,
        serverSelectionTimeoutMS=5_000,   # fail fast on bad URI
        connectTimeoutMS=10_000,
        socketTimeoutMS=30_000,
    )
    # Ping to verify the connection is alive
    await _client.admin.command("ping")
    logger.info("MongoDB connected ✓  db=%s", settings.mongo_db_name)

    await _create_indexes()


async def close_db() -> None:
    """Close the Motor connection pool gracefully."""
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed.")


# ── Index creation ───────────────────────────────────────────────────────────
async def _create_indexes() -> None:
    """Ensure required indexes exist on startup (idempotent)."""
    db = get_database()

    users_col = db["users"]
    await users_col.create_indexes([
        IndexModel([("google_id", ASCENDING)], unique=True, name="google_id_unique"),
        IndexModel([("email", ASCENDING)],    unique=True, name="email_unique"),
    ])
    logger.info("Indexes ensured ✓")
