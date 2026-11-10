import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.core.constants import Currency, TransactionType, TransactionStatus, LedgerEntryType


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    reference: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    source_wallet_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wallets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    destination_wallet_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wallets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=4), nullable=False
    )
    fee: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=4), default=Decimal("0.0000"), nullable=False
    )
    currency: Mapped[Currency] = mapped_column(
        SQLEnum(Currency), nullable=False
    )
    type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType), nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        SQLEnum(TransactionStatus), default=TransactionStatus.COMPLETED, nullable=False
    )
    description: Mapped[str] = mapped_column(
        String(255), default="", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    ledger_entries = relationship(
        "LedgerEntry",
        back_populates="transaction",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class LedgerEntry(Base):
    """
    Immutable double-entry ledger record.
    Every financial movement is backed by debit or credit entries.
    """
    __tablename__ = "ledger_entries"
    __table_args__ = (
        Index("ix_ledger_wallet_created", "wallet_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    wallet_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False
    )
    entry_type: Mapped[LedgerEntryType] = mapped_column(
        SQLEnum(LedgerEntryType), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=4), nullable=False
    )
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=4), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    transaction = relationship("Transaction", back_populates="ledger_entries")
    wallet = relationship("Wallet", back_populates="ledger_entries")
