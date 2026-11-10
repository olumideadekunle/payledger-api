# PayLedger API

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red?style=flat)](https://www.sqlalchemy.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=flat&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A production-grade, asynchronous financial ledger and digital wallet API built with **Python 3.12**, **FastAPI**, **SQLAlchemy 2.0 Async**, and **Pydantic v2**.

Designed with bank-grade financial engineering principles: strict **immutable double-entry bookkeeping**, **ACID-compliant atomic peer-to-peer transfers**, **deterministic idempotency key protection**, and **high-precision fixed-point decimal arithmetic** to prevent floating-point rounding leakage.

---

## Architecture Overview

```
                        ┌───────────────────────────────────────────────┐
                        │              Client / Mobile App              │
                        └───────────────────────┬───────────────────────┘
                                                │
                                    HTTPS / Bearer JWT Token
                                    Header: X-Idempotency-Key
                                                │
                                                ▼
                        ┌───────────────────────────────────────────────┐
                        │             FastAPI Application               │
                        │  ├─ Auth & Role-Based Access Control (RBAC)   │
                        │  ├─ Pydantic v2 Validation & Serializers      │
                        │  └─ Idempotency Filter & Request Hash Cache   │
                        └───────────────────────┬───────────────────────┘
                                                │
                                                ▼
                        ┌───────────────────────────────────────────────┐
                        │            Ledger Engine (Service)            │
                        │  ├─ Concurrency Locks & Balance Validation    │
                        │  ├─ Double-Entry Debit/Credit Generator       │
                        │  └─ Invariant: Sum(Debits) == Sum(Credits)    │
                        └───────────────────────┬───────────────────────┘
                                                │
                                                ▼
                        ┌───────────────────────────────────────────────┐
                        │           Async SQLAlchemy 2.0 Engine         │
                        │  ├─ Users & Auth Credential Store             │
                        │  ├─ Wallets (NGN, USD, EUR, GBP)              │
                        │  ├─ Immutable Ledger Entries (Audit Trail)    │
                        │  └─ Idempotency Records                       │
                        └───────────────────────────────────────────────┘
```

---

## Core Financial Engineering Principles

### 1. Immutable Double-Entry Ledger
No balance changes in PayLedger occur without a corresponding audit trail.
- Every **transfer** produces two simultaneous ledger entries: a **DEBIT** on the source wallet and an exact **CREDIT** on the recipient wallet.
- Deposits and withdrawals generate verifiable single-sided ledger entries with calculated running `balance_after` snapshots.
- Mathematical invariant: `Total Debits == Total Credits` across all transfers.

### 2. Fixed-Point Decimal Arithmetic
Computations never use native IEEE 754 floating-point numbers (`float`). All monetary amounts and balances are modeled via Python's `decimal.Decimal` and database `Numeric(precision=18, scale=4)` to eliminate fractional penny discrepancies.

### 3. Distributed Idempotency Protection
Clients can submit payments with an `X-Idempotency-Key` header.
- If a client experiences a network timeout or retries a request, the engine detects the duplicate key and returns the cached result without executing a second transfer or debiting funds twice.

### 4. Overdraft Prevention & ACID Transactions
Transfers execute inside atomic database transactions:
- Source and destination balances update together or rollback completely.
- Wallets with insufficient funds are rejected with HTTP 422 before any balance mutation occurs.
- Self-transfers to the same wallet are strictly prohibited.

---

## Project Structure

```
payledger-api/
├── app/
│   ├── api/
│   │   ├── deps.py               # Fastapi security dependencies & JWT decoding
│   │   └── v1/
│   │       ├── auth.py           # Register, login, refresh, me
│   │       ├── wallets.py        # Wallet creation, balances, ledger statements
│   │       ├── transactions.py   # Deposit, withdraw, atomic transfer, verify
│   │       ├── admin.py          # Metrics, user suspension, audit logs
│   │       └── router.py         # Root v1 router aggregation
│   ├── core/
│   │   ├── constants.py          # Enums (Role, Currency, TransactionStatus, etc.)
│   │   ├── exceptions.py         # Domain error handlers & HTTP exception mapping
│   │   └── security.py           # Bcrypt password hashing & PyJWT token handling
│   ├── models/                   # SQLAlchemy 2.0 Async ORM models
│   │   ├── user.py               # User identity & status
│   │   ├── wallet.py             # Multi-currency balances
│   │   ├── transaction.py        # Transactions & immutable LedgerEntry records
│   │   └── idempotency.py        # Request deduplication store
│   ├── schemas/                  # Pydantic v2 schemas & DTOs
│   │   ├── user.py
│   │   ├── wallet.py
│   │   ├── transaction.py
│   │   └── common.py
│   ├── services/                 # Core domain business logic
│   │   ├── auth_service.py
│   │   ├── wallet_service.py
│   │   ├── ledger_service.py
│   │   └── idempotency_service.py
│   ├── config.py                 # Pydantic BaseSettings & environment variables
│   ├── database.py               # Async SQLAlchemy engine & session maker
│   └── main.py                   # FastAPI application initialization & lifespan
├── tests/
│   ├── conftest.py               # In-memory async database & TestClient fixtures
│   ├── test_auth.py              # Auth & JWT verification tests
│   ├── test_wallets.py           # Multi-currency wallet tests
│   ├── test_transfers.py         # Atomic transfers, overdraft, double-entry tests
│   └── test_idempotency.py       # Duplicate request deduplication tests
├── Dockerfile                    # Containerization definition
├── docker-compose.yml            # Local orchestration
├── requirements.txt              # Production and test dependencies
├── pyproject.toml                # Pytest & Ruff linter settings
├── .env.example                  # Environment configuration template
└── README.md
```

---

## Quickstart Guide

### Option 1: Run Locally with Python Virtual Environment

#### 1. Clone repository & navigate to folder
```bash
git clone https://github.com/olumideadekunle/payledger-api.git
cd payledger-api
```

#### 2. Create and activate a Python 3.12 virtual environment
```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

#### 3. Install dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure environment
```bash
# Windows
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

#### 5. Start the development server
```bash
uvicorn app.main:app --reload --port 8000
```

The API will now be live at: **`http://localhost:8000`**

---

### Option 2: Run with Docker Compose

```bash
docker compose up --build
```

---

## Interactive API Documentation

Once the server is running, explore and test every endpoint via:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## Key API Endpoints

### Authentication & Profiles
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Register customer account & generate default wallet | No |
| `POST` | `/api/v1/auth/login` | Authenticate with email/password to receive JWT | No |
| `POST` | `/api/v1/auth/refresh` | Renew expired access token using refresh token | No |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile | Bearer Token |

### Wallets & Balances
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/wallets` | Create a new currency wallet (NGN, USD, EUR, GBP) | Bearer Token |
| `GET` | `/api/v1/wallets` | List all wallets owned by authenticated user | Bearer Token |
| `GET` | `/api/v1/wallets/{id}` | Get wallet balance and status | Bearer Token |
| `GET` | `/api/v1/wallets/{id}/statement` | Get full double-entry ledger statement | Bearer Token |

### Payments & Transfers
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/transactions/deposit` | Deposit funds into wallet (supports idempotency) | Bearer Token |
| `POST` | `/api/v1/transactions/withdraw` | Withdraw funds from wallet (supports idempotency) | Bearer Token |
| `POST` | `/api/v1/transactions/transfer` | Atomic transfer between wallets (with idempotency) | Bearer Token |
| `GET` | `/api/v1/transactions/{reference}` | Get transaction status & details by reference | Bearer Token |

### Administration & Auditing
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/admin/metrics` | Vault balances, total platform volume, user counts | Admin Bearer |
| `GET` | `/api/v1/admin/transactions` | Platform-wide audit logs across all users | Admin Bearer |
| `PATCH` | `/api/v1/admin/users/{id}/status` | Freeze or reinstate a user account | Admin Bearer |

---

## Example Usage with cURL

### 1. Register a new user
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "full_name": "Adekunle Olumide",
    "password": "Password123!"
  }'
```

### 2. Login to receive JWT Bearer Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "password": "Password123!"
  }'
