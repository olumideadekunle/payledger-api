import uuid
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.wallet import Wallet
from app.models.transaction import Transaction, LedgerEntry
from app.core.constants import (
    TransactionType,
    TransactionStatus,
    LedgerEntryType,
)
from app.core.exceptions import (
    InsufficientFundsException,
    WalletNotFoundException,
    CurrencyMismatchException,
    SelfTransferException,
)


class LedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def generate_reference(self, prefix: str = "TXN") -> str:
        """Generate high-entropy unique transaction reference."""
        token = uuid.uuid4().hex[:12].upper()
        return f"{prefix}_{token}"

    async def execute_deposit(
        self,
        wallet: Wallet,
        amount: Decimal,
        description: str = "Account deposit",
    ) -> Transaction:
        """Deposit funds into a wallet and record double-entry audit entry."""
        if amount <= Decimal("0.0000"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deposit amount must be strictly greater than zero.",
            )

        ref = self.generate_reference("DEP")

        # 1. Update wallet balance
        wallet.balance += amount
        balance_after = wallet.balance

        # 2. Create transaction record
        tx = Transaction(
            reference=ref,
            destination_wallet_id=wallet.id,
            amount=amount,
            fee=Decimal("0.0000"),
            currency=wallet.currency,
            type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED,
            description=description,
        )
        self.db.add(tx)
        await self.db.flush()

        # 3. Create credit ledger entry
        entry = LedgerEntry(
            transaction_id=tx.id,
            wallet_id=wallet.id,
            entry_type=LedgerEntryType.CREDIT,
            amount=amount,
            balance_after=balance_after,
        )
        self.db.add(entry)

        await self.db.commit()
        await self.db.refresh(tx)
        return tx

    async def execute_withdrawal(
        self,
        wallet: Wallet,
        amount: Decimal,
        description: str = "Account withdrawal",
    ) -> Transaction:
        """Withdraw funds from a wallet, verifying balance."""
        if amount <= Decimal("0.0000"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Withdrawal amount must be strictly greater than zero.",
            )

        if wallet.balance < amount:
            raise InsufficientFundsException(
                available_balance=wallet.balance,
                attempted_amount=amount,
            )

        ref = self.generate_reference("WTH")

        # 1. Update wallet balance
        wallet.balance -= amount
        balance_after = wallet.balance

        # 2. Create transaction record
        tx = Transaction(
            reference=ref,
            source_wallet_id=wallet.id,
            amount=amount,
            fee=Decimal("0.0000"),
            currency=wallet.currency,
            type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.COMPLETED,
            description=description,
        )
        self.db.add(tx)
        await self.db.flush()

        # 3. Create debit ledger entry
        entry = LedgerEntry(
            transaction_id=tx.id,
            wallet_id=wallet.id,
            entry_type=LedgerEntryType.DEBIT,
            amount=amount,
            balance_after=balance_after,
        )
        self.db.add(entry)

        await self.db.commit()
        await self.db.refresh(tx)
        return tx

    async def execute_transfer(
        self,
        source_wallet: Wallet,
        destination_wallet_id: str,
        amount: Decimal,
        description: str = "Wallet transfer",
    ) -> Transaction:
        """
        Execute an atomic peer-to-peer wallet transfer.
        Enforces double-entry ledger invariant (Total debits == Total credits).
        """
        if amount <= Decimal("0.0000"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transfer amount must be strictly greater than zero.",
            )

        if source_wallet.id == destination_wallet_id:
            raise SelfTransferException()

        # Fetch and validate destination wallet
        dest_stmt = select(Wallet).where(Wallet.id == destination_wallet_id)
        res = await self.db.execute(dest_stmt)
        dest_wallet = res.scalar_one_or_none()

        if not dest_wallet:
            raise WalletNotFoundException(destination_wallet_id)

        if not dest_wallet.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Destination wallet is inactive or suspended.",
            )

        if source_wallet.currency != dest_wallet.currency:
            raise CurrencyMismatchException(
                source_currency=source_wallet.currency.value,
                target_currency=dest_wallet.currency.value,
            )

        # Ensure sufficient funds
        if source_wallet.balance < amount:
            raise InsufficientFundsException(
                available_balance=source_wallet.balance,
                attempted_amount=amount,
            )

        ref = self.generate_reference("TRF")

        # Atomic Balance Mutations
        source_wallet.balance -= amount
        source_balance_after = source_wallet.balance

        dest_wallet.balance += amount
        dest_balance_after = dest_wallet.balance

        # Transaction Record
        tx = Transaction(
            reference=ref,
            source_wallet_id=source_wallet.id,
            destination_wallet_id=dest_wallet.id,
            amount=amount,
            fee=Decimal("0.0000"),
            currency=source_wallet.currency,
            type=TransactionType.TRANSFER_OUT,
            status=TransactionStatus.COMPLETED,
            description=description,
        )
        self.db.add(tx)
        await self.db.flush()

        # Double-entry ledger audit:
        # 1. Debit from source
        debit_entry = LedgerEntry(
            transaction_id=tx.id,
            wallet_id=source_wallet.id,
            entry_type=LedgerEntryType.DEBIT,
            amount=amount,
            balance_after=source_balance_after,
        )
        # 2. Credit to destination
        credit_entry = LedgerEntry(
            transaction_id=tx.id,
            wallet_id=dest_wallet.id,
            entry_type=LedgerEntryType.CREDIT,
            amount=amount,
            balance_after=dest_balance_after,
        )

        self.db.add_all([debit_entry, credit_entry])

        # Commit atomic unit of work
        await self.db.commit()
        await self.db.refresh(tx)
        return tx

    async def get_statement(
        self,
        wallet: Wallet,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[LedgerEntry], Decimal, Decimal, int]:
        """Fetch all ledger audit entries for this wallet with running calculations."""
        # Entries query
        stmt = (
            select(LedgerEntry)
            .where(LedgerEntry.wallet_id == wallet.id)
            .order_by(LedgerEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.db.execute(stmt)
        entries = list(res.scalars().all())

        # Total Credits
        credit_stmt = select(func.coalesce(func.sum(LedgerEntry.amount), Decimal("0.0000"))).where(
            and_(
                LedgerEntry.wallet_id == wallet.id,
                LedgerEntry.entry_type == LedgerEntryType.CREDIT,
            )
        )
        total_credits = (await self.db.execute(credit_stmt)).scalar_one()

        # Total Debits
        debit_stmt = select(func.coalesce(func.sum(LedgerEntry.amount), Decimal("0.0000"))).where(
            and_(
                LedgerEntry.wallet_id == wallet.id,
                LedgerEntry.entry_type == LedgerEntryType.DEBIT,
            )
        )
        total_debits = (await self.db.execute(debit_stmt)).scalar_one()

        # Count
        count_stmt = select(func.count(LedgerEntry.id)).where(LedgerEntry.wallet_id == wallet.id)
        total_count = (await self.db.execute(count_stmt)).scalar_one()

        return entries, total_credits, total_debits, total_count

    async def get_transaction_by_reference(self, reference: str) -> Optional[Transaction]:
        stmt = select(Transaction).where(Transaction.reference == reference)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_all_transactions(self, limit: int = 50, offset: int = 0) -> List[Transaction]:
        stmt = select(Transaction).order_by(Transaction.created_at.desc()).limit(limit).offset(offset)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
