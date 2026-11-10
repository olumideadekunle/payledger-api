import pytest
from httpx import AsyncClient
from tests.test_transfers import create_user_and_get_wallet


@pytest.mark.asyncio
async def test_idempotent_transfer_prevents_double_charge(client: AsyncClient):
    token_alice, wallet_alice = await create_user_and_get_wallet(client, "alice_idem@example.com", "Alice Idem")
    token_bob, wallet_bob = await create_user_and_get_wallet(client, "bob_idem@example.com", "Bob Idem")

    headers_alice = {
        "Authorization": f"Bearer {token_alice}",
        "X-Idempotency-Key": "idemp-key-unique-998877",
    }

    # Fund Alice with 20,000
    await client.post(
        "/api/v1/transactions/deposit",
        json={"wallet_id": wallet_alice, "amount": 20000.00},
        headers={"Authorization": f"Bearer {token_alice}"},
    )

    transfer_payload = {
        "source_wallet_id": wallet_alice,
        "destination_wallet_id": wallet_bob,
        "amount": 5000.00,
        "description": "Idempotent payment",
    }

    # First Attempt
    first_res = await client.post(
        "/api/v1/transactions/transfer",
        json=transfer_payload,
        headers=headers_alice,
    )
    assert first_res.status_code == 201
    first_data = first_res.json()
    first_ref = first_data["reference"]

    # Second Attempt with identical key (e.g. network retry)
    second_res = await client.post(
        "/api/v1/transactions/transfer",
        json=transfer_payload,
        headers=headers_alice,
    )
    assert second_res.status_code == 201
    second_data = second_res.json()
    assert second_data["reference"] == first_ref

    # Verify Alice's balance was only debited once (20,000 - 5,000 = 15,000, NOT 10,000!)
    alice_wallet = (
        await client.get(
            f"/api/v1/wallets/{wallet_alice}",
            headers={"Authorization": f"Bearer {token_alice}"},
        )
    ).json()
    assert float(alice_wallet["balance"]) == 15000.00
