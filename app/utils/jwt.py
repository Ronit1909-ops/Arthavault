"""
app/utils/jwt.py – JWT token generation & validation using PyJWT
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, status
from app.config import get_settings

settings = get_settings()

# ── Constants ────────────────────────────────────────────────────────────────
_ALGORITHM = settings.jwt_algorithm
_SECRET    = settings.jwt_secret
_EXPIRE_S  = settings.jwt_expire_seconds


# ── Public helpers ───────────────────────────────────────────────────────────
def create_access_token(user_id: str, extra: dict[str, Any] | None = None) -> str:
    """
    Create a signed JWT.

    Payload:
        sub  – user's MongoDB ObjectId (as string)
        iat  – issued-at UTC timestamp
        exp  – expiry UTC timestamp (now + JWT_EXPIRE_SECONDS)
        ...  – any extra claims (e.g. email, name)
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=_EXPIRE_S),
    }
    if extra:
        payload.update(extra)

    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT.

    Raises HTTPException(401) if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def extract_user_id(token: str) -> str:
    """Convenience wrapper – returns the `sub` claim as a string."""
    payload = decode_access_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing subject claim.",
        )
    return str(sub)