```

### 3. Deposit funds into wallet
```bash
curl -X POST "http://localhost:8000/api/v1/transactions/deposit" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: deposit-txn-001" \
  -d '{
    "wallet_id": "<YOUR_WALLET_ID>",
    "amount": 100000.00,
    "description": "Initial account deposit"
  }'
```

### 4. Transfer funds to another user
```bash
curl -X POST "http://localhost:8000/api/v1/transactions/transfer" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: transfer-req-9901" \
  -d '{
    "source_wallet_id": "<YOUR_WALLET_ID>",
    "destination_wallet_id": "<RECIPIENT_WALLET_ID>",
    "amount": 25000.00,
    "description": "Invoice payment"
  }'
```

### 5. Fetch account statement (Double-Entry Audit)
```bash
curl -X GET "http://localhost:8000/api/v1/wallets/<YOUR_WALLET_ID>/statement" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

---

## Running Automated Tests

Run the full async test suite using `pytest`:

```bash
pytest
```

To run with verbose output and coverage:
```bash
pytest -v
```

---

## Pushing to GitHub

To publish this project to your GitHub profile:

1. Create a new empty repository on GitHub named **`payledger-api`** (or your preferred name).
2. Run the following commands in your terminal:

```bash
cd payledger-api
git init
git add .
git commit -m "feat: Initial commit for PayLedger API high-performance financial ledger"
git branch -M main
git remote add origin https://github.com/olumideadekunle/payledger-api.git
git push -u origin main
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
