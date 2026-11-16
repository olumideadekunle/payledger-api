import os
from functools import lru_cache
from typing import List
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET = "supersecretjwtkeyforlocaldevelopmentpayledger123456"


def normalize_database_url(url: str) -> str:
    """
    Convert provider URLs (Vercel Postgres / Neon / Supabase / Heroku style
    `postgres://...?sslmode=require`) into an asyncpg-compatible SQLAlchemy URL.
    asyncpg does not understand libpq params like `sslmode` / `channel_binding`.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    if not url.startswith("postgresql+asyncpg://"):
        return url

    parts = urlsplit(url)
    params = dict(parse_qsl(parts.query))
    sslmode = params.pop("sslmode", None)
    params.pop("channel_binding", None)
    if sslmode and sslmode != "disable" and "ssl" not in params:
        params["ssl"] = "require"
    return urlunsplit(parts._replace(query=urlencode(params)))


class Settings(BaseSettings):
    PROJECT_NAME: str = "PayLedger API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = _DEV_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: List[str] = ["*"]

    # Database — falls back to Vercel/Neon-injected POSTGRES_URL when DATABASE_URL is unset
    DATABASE_URL: str = os.getenv("POSTGRES_URL") or "sqlite+aiosqlite:///./payledger.db"

    # Business Limits
    MAX_DAILY_TRANSFER_LIMIT: float = 500000.00
    DEFAULT_CURRENCY: str = "NGN"
    ALLOWED_CURRENCIES: List[str] = ["NGN", "USD", "EUR", "GBP"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalize_db(cls, v: str) -> str:
        return normalize_database_url(v)

    @property
    def IS_SERVERLESS(self) -> bool:
        return bool(os.getenv("VERCEL"))

    @property
    def IS_PRODUCTION(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @model_validator(mode="after")
    def _guard_production(self) -> "Settings":
        if self.IS_PRODUCTION:
            if self.SECRET_KEY == _DEV_SECRET or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be set to a strong value (>=32 chars) in production."
                )
            if self.DATABASE_URL.startswith("sqlite") and self.IS_SERVERLESS:
                raise ValueError(
                    "SQLite is not persistent on Vercel. Set DATABASE_URL to a Postgres database."
                )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
