"""
app/routers/auth.py – Google OAuth 2.0 routes + protected /me endpoint

Flow:
  GET  /auth/login      → Redirect to Google consent screen
  GET  /auth/callback   → Exchange code → JWT → set HttpOnly cookie → redirect frontend
  GET  /auth/me         → Return current user (JWT cookie required)
  POST /auth/logout     → Expire cookie
"""
import secrets
import logging
from typing import Annotated

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.models.user import UserResponse
from app.services.auth_service import get_or_create_user, get_user_by_id
from app.utils.jwt import create_access_token, decode_access_token

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPES    = "openid email profile"


def _make_oauth_client() -> AsyncOAuth2Client:
    return AsyncOAuth2Client(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
        scope=GOOGLE_SCOPES,
    )


# ── Dependency: extract current user from JWT cookie ─────────────────────────
async def get_current_user(
    request: Request,
    access_token: Annotated[str | None, Cookie()] = None,
) -> UserResponse:
    """
    Validates the JWT from:
      1. Authorization: Bearer <token>  header, OR
      2. `access_token` HttpOnly cookie (set after OAuth callback)

    Redis session check removed — JWT is the single source of truth.
    """
    token: str | None = None

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)   # raises 401 if expired / invalid
    user_id = payload.get("sub")

    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )
    return user


# ── Routes ────────────────────────────────────────────────────────────────────
@router.get("/login", summary="Redirect to Google OAuth consent screen")
async def login(request: Request):
    state = secrets.token_urlsafe(32)

    async with _make_oauth_client() as client:
        auth_url, _ = client.create_authorization_url(
            GOOGLE_AUTH_URL,
            state=state,
            access_type="offline",
            prompt="select_account",
        )

    redir = RedirectResponse(url=auth_url, status_code=302)
    redir.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        max_age=300,
        samesite="lax",
    )
    return redir


@router.get("/callback", summary="Google OAuth callback – issues JWT")
async def callback(
    request: Request,
    code: str,
    state: str,
    oauth_state: Annotated[str | None, Cookie()] = None,
):
    # CSRF state check
    if not oauth_state or oauth_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state. Possible CSRF attack.",
        )

    async with _make_oauth_client() as client:
        try:
            await client.fetch_token(
                GOOGLE_TOKEN_URL,
                code=code,
                redirect_uri=settings.google_redirect_uri,
            )
        except Exception as exc:
            logger.error("Token exchange failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorisation code.",
            )

        resp = await client.get(GOOGLE_USERINFO)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch Google user profile.",
            )
        google_profile = resp.json()

    user = await get_or_create_user(google_profile)

    jwt_token = create_access_token(
        user_id=user.id,
        extra={"email": user.email, "name": user.name},
    )

    # Redirect to React frontend /auth/callback — it will call /auth/me to restore session
    frontend_callback = f"{settings.frontend_url}/auth/callback"
    response = RedirectResponse(url=frontend_callback, status_code=302)
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        max_age=settings.jwt_expire_seconds,
        samesite="lax",
        secure=settings.is_production,
    )
    response.delete_cookie("oauth_state")
    return response


@router.get("/me", response_model=UserResponse, summary="Get the currently authenticated user")
async def me(current_user: Annotated[UserResponse, Depends(get_current_user)]):
    return current_user


@router.post("/logout", summary="Invalidate session and clear cookie")
async def logout(
    response: Response,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    response.delete_cookie("access_token")
    return {"detail": "Logged out successfully."}
