from typing import List, Dict, Any
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionResponse
from app.schemas.user import UserResponse
from app.services.ledger_service import LedgerService
from app.services.auth_service import AuthService
from app.api.deps import get_current_admin
from app.core.constants import UserStatus

router = APIRouter(prefix="/admin", tags=["Admin & System Operations"])


@router.get(
    "/metrics",
    summary="System-wide financial ledger metrics",
)
async def get_system_metrics(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns high-level statistics for platform administrators:
    total registered users, total transactions executed, and wallet balances grouped by currency.
    """
    user_count = (await db.execute(select(func.count(User.id)))).scalar_one()
    tx_count = (await db.execute(select(func.count(Transaction.id)))).scalar_one()

    # Aggregate wallet balances grouped by currency
    currency_stmt = select(
        Wallet.currency,
        func.coalesce(func.sum(Wallet.balance), Decimal("0.0000")).label("total_balance"),
        func.count(Wallet.id).label("wallet_count"),
    ).group_by(Wallet.currency)
    currency_res = await db.execute(currency_stmt)

    balances = [
        {
            "currency": row[0].value,
            "total_balance": str(row[1]),
            "wallet_count": row[2],
        }
        for row in currency_res.all()
    ]

    return {
        "status": "healthy",
        "total_users": user_count,
        "total_transactions": tx_count,
        "vault_balances": balances,
    }


@router.get(
    "/transactions",
    response_model=List[TransactionResponse],
    summary="List all platform transactions (audit log)",
)
async def list_all_transactions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Administrator audit log for examining all transactions across the entire platform.
    """
    ledger_service = LedgerService(db)
    return await ledger_service.get_all_transactions(limit=limit, offset=offset)


@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
    summary="Update customer account status (e.g. freeze/unfreeze)",
)
async def update_user_status(
    user_id: str,
    new_status: UserStatus,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Enables administrators to immediately freeze or reinstate customer accounts.
    """
    auth_service = AuthService(db)
    user = await auth_service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.status = new_status
    await db.commit()
    await db.refresh(user)
    return user
