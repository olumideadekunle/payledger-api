from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api.v1.router import api_v1_router
from app.core.exceptions import PayLedgerException


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database schema is created
    await init_db()
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

# CORS middleware for mobile and frontend apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    """System health check and readiness probe."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["System"])
async def root():
    """Root redirect and welcome information."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }
