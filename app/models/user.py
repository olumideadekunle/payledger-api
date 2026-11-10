import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.core.constants import Role, UserStatus


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        SQLEnum(Role), default=Role.USER, nullable=False
    )
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(UserStatus), default=UserStatus.ACTIVE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    wallets = relationship("Wallet", back_populates="user", cascade="all, delete-orphan")
