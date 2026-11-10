import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # 1. Register User
    payload = {
        "email": "olumide@example.com",
        "full_name": "Olumide Adekunle",
        "password": "Password123!",
    }
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["email"] == "olumide@example.com"
    assert data["full_name"] == "Olumide Adekunle"
    assert "id" in data

    # 2. Duplicate registration should be rejected
    dup_res = await client.post("/api/v1/auth/register", json=payload)
    assert dup_res.status_code == 409

    # 3. Login with credentials
    login_payload = {
        "email": "olumide@example.com",
        "password": "Password123!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200, login_res.text
    token_data = login_res.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    token = token_data["access_token"]

    # 4. Access protected profile route
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "olumide@example.com"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    payload = {
        "email": "nonexistent@example.com",
        "password": "WrongPassword!",
    }
    res = await client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 401
