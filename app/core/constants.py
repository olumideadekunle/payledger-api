from enum import Enum


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Currency(str, Enum):
    NGN = "NGN"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


class LedgerEntryType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"
