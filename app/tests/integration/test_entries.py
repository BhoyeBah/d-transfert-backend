async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise Entrées",
        "company_phone": "+224850000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Entrées",
        "password": "SuperSecret123!",
        "password_confirmation": "SuperSecret123!",
    }
    payload.update(overrides)
    register_response = await client.post("/api/v1/auth/register", json=payload)
    matricule = register_response.json()["registration_code"]
    login_response = await client.post(
        "/api/v1/auth/login", json={"matricule": matricule, "password": payload["password"]}
    )
    return matricule, login_response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_wallet(client, token, code, currency="GNF"):
    response = await client.post(
        "/api/v1/wallets",
        json={"name": code, "code": code, "type": "cash", "currency": currency},
        headers=_auth_headers(token),
    )
    return response.json()["id"]


async def test_create_entry_multi_wallet(client):
    _, owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH")
    wave_id = await _create_wallet(client, owner_token, "WAVE")

    response = await client.post(
        "/api/v1/entries",
        json={
            "client_name": "Client A",
            "lines": [
                {"wallet_id": cash_id, "amount": "60000", "currency": "GNF"},
                {"wallet_id": wave_id, "amount": "25000", "currency": "GNF"},
            ],
        },
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "unallocated"
    assert body["available_by_currency"] == {"GNF": "85000.00"}

    cash_wallet = await client.get(f"/api/v1/wallets/{cash_id}", headers=_auth_headers(owner_token))
    wave_wallet = await client.get(f"/api/v1/wallets/{wave_id}", headers=_auth_headers(owner_token))
    assert cash_wallet.json()["balance"] == "60000.00"
    assert wave_wallet.json()["balance"] == "25000.00"


async def test_entry_currency_mismatch_rejected(client):
    _, owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH", currency="XOF")

    response = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "1000", "currency": "GNF"}]},
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 422


async def test_entry_wallet_from_other_company_rejected(client):
    _, owner_a_token = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224850000010"
    )
    _, owner_b_token = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224850000011"
    )
    wallet_b_id = await _create_wallet(client, owner_b_token, "CASH")

    response = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": wallet_b_id, "amount": "1000", "currency": "GNF"}]},
        headers=_auth_headers(owner_a_token),
    )
    assert response.status_code == 404


async def test_merge_entries_aggregates_lines_without_new_wallet_movement(client):
    _, owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH")

    entry_1 = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "10000", "currency": "GNF"}]},
        headers=_auth_headers(owner_token),
    )
    entry_2 = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "5000", "currency": "GNF"}]},
        headers=_auth_headers(owner_token),
    )
    entry_1_id = entry_1.json()["id"]
    entry_2_id = entry_2.json()["id"]

    merge_response = await client.post(
        "/api/v1/entries/merge",
        json={"entry_ids": [entry_1_id, entry_2_id], "note": "Fusion client A"},
        headers=_auth_headers(owner_token),
    )
    assert merge_response.status_code == 201
    merged = merge_response.json()
    assert merged["available_by_currency"] == {"GNF": "15000.00"}
    assert len(merged["lines"]) == 1
    assert merged["lines"][0]["amount"] == "15000.00"

    cash_wallet = await client.get(f"/api/v1/wallets/{cash_id}", headers=_auth_headers(owner_token))
    assert cash_wallet.json()["balance"] == "15000.00"

    original_1 = await client.get(f"/api/v1/entries/{entry_1_id}", headers=_auth_headers(owner_token))
    original_2 = await client.get(f"/api/v1/entries/{entry_2_id}", headers=_auth_headers(owner_token))
    assert original_1.json()["merged_into_id"] == merged["id"]
    assert original_2.json()["merged_into_id"] == merged["id"]


async def test_merge_rejects_already_merged_entry(client):
    _, owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH")

    entry_1 = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "10000", "currency": "GNF"}]},
        headers=_auth_headers(owner_token),
    )
    entry_2 = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "5000", "currency": "GNF"}]},
        headers=_auth_headers(owner_token),
    )
    entry_3 = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "2000", "currency": "GNF"}]},
        headers=_auth_headers(owner_token),
    )
    entry_1_id = entry_1.json()["id"]
    entry_2_id = entry_2.json()["id"]
    entry_3_id = entry_3.json()["id"]

    await client.post(
        "/api/v1/entries/merge",
        json={"entry_ids": [entry_1_id, entry_2_id]},
        headers=_auth_headers(owner_token),
    )

    response = await client.post(
        "/api/v1/entries/merge",
        json={"entry_ids": [entry_1_id, entry_3_id]},
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 409


async def test_cancel_entry_reverses_wallet_balance(client):
    _, owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH")

    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "10000", "currency": "GNF"}]},
        headers=_auth_headers(owner_token),
    )
    entry_id = entry.json()["id"]

    cancel_response = await client.post(
        f"/api/v1/entries/{entry_id}/cancel", headers=_auth_headers(owner_token)
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    cash_wallet = await client.get(f"/api/v1/wallets/{cash_id}", headers=_auth_headers(owner_token))
    assert cash_wallet.json()["balance"] == "0.00"

    second_cancel = await client.post(
        f"/api/v1/entries/{entry_id}/cancel", headers=_auth_headers(owner_token)
    )
    assert second_cancel.status_code == 409


async def test_merge_partially_allocated_entry_carries_only_remaining_amount(client):
    _, owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH")

    other_token = (
        await _register_and_login_owner(
            client, company_name="Entreprise Collab Fusion", company_phone="+224850000030"
        )
    )[1]
    collab_response = await client.post(
        "/api/v1/collaborations",
        json={
            "target_matricule": (
                await client.get("/api/v1/companies/me", headers=_auth_headers(owner_token))
            ).json()["registration_code"],
            "currency": "GNF",
            "initial_rate": "1",
        },
        headers=_auth_headers(other_token),
    )
    collaboration_id = collab_response.json()["id"]
    await client.post(
        f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(owner_token)
    )

    entry_1 = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "10000", "currency": "GNF"}]},
        headers=_auth_headers(owner_token),
    )
    entry_2 = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "5000", "currency": "GNF"}]},
        headers=_auth_headers(owner_token),
    )
    entry_1_id = entry_1.json()["id"]
    entry_2_id = entry_2.json()["id"]

    # Consume 4000 of entry_1's 10000 via a transfer, leaving only 6000 available.
    await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_1_id,
            "amount": "4000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000001",
            "send_mode": "cash",
        },
        headers=_auth_headers(owner_token),
    )
    entry_1_after = await client.get(f"/api/v1/entries/{entry_1_id}", headers=_auth_headers(owner_token))
    assert entry_1_after.json()["status"] == "partially_allocated"
    assert entry_1_after.json()["available_by_currency"] == {"GNF": "6000.00"}

    merge_response = await client.post(
        "/api/v1/entries/merge",
        json={"entry_ids": [entry_1_id, entry_2_id]},
        headers=_auth_headers(owner_token),
    )
    assert merge_response.status_code == 201
    merged = merge_response.json()
    # Only the remaining 6000 (not the original 10000) must be carried forward, otherwise the
    # 4000 already allocated to the transfer would be double-spent via the merged entry.
    assert merged["available_by_currency"] == {"GNF": "11000.00"}

    # The source entry that was partially allocated and then merged away must no longer be
    # directly usable to fund a new transfer/payment (its money now lives in the merged entry).
    reuse_attempt = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_1_id,
            "amount": "1000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000002",
            "send_mode": "cash",
        },
        headers=_auth_headers(owner_token),
    )
    assert reuse_attempt.status_code == 409


