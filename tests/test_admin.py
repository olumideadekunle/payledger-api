import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_metrics_and_user_status(client: AsyncClient):
    # Register first user (automatically assigned ADMIN role)
    admin_payload = {
        "email": "admin@payledger.internal",
        "full_name": "System Administrator",
        "password": "AdminPassword123!",
    }
    await client.post("/api/v1/auth/register", json=admin_payload)
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_payload["email"], "password": admin_payload["password"]},
    )
    admin_token = login_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Register a regular customer
    cust_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "customer_regular@example.com", "full_name": "Regular Customer", "password": "Password123!"},
    )
    cust_id = cust_res.json()["id"]

    # 1. Fetch Admin Metrics
    metrics_res = await client.get("/api/v1/admin/metrics", headers=admin_headers)
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["total_users"] == 2
    assert "vault_balances" in metrics

    # 2. Freeze Customer Account
    freeze_res = await client.patch(
        f"/api/v1/admin/users/{cust_id}/status?new_status=suspended",
        headers=admin_headers,
    )
    assert freeze_res.status_code == 200
    assert freeze_res.json()["status"] == "suspended"

    # 3. Verify Frozen Customer Cannot Login
    cust_login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "customer_regular@example.com", "password": "Password123!"},
    )
    assert cust_login_res.status_code == 403
