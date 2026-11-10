from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.user import UserRegister, UserLogin
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.constants import Role, UserStatus, Currency


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower().strip())
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def register(self, data: UserRegister, is_first_user_admin: bool = True) -> User:
        existing = await self.get_by_email(data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email '{data.email}' already exists.",
            )

        # First user registered can be automatically granted admin role for easy testing, or default to USER
        role = Role.USER
        if is_first_user_admin:
            stmt = select(User)
            any_user = await self.db.execute(stmt)
            if any_user.first() is None:
                role = Role.ADMIN

        user = User(
            email=data.email.lower().strip(),
            full_name=data.full_name.strip(),
            hashed_password=hash_password(data.password),
            role=role,
            status=UserStatus.ACTIVE,
        )
        self.db.add(user)
        await self.db.flush()

        # Automatically create default primary wallet (e.g. NGN) for user
        default_wallet = Wallet(
            user_id=user.id,
            currency=Currency.NGN,
        )
        self.db.add(default_wallet)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate(self, data: UserLogin) -> dict:
        user = await self.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is suspended or inactive.",
            )

        access_token = create_access_token(subject=user.id, role=user.role.value)
        refresh_token = create_refresh_token(subject=user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user,
        }

    async def refresh_tokens(self, refresh_token_str: str) -> dict:
        try:
            payload = decode_token(refresh_token_str)
            if payload.get("type") != "refresh":
                raise ValueError("Token is not a refresh token")
            user_id = payload.get("sub")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid refresh token: {str(e)}",
            )

        user = await self.get_by_id(user_id)
        if not user or user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        new_access_token = create_access_token(subject=user.id, role=user.role.value)
        new_refresh_token = create_refresh_token(subject=user.id)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": user,
        }
