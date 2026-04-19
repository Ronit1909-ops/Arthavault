"""
app/utils/redis.py – Redis DISABLED.
All session helpers are no-ops. Auth works via JWT HttpOnly cookie only.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def connect_redis() -> None:
    logger.info("Redis disabled – using JWT cookie auth only.")


async def close_redis() -> None:
    pass


async def set_session(session_id: str, data: dict[str, Any]) -> None:
    pass


async def get_session(session_id: str) -> dict[str, Any] | None:
    return None


async def delete_session(session_id: str) -> None:
    pass


async def refresh_session(session_id: str) -> None:
    pass
