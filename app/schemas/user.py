from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.core.constants import Role, UserStatus


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)


class UserRegister(UserBase):
    password: str = Field(
        min_length=8,
        max_length=64,
        description="Password must be at least 8 characters long"
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: str
    role: Role
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefreshRequest(BaseModel):
    refresh_token: str
