import os
from functools import lru_cache
from typing import List
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
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
        v = normalize_database_url(v)
        # Zero-config on Vercel: only /tmp is writable. Data there is ephemeral (demo mode).
        if os.getenv("VERCEL") and v.startswith("sqlite") and "/tmp/" not in v:
            v = "sqlite+aiosqlite:////tmp/payledger.db"
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def _default_secret(cls, v: str) -> str:
        # Zero-config on Vercel: derive a stable per-project key so JWTs survive cold starts.
        # Not secret-grade (project id is not confidential) — demo mode only; flagged in /health.
        if os.getenv("VERCEL") and v == _DEV_SECRET:
            import hashlib

            seed = "payledger-demo:" + (os.getenv("VERCEL_PROJECT_ID") or os.getenv("VERCEL_URL", ""))
            v = hashlib.sha256(seed.encode()).hexdigest()
            os.environ["PAYLEDGER_DEMO_SECRET"] = "1"
        return v

    @property
    def IS_DEMO(self) -> bool:
        return self.IS_SERVERLESS and (
            self.DATABASE_URL.startswith("sqlite") or bool(os.getenv("PAYLEDGER_DEMO_SECRET"))
        )

    @property
    def CONFIG_WARNINGS(self) -> List[str]:
        warnings: List[str] = []
        if self.IS_SERVERLESS and self.DATABASE_URL.startswith("sqlite"):
            warnings.append("Demo mode: no Postgres connected, data is temporary and may reset.")
        if os.getenv("PAYLEDGER_DEMO_SECRET"):
            warnings.append("Demo mode: SECRET_KEY not set, using an auto-generated demo key.")
        return warnings

    @property
    def IS_SERVERLESS(self) -> bool:
        return bool(os.getenv("VERCEL"))

    @property
    def IS_PRODUCTION(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def CONFIG_ERRORS(self) -> List[str]:
        """
        Misconfigurations that make the deployment unsafe. Reported via HTTP 503
        instead of crashing at import, so the cause is visible from the browser.
        """
        errors: List[str] = []
        # Only enforced when ENVIRONMENT=production is explicitly set; otherwise demo mode.
        if self.IS_PRODUCTION:
            if (
                self.SECRET_KEY == _DEV_SECRET
                or len(self.SECRET_KEY) < 32
                or os.getenv("PAYLEDGER_DEMO_SECRET")
            ):
                errors.append(
                    "SECRET_KEY is missing or too short. Set a random value of 32+ characters "
                    "in Vercel → Settings → Environment Variables, then redeploy."
                )
            if self.DATABASE_URL.startswith("sqlite") and self.IS_SERVERLESS:
                errors.append(
                    "No Postgres database configured. Connect one in Vercel → Storage "
                    "(Neon) so DATABASE_URL / POSTGRES_URL is set, then redeploy."
                )
        return errors


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
