import pytest
from httpx import AsyncClient


async def get_auth_token_and_user(client: AsyncClient, email: str = "test@example.com") -> tuple[str, dict]:
    payload = {
        "email": email,
        "full_name": "Test Account",
        "password": "Password123!",
    }
    await client.post("/api/v1/auth/register", json=payload)
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    data = login_res.json()
    return data["access_token"], data["user"]


@pytest.mark.asyncio
async def test_wallet_creation_and_listing(client: AsyncClient):
    token, user = await get_auth_token_and_user(client, "walletuser@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # User already has default NGN wallet created during registration
    res = await client.get("/api/v1/wallets", headers=headers)
    assert res.status_code == 200
    wallets = res.json()
    assert len(wallets) == 1
    assert wallets[0]["currency"] == "NGN"
    ngn_wallet_id = wallets[0]["id"]

    # Create additional USD wallet
    usd_res = await client.post("/api/v1/wallets", json={"currency": "USD"}, headers=headers)
    assert usd_res.status_code == 201
    usd_data = usd_res.json()
    assert usd_data["currency"] == "USD"

    # Creating another USD wallet for same user should conflict
    dup_res = await client.post("/api/v1/wallets", json={"currency": "USD"}, headers=headers)
    assert dup_res.status_code == 409

    # Fetch statement for initial wallet
    stmt_res = await client.get(f"/api/v1/wallets/{ngn_wallet_id}/statement", headers=headers)
    assert stmt_res.status_code == 200
    stmt_data = stmt_res.json()
    assert stmt_data["wallet_id"] == ngn_wallet_id
    assert stmt_data["current_balance"] == "0.0000"
    assert stmt_data["entry_count"] == 0
