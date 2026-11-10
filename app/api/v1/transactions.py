from typing import Optional
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.transaction import (
    DepositRequest,
    WithdrawRequest,
    TransferRequest,
    TransactionResponse,
)
from app.services.wallet_service import WalletService
from app.services.ledger_service import LedgerService
from app.services.idempotency_service import IdempotencyService
from app.api.deps import get_current_user, get_idempotency_key
from app.core.constants import Role

router = APIRouter(prefix="/transactions", tags=["Payments & Ledger Transactions"])


@router.post(
    "/deposit",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Deposit funds into wallet",
)
async def deposit(
    data: DepositRequest,
    current_user: User = Depends(get_current_user),
    idempotency_key: Optional[str] = Depends(get_idempotency_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Credits a user's wallet and records an immutable ledger credit entry.
    Supports idempotent submission via `X-Idempotency-Key` header.
    """
    idempotency_service = IdempotencyService(db)
    if idempotency_key:
        cached = await idempotency_service.get_recorded_response(idempotency_key, current_user.id)
        if cached:
            status_code, body = cached
            return JSONResponse(status_code=status_code, content=body)

    wallet_service = WalletService(db)
    wallet = await wallet_service.verify_wallet_ownership(data.wallet_id, current_user.id)

    ledger_service = LedgerService(db)
    tx = await ledger_service.execute_deposit(
        wallet=wallet,
        amount=data.amount,
        description=data.description or "Account deposit",
    )

    response_data = TransactionResponse.model_validate(tx).model_dump(mode="json")

    if idempotency_key:
        req_hash = idempotency_service.compute_request_hash("/deposit", data.model_dump(mode="json"))
        await idempotency_service.record_response(
            key=idempotency_key,
            user_id=current_user.id,
            endpoint="/deposit",
            request_hash=req_hash,
            status_code=status.HTTP_201_CREATED,
            response_dict=response_data,
        )

    return response_data


@router.post(
    "/withdraw",
    response_model=TransactionResponse,
    summary="Withdraw funds from wallet",
)
async def withdraw(
    data: WithdrawRequest,
    current_user: User = Depends(get_current_user),
    idempotency_key: Optional[str] = Depends(get_idempotency_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Debits a user's wallet after verifying sufficient funds.
    Records an immutable debit ledger entry.
    """
    idempotency_service = IdempotencyService(db)
    if idempotency_key:
        cached = await idempotency_service.get_recorded_response(idempotency_key, current_user.id)
        if cached:
            status_code, body = cached
            return JSONResponse(status_code=status_code, content=body)

    wallet_service = WalletService(db)
    wallet = await wallet_service.verify_wallet_ownership(data.wallet_id, current_user.id)

    ledger_service = LedgerService(db)
    tx = await ledger_service.execute_withdrawal(
        wallet=wallet,
        amount=data.amount,
        description=data.description or "Account withdrawal",
    )

    response_data = TransactionResponse.model_validate(tx).model_dump(mode="json")

    if idempotency_key:
        req_hash = idempotency_service.compute_request_hash("/withdraw", data.model_dump(mode="json"))
        await idempotency_service.record_response(
            key=idempotency_key,
            user_id=current_user.id,
            endpoint="/withdraw",
            request_hash=req_hash,
            status_code=status.HTTP_200_OK,
            response_dict=response_data,
        )

    return response_data


@router.post(
    "/transfer",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Atomic peer-to-peer wallet transfer",
)
async def transfer(
    data: TransferRequest,
    current_user: User = Depends(get_current_user),
    idempotency_key: Optional[str] = Depends(get_idempotency_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes an atomic transfer between two wallets.
    Guarantees strict double-entry invariant: Total Debits == Total Credits.
    Enforces concurrency checks, balance verification, and idempotency protection.
    """
    idempotency_service = IdempotencyService(db)
    if idempotency_key:
        cached = await idempotency_service.get_recorded_response(idempotency_key, current_user.id)
        if cached:
            status_code, body = cached
            return JSONResponse(status_code=status_code, content=body)

    wallet_service = WalletService(db)
    source_wallet = await wallet_service.verify_wallet_ownership(
        data.source_wallet_id, current_user.id
    )

    ledger_service = LedgerService(db)
    tx = await ledger_service.execute_transfer(
        source_wallet=source_wallet,
        destination_wallet_id=data.destination_wallet_id,
        amount=data.amount,
        description=data.description or "Wallet transfer",
    )

    response_data = TransactionResponse.model_validate(tx).model_dump(mode="json")

    if idempotency_key:
        req_hash = idempotency_service.compute_request_hash("/transfer", data.model_dump(mode="json"))
        await idempotency_service.record_response(
            key=idempotency_key,
            user_id=current_user.id,
            endpoint="/transfer",
            request_hash=req_hash,
            status_code=status.HTTP_201_CREATED,
            response_dict=response_data,
        )

    return response_data


@router.get(
    "/{reference}",
    response_model=TransactionResponse,
    summary="Get transaction status by reference",
)
async def get_transaction(
    reference: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves full transaction status and ledger history by transaction reference.
    """
    ledger_service = LedgerService(db)
    tx = await ledger_service.get_transaction_by_reference(reference)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction reference '{reference}' not found.",
        )

    # Authorization: User must be sender, receiver, or admin
    if current_user.role != Role.ADMIN:
        wallet_service = WalletService(db)
        user_wallets = await wallet_service.get_user_wallets(current_user.id)
        user_wallet_ids = {w.id for w in user_wallets}
        if tx.source_wallet_id not in user_wallet_ids and tx.destination_wallet_id not in user_wallet_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this transaction.",
            )

    return tx
