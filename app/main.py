import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine, ensure_db_initialized
from app.api.v1.router import api_v1_router
from app.core.exceptions import PayLedgerException

logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO)
logger = logging.getLogger("payledger")

_config_errors = settings.CONFIG_ERRORS
for _err in _config_errors:
    logger.error("Configuration error: %s", _err)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure schema exists (also lazily retried per-request on serverless)
    if _config_errors:
        yield
        return
    try:
        await ensure_db_initialized()
    except Exception:  # don't crash cold start; get_db will retry
        logger.exception("Database initialization failed at startup")
    yield
    # Shutdown logic (if any)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
# PayLedger API — High-Performance Double-Entry Financial Engine

A production-grade, fintech-ready digital wallet and transaction ledger backend built with **FastAPI**, **SQLAlchemy 2.0 Async**, and **Pydantic v2**.

### Key Architectural Highlights:
* **Double-Entry Bookkeeping**: Strict immutable debit and credit ledger entries ensuring arithmetic balance invariants across all transactions.
* **ACID Transfers**: Atomic balance updates with concurrency protections preventing overdrafts, race conditions, or duplicate credits.
* **Idempotency Protection**: Deterministic idempotency processing via `X-Idempotency-Key` headers to eliminate double charging or replay anomalies.
* **Multi-Currency Wallets**: Native support for isolated currency accounts (NGN, USD, EUR, GBP) with high-precision Decimal financial arithmetic.
* **Role-Based Access Control**: Secure JWT-based authentication supporting customer profiles and administrative oversight.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — wildcard origins cannot be combined with credentials per the CORS spec
_wildcard = settings.CORS_ORIGINS == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=not _wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Attach request IDs, timing, and security headers to every response."""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    start = time.perf_counter()
    if _config_errors:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error_code": "SERVICE_MISCONFIGURED",
                "detail": _config_errors,
                "request_id": request_id,
            },
        )
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error request_id=%s path=%s", request_id, request.url.path)
        response = JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_code": "INTERNAL_SERVER_ERROR",
                "detail": "An unexpected error occurred.",
                "request_id": request_id,
            },
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{(time.perf_counter() - start) * 1000:.2f}ms"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.exception_handler(PayLedgerException)
async def payledger_exception_handler(request: Request, exc: PayLedgerException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "detail": exc.detail,
            "extra": exc.extra,
        },
    )


# Include API v1 Router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System"])
async def health_check():
    """Liveness + readiness probe (verifies database connectivity)."""
    db_ok = True
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check database ping failed")
        db_ok = False
    return JSONResponse(
        status_code=200 if db_ok else 503,
        content={
            "status": "healthy" if db_ok else "degraded",
            "database": "up" if db_ok else "down",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "mode": "demo" if settings.IS_DEMO else "full",
            "warnings": settings.CONFIG_WARNINGS,
        },
    )


@app.get("/", tags=["System"], include_in_schema=False)
async def root():
    """Send visitors straight to the interactive API docs."""
    return RedirectResponse(url="/docs")
