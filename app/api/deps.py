from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.core.security import decode_token
from app.core.constants import Role, UserStatus
from app.services.auth_service import AuthService

security_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that extracts and validates the currently logged-in user from the JWT Bearer token."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: access token required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token subject missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    user = await auth_service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is suspended or inactive",
        )

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency that guarantees the caller holds the administrator role."""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required.",
        )
    return current_user


async def get_idempotency_key(
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
) -> Optional[str]:
    """Optional header dependency for idempotency protection."""
    if x_idempotency_key:
        return x_idempotency_key.strip()
    return None
