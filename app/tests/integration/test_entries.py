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


async def test_employee_without_permission_forbidden(client):
    matricule, owner_token = await _register_and_login_owner(client)
    await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Un",
            "phone": "+224851111111",
            "password": "EmployeePass123!",
            "permissions": [],
        },
        headers=_auth_headers(owner_token),
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"matricule": matricule, "phone": "+224851111111", "password": "EmployeePass123!"},
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
