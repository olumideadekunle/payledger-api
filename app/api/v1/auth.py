from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenRefreshRequest,
)
from app.services.auth_service import AuthService
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication & Profiles"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer account",
)
async def register(
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new user profile with a hashed password and automatically
    provisions their primary digital wallet.
    """
    auth_service = AuthService(db)
    user = await auth_service.register(data)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and issue JWT tokens",
)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Verifies user credentials and returns both an access token (short-lived)
    and a refresh token (long-lived).
    """
    auth_service = AuthService(db)
    result = await auth_service.authenticate(data)
    return result


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renew access token using refresh token",
)
async def refresh_tokens(
    data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchanges a valid refresh token for a fresh token pair.
    """
    auth_service = AuthService(db)
    result = await auth_service.refresh_tokens(data.refresh_token)
    return result


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Retrieve current user profile",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Returns the authenticated user's profile information.
    """
    return current_user
