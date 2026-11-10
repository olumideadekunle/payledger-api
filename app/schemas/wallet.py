from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import Currency


class WalletCreate(BaseModel):
    currency: Currency = Field(
        default=Currency.NGN,
        description="Currency for the new wallet (e.g. NGN, USD, EUR, GBP)"
    )


class WalletResponse(BaseModel):
    id: str
    user_id: str
    currency: Currency
    balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WalletBalanceResponse(BaseModel):
    wallet_id: str
    currency: Currency
    balance: Decimal
    is_active: bool
