"""
Database Seeding Script for PayLedger API.
Populates initial sample accounts, wallets, and double-entry ledger transactions for demo and testing.
Run:
    python scripts/seed.py
"""

import asyncio
from decimal import Decimal
import sys
import os

# Add parent directory to sys.path so app imports work cleanly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import async_session_maker, init_db
from app.models.user import User
from app.models.wallet import Wallet
from app.core.constants import Role, UserStatus, Currency
from app.core.security import hash_password
from app.services.ledger_service import LedgerService


async def seed():
    print("Initializing PayLedger database schema...")
    await init_db()

    async with async_session_maker() as session:
        ledger_service = LedgerService(session)

        print("Seeding Administrator account...")
        admin = User(
            email="admin@payledger.internal",
            full_name="System Administrator",
            hashed_password=hash_password("AdminPass123!"),
            role=Role.ADMIN,
            status=UserStatus.ACTIVE,
        )
        session.add(admin)
        await session.flush()

        print("Seeding Customer accounts...")
        alice = User(
            email="alice@example.com",
            full_name="Alice Johnson",
            hashed_password=hash_password("AlicePass123!"),
            role=Role.USER,
            status=UserStatus.ACTIVE,
        )
        bob = User(
            email="bob@example.com",
            full_name="Bob Smith",
            hashed_password=hash_password("BobPass123!"),
            role=Role.USER,
            status=UserStatus.ACTIVE,
        )
        session.add_all([alice, bob])
        await session.flush()

        print("Provisioning Multi-Currency Wallets...")
        alice_ngn = Wallet(user_id=alice.id, currency=Currency.NGN)
        alice_usd = Wallet(user_id=alice.id, currency=Currency.USD)
        bob_ngn = Wallet(user_id=bob.id, currency=Currency.NGN)

        session.add_all([alice_ngn, alice_usd, bob_ngn])
        await session.flush()

        print("Executing initial deposits and double-entry ledger audit entries...")
        # 1. Fund Alice NGN
        await ledger_service.execute_deposit(
            wallet=alice_ngn,
            amount=Decimal("1500000.00"),
            description="Initial salary deposit",
        )
        # 2. Fund Alice USD
        await ledger_service.execute_deposit(
            wallet=alice_usd,
            amount=Decimal("5000.00"),
            description="Consulting retainer payout",
        )
        # 3. Fund Bob NGN
        await ledger_service.execute_deposit(
            wallet=bob_ngn,
            amount=Decimal("200000.00"),
            description="Opening balance funding",
        )

        print("Simulating peer-to-peer atomic transfer from Alice to Bob...")
        tx = await ledger_service.execute_transfer(
            source_wallet=alice_ngn,
            destination_wallet_id=bob_ngn.id,
            amount=Decimal("250000.00"),
            description="Payment for web design deliverables",
        )

        await session.commit()

        print("\n" + "=" * 60)
        print(" PAYLEDGER API SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("Sample Accounts Created:")
        print("  1. Admin:")
        print("     Email:    admin@payledger.internal")
        print("     Password: AdminPass123!")
        print("     Role:     Administrator")
        print("\n  2. Alice (Customer):")
        print("     Email:    alice@example.com")
        print("     Password: AlicePass123!")
        print(f"     NGN Bal:  {alice_ngn.balance} NGN")
        print(f"     USD Bal:  {alice_usd.balance} USD")
        print("\n  3. Bob (Customer):")
        print("     Email:    bob@example.com")
        print("     Password: BobPass123!")
        print(f"     NGN Bal:  {bob_ngn.balance} NGN")
        print("\nSample Transfer Reference:", tx.reference)
        print("=" * 60)
        print("Start server: uvicorn app.main:app --reload --port 8000")
        print("Explore docs: http://localhost:8000/docs\n")


if __name__ == "__main__":
    asyncio.run(seed())