async def test_cancel_entry_with_live_allocation_rejected(client):
    _, owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH")

    other_token = (
        await _register_and_login_owner(
            client, company_name="Entreprise Collab Cancel", company_phone="+224850000031"
        )
    )[1]
    collab_response = await client.post(
        "/api/v1/collaborations",
        json={
            "target_matricule": (
                await client.get("/api/v1/companies/me", headers=_auth_headers(owner_token))
            ).json()["registration_code"],
            "currency": "GNF",
            "initial_rate": "1",
        },
        headers=_auth_headers(other_token),
    )
    collaboration_id = collab_response.json()["id"]
    await client.post(
        f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(owner_token)
    )

    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "10000", "currency": "GNF"}]},
        headers=_auth_headers(owner_token),
    )
    entry_id = entry.json()["id"]

    await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "amount": "4000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000003",
            "send_mode": "cash",
        },
        headers=_auth_headers(owner_token),
    )

    cancel_response = await client.post(
        f"/api/v1/entries/{entry_id}/cancel", headers=_auth_headers(owner_token)
    )
    assert cancel_response.status_code == 409

    cash_wallet = await client.get(f"/api/v1/wallets/{cash_id}", headers=_auth_headers(owner_token))
    assert cash_wallet.json()["balance"] == "10000.00"


async def test_cancel_merged_entry_rejected(client):
    _, owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH")

    entry_1 = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "10000", "currency": "GNF"}]},
        headers=_auth_headers(owner_token),
    )
    entry_2 = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "5000", "currency": "GNF"}]},
        headers=_auth_headers(owner_token),
    )
    entry_1_id = entry_1.json()["id"]
    entry_2_id = entry_2.json()["id"]

    await client.post(
        "/api/v1/entries/merge",
        json={"entry_ids": [entry_1_id, entry_2_id]},
        headers=_auth_headers(owner_token),
    )

    cancel_response = await client.post(
        f"/api/v1/entries/{entry_1_id}/cancel", headers=_auth_headers(owner_token)
    )
    assert cancel_response.status_code == 409


async def test_employee_without_permission_forbidden(client):
    _, owner_token = await _register_and_login_owner(client)
    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Un",
            "phone": "+224851111111",
            "password": "EmployeePass123!",
            "permissions": [],
        },
        headers=_auth_headers(owner_token),
    )
    employee_matricule = create_response.json()["matricule"]
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"matricule": employee_matricule, "password": "EmployeePass123!"},
    )
    employee_token = login_response.json()["access_token"]

    response = await client.get("/api/v1/entries", headers=_auth_headers(employee_token))
    assert response.status_code == 403


async def test_entries_isolated_between_companies(client):
    _, owner_a_token = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224850000020"
    )
    cash_a_id = await _create_wallet(client, owner_a_token, "CASH")
    await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_a_id, "amount": "10000", "currency": "GNF"}]},
        headers=_auth_headers(owner_a_token),
    )

    _, owner_b_token = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224850000021"
    )
    response = await client.get("/api/v1/entries", headers=_auth_headers(owner_b_token))
    assert response.status_code == 200
    assert response.json() == []


async def test_entries_page_search_sort_pagination(client):
    _, owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH")

    for client_name in ["Alice", "Bob", "Charlie"]:
        await client.post(
            "/api/v1/entries",
            json={
                "client_name": client_name,
                "lines": [{"wallet_id": cash_id, "amount": "1000", "currency": "GNF"}],
            },
            headers=_auth_headers(owner_token),
        )

    response = await client.get(
        "/api/v1/entries/page",
        params={"page": 1, "page_size": 2, "sort_by": "reference", "sort_dir": "asc"},
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2

    response = await client.get(
        "/api/v1/entries/page", params={"search": "bob"}, headers=_auth_headers(owner_token)
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["client_name"] == "Bob"
