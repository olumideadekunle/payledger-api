from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.wallets import router as wallets_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.admin import router as admin_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(wallets_router)
api_v1_router.include_router(transactions_router)
api_v1_router.include_router(admin_router)
