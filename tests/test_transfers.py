import pytest
from httpx import AsyncClient


async def create_user_and_get_wallet(client: AsyncClient, email: str, name: str) -> tuple[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": name, "password": "Password123!"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    wallets_res = await client.get("/api/v1/wallets", headers=headers)
    wallet_id = wallets_res.json()[0]["id"]
    return token, wallet_id


@pytest.mark.asyncio
async def test_full_transfer_lifecycle(client: AsyncClient):
    # Setup Alice and Bob
    token_alice, wallet_alice = await create_user_and_get_wallet(client, "alice@example.com", "Alice Tester")
    token_bob, wallet_bob = await create_user_and_get_wallet(client, "bob@example.com", "Bob Receiver")

    headers_alice = {"Authorization": f"Bearer {token_alice}"}
    headers_bob = {"Authorization": f"Bearer {token_bob}"}

    # 1. Deposit 50,000 into Alice's wallet
    dep_res = await client.post(
        "/api/v1/transactions/deposit",
        json={"wallet_id": wallet_alice, "amount": 50000.00, "description": "Salary deposit"},
        headers=headers_alice,
    )
    assert dep_res.status_code == 201, dep_res.text
    dep_data = dep_res.json()
    assert dep_data["type"] == "deposit"
    assert dep_data["status"] == "completed"

    # Verify Alice's balance
    alice_wallet = (await client.get(f"/api/v1/wallets/{wallet_alice}", headers=headers_alice)).json()
    assert float(alice_wallet["balance"]) == 50000.00

    # 2. Overdraft rejection test: Attempting to send 60,000
    overdraft_res = await client.post(
        "/api/v1/transactions/transfer",
        json={
            "source_wallet_id": wallet_alice,
            "destination_wallet_id": wallet_bob,
            "amount": 60000.00,
            "description": "Overdraft attempt",
        },
        headers=headers_alice,
    )
    assert overdraft_res.status_code == 422
    assert "Insufficient funds" in overdraft_res.json()["detail"]

    # 3. Self-transfer rejection test
    self_res = await client.post(
        "/api/v1/transactions/transfer",
        json={
            "source_wallet_id": wallet_alice,
            "destination_wallet_id": wallet_alice,
            "amount": 1000.00,
        },
        headers=headers_alice,
    )
    assert self_res.status_code == 400
    assert "Self-transfers" in self_res.json()["detail"]

    # 4. Valid Transfer: Alice sends 15,000 to Bob
    tx_res = await client.post(
        "/api/v1/transactions/transfer",
        json={
            "source_wallet_id": wallet_alice,
            "destination_wallet_id": wallet_bob,
            "amount": 15000.00,
            "description": "Payment for freelance work",
        },
        headers=headers_alice,
    )
    assert tx_res.status_code == 201, tx_res.text
    tx_data = tx_res.json()
    assert tx_data["reference"].startswith("TRF_")

    # 5. Verify Balances after transfer
    alice_after = (await client.get(f"/api/v1/wallets/{wallet_alice}", headers=headers_alice)).json()
    bob_after = (await client.get(f"/api/v1/wallets/{wallet_bob}", headers=headers_bob)).json()

    assert float(alice_after["balance"]) == 35000.00
    assert float(bob_after["balance"]) == 15000.00

    # 6. Verify Ledger Statements and Double-Entry Records
    stmt_alice = (await client.get(f"/api/v1/wallets/{wallet_alice}/statement", headers=headers_alice)).json()
    assert float(stmt_alice["total_credits"]) == 50000.00
    assert float(stmt_alice["total_debits"]) == 15000.00
    assert float(stmt_alice["current_balance"]) == 35000.00
    assert stmt_alice["entry_count"] == 2  # 1 credit (deposit), 1 debit (transfer out)

    stmt_bob = (await client.get(f"/api/v1/wallets/{wallet_bob}/statement", headers=headers_bob)).json()
    assert float(stmt_bob["total_credits"]) == 15000.00
    assert float(stmt_bob["total_debits"]) == 0.00
    assert float(stmt_bob["current_balance"]) == 15000.00
    assert stmt_bob["entry_count"] == 1
