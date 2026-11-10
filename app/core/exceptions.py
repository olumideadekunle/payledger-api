from typing import Any, Optional
from fastapi import HTTPException, status


class PayLedgerException(HTTPException):
    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        detail: str = "A financial ledger error occurred.",
        error_code: str = "LEDGER_ERROR",
        extra: Optional[dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.extra = extra or {}


class InsufficientFundsException(PayLedgerException):
    def __init__(self, available_balance: Any, attempted_amount: Any):
        super().__init__(
            status_code=422,
            detail=f"Insufficient funds. Available: {available_balance}, Attempted: {attempted_amount}.",
            error_code="INSUFFICIENT_FUNDS",
            extra={"available_balance": str(available_balance), "attempted_amount": str(attempted_amount)},
        )


class WalletNotFoundException(PayLedgerException):
    def __init__(self, wallet_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet '{wallet_id}' not found.",
            error_code="WALLET_NOT_FOUND",
            extra={"wallet_id": wallet_id},
        )


class CurrencyMismatchException(PayLedgerException):
    def __init__(self, source_currency: str, target_currency: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Currency mismatch: Cannot transfer from {source_currency} to {target_currency}.",
            error_code="CURRENCY_MISMATCH",
            extra={"source": source_currency, "target": target_currency},
        )


class SelfTransferException(PayLedgerException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-transfers to the same wallet are not permitted.",
            error_code="SELF_TRANSFER_PROHIBITED",
        )


class AccountSuspendedException(PayLedgerException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended. Contact administration.",
            error_code="ACCOUNT_SUSPENDED",
        )


class DuplicateIdempotencyKeyException(PayLedgerException):
    def __init__(self, idempotency_key: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A transaction with idempotency key '{idempotency_key}' is already processed or in progress.",
            error_code="DUPLICATE_IDEMPOTENCY_KEY",
            extra={"idempotency_key": idempotency_key},
        )
