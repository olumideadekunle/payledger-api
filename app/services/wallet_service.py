from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.wallet import Wallet
from app.models.user import User
from app.core.constants import Currency
from app.core.exceptions import WalletNotFoundException


class WalletService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, wallet_id: str) -> Optional[Wallet]:
        stmt = select(Wallet).where(Wallet.id == wallet_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_wallets(self, user_id: str) -> List[Wallet]:
        stmt = select(Wallet).where(Wallet.user_id == user_id).order_by(Wallet.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create_wallet(self, user: User, currency: Currency) -> Wallet:
        # Check if user already has an active wallet in this currency
        stmt = select(Wallet).where(
            Wallet.user_id == user.id,
            Wallet.currency == currency,
        )
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User already has a {currency.value} wallet.",
            )

        wallet = Wallet(
            user_id=user.id,
            currency=currency,
        )
        self.db.add(wallet)
        await self.db.commit()
        await self.db.refresh(wallet)
        return wallet

    async def verify_wallet_ownership(self, wallet_id: str, user_id: str) -> Wallet:
        wallet = await self.get_by_id(wallet_id)
        if not wallet:
            raise WalletNotFoundException(wallet_id)
        if wallet.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this wallet.",
            )
        if not wallet.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This wallet is inactive.",
            )
        return wallet
