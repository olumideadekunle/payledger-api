import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs: dict = {"echo": False, "future": True}
if _is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif settings.IS_SERVERLESS:
    # Serverless functions freeze between invocations; pooled connections go stale and
    # exhaust DB connection limits. Open per-request and rely on the provider's pooler
    # (e.g. Neon's -pooler host). Disable asyncpg's statement cache for PgBouncer compat.
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["connect_args"] = {"statement_cache_size": 0}
else:
    engine_kwargs.update(pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=1800)

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session per request."""
    await ensure_db_initialized()
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables (idempotent)."""
    # Import models so they register on Base.metadata
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


_initialized = False
_init_lock = asyncio.Lock()


async def ensure_db_initialized() -> None:
    """
    Lazily create schema once per process. Serverless runtimes don't reliably run
    ASGI lifespan startup, so this runs on the first request as a fallback.
    """
    global _initialized
    if _initialized:
        return
    async with _init_lock:
        if not _initialized:
            await init_db()
            _initialized = True
