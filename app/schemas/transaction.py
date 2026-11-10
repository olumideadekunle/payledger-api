from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import Currency, TransactionType, TransactionStatus, LedgerEntryType


class DepositRequest(BaseModel):
    wallet_id: str
    amount: Decimal = Field(gt=Decimal("0.00"), decimal_places=4, max_digits=18)
    description: Optional[str] = Field(default="Account funding/deposit", max_length=255)


class WithdrawRequest(BaseModel):
    wallet_id: str
    amount: Decimal = Field(gt=Decimal("0.00"), decimal_places=4, max_digits=18)
    description: Optional[str] = Field(default="Account withdrawal/payout", max_length=255)


class TransferRequest(BaseModel):
    source_wallet_id: str = Field(description="Sender wallet ID")
    destination_wallet_id: str = Field(description="Recipient wallet ID")
    amount: Decimal = Field(gt=Decimal("0.00"), decimal_places=4, max_digits=18)
    description: Optional[str] = Field(default="Peer-to-peer wallet transfer", max_length=255)


class LedgerEntryResponse(BaseModel):
    id: str
    transaction_id: str
    wallet_id: str
    entry_type: LedgerEntryType
    amount: Decimal
    balance_after: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionResponse(BaseModel):
    id: str
    reference: str
    source_wallet_id: Optional[str] = None
    destination_wallet_id: Optional[str] = None
    amount: Decimal
    fee: Decimal
    currency: Currency
    type: TransactionType
    status: TransactionStatus
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountStatementResponse(BaseModel):
    wallet_id: str
    currency: Currency
    current_balance: Decimal
    total_credits: Decimal
    total_debits: Decimal
    entry_count: int
    entries: List[LedgerEntryResponse]
