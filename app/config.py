from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "PayLedger API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "supersecretjwtkeyforlocaldevelopmentpayledger123456"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./payledger.db"

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


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
