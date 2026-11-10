import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import String, Numeric, Boolean, DateTime, ForeignKey, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.core.constants import Currency


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint("user_id", "currency", name="uq_user_currency_wallet"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    currency: Mapped[Currency] = mapped_column(
        SQLEnum(Currency), default=Currency.NGN, nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=4), default=Decimal("0.0000"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    user = relationship("User", back_populates="wallets")
    ledger_entries = relationship("LedgerEntry", back_populates="wallet", cascade="all, delete-orphan")
