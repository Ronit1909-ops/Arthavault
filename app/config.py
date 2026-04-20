"""
app/config.py – Pydantic Settings loaded from .env
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── MongoDB ──────────────────────────────────────────────────────────
    mongo_uri: str
    mongo_db_name: str = "upi_tracker"

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"

    # ── Google OAuth ─────────────────────────────────────────────────────
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "https://arthavault.onrender.com/auth/callback"

    # ── JWT ──────────────────────────────────────────────────────────────
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 86400  # 24 h

    # ── App ──────────────────────────────────────────────────────────────
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    frontend_url: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()
