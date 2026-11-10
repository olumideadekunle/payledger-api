from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.wallet import WalletCreate, WalletResponse
from app.schemas.transaction import AccountStatementResponse, LedgerEntryResponse
from app.services.wallet_service import WalletService
from app.services.ledger_service import LedgerService
from app.api.deps import get_current_user

router = APIRouter(prefix="/wallets", tags=["Wallets & Balances"])


@router.post(
    "",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new currency wallet",
)
@router.post(
    "/",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_wallet(
    data: WalletCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new wallet for the authenticated user with the selected currency (e.g. USD, EUR, GBP).
    """
    wallet_service = WalletService(db)
    wallet = await wallet_service.create_wallet(current_user, data.currency)
    return wallet


@router.get(
    "",
    response_model=List[WalletResponse],
    summary="List all wallets owned by current user",
)
@router.get(
    "/",
    response_model=List[WalletResponse],
    include_in_schema=False,
)
async def list_my_wallets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all active and inactive digital wallets belonging to the authenticated user.
    """
    wallet_service = WalletService(db)
    wallets = await wallet_service.get_user_wallets(current_user.id)
    return wallets


@router.get(
    "/{wallet_id}",
    response_model=WalletResponse,
    summary="Get details of a specific wallet",
)
async def get_wallet(
    wallet_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches details and real-time balance of a specific user wallet.
    """
    wallet_service = WalletService(db)
    wallet = await wallet_service.verify_wallet_ownership(wallet_id, current_user.id)
    return wallet


@router.get(
    "/{wallet_id}/statement",
    response_model=AccountStatementResponse,
    summary="Get full double-entry ledger statement for a wallet",
)
async def get_wallet_statement(
    wallet_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates an official ledger statement with chronological debit/credit entries,
    running balances, total debits, and total credits.
    """
    wallet_service = WalletService(db)
    wallet = await wallet_service.verify_wallet_ownership(wallet_id, current_user.id)

    ledger_service = LedgerService(db)
    entries, total_credits, total_debits, total_count = await ledger_service.get_statement(
        wallet=wallet, limit=limit, offset=offset
    )

    return AccountStatementResponse(
        wallet_id=wallet.id,
        currency=wallet.currency,
        current_balance=wallet.balance,
        total_credits=total_credits,
        total_debits=total_debits,
        entry_count=total_count,
        entries=[LedgerEntryResponse.model_validate(e) for e in entries],
    )
