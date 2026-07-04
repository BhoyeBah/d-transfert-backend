async def _register_and_login_owner(client, **overrides) -> str:
    payload = {
        "company_name": "Entreprise Wallet",
        "company_phone": "+224700000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Wallet",
        "password": "SuperSecret123!",
        "password_confirmation": "SuperSecret123!",
    }
    payload.update(overrides)
    register_response = await client.post("/api/v1/auth/register", json=payload)
    matricule = register_response.json()["registration_code"]
    login_response = await client.post(
        "/api/v1/auth/login", json={"matricule": matricule, "password": payload["password"]}
    )
    return login_response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_create_wallet_with_initial_balance_generates_movement(client):
    owner_token = await _register_and_login_owner(client)

    response = await client.post(
        "/api/v1/wallets",
        json={
            "name": "Caisse Cash",
            "code": "CASH",
            "type": "cash",
            "currency": "GNF",
            "initial_balance": "10000",
        },
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["balance"] == "10000.00"
    wallet_id = body["id"]

    movements_response = await client.get(
        f"/api/v1/wallets/{wallet_id}/movements", headers=_auth_headers(owner_token)
    )
    assert movements_response.status_code == 200
    movements = movements_response.json()
    assert len(movements) == 1
    assert movements[0]["direction"] == "in"
    assert movements[0]["amount"] == "10000.00"
    assert movements[0]["balance_before"] == "0.00"
    assert movements[0]["balance_after"] == "10000.00"
    assert movements[0]["source_type"] == "wallet_initial"


async def test_wallet_code_unique_per_company(client):
    owner_token = await _register_and_login_owner(client)
    payload = {"name": "Caisse Cash", "code": "CASH", "type": "cash", "currency": "GNF"}

    await client.post("/api/v1/wallets", json=payload, headers=_auth_headers(owner_token))
    response = await client.post("/api/v1/wallets", json=payload, headers=_auth_headers(owner_token))
    assert response.status_code == 409


async def test_wallet_list_isolated_between_companies(client):
    owner_a_token = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224700000010"
    )
    await client.post(
        "/api/v1/wallets",
        json={"name": "Caisse A", "code": "CASH", "type": "cash", "currency": "GNF"},
        headers=_auth_headers(owner_a_token),
    )

    owner_b_token = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224700000011"
    )
    response = await client.get("/api/v1/wallets", headers=_auth_headers(owner_b_token))
    assert response.status_code == 200
    assert response.json() == []


async def test_update_and_deactivate_wallet(client):
    owner_token = await _register_and_login_owner(client)
    create_response = await client.post(
        "/api/v1/wallets",
        json={"name": "Caisse Cash", "code": "CASH", "type": "cash", "currency": "GNF"},
        headers=_auth_headers(owner_token),
    )
    wallet_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/wallets/{wallet_id}",
        json={"description": "Caisse principale"},
        headers=_auth_headers(owner_token),
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Caisse principale"

    status_response = await client.patch(
        f"/api/v1/wallets/{wallet_id}/status",
        json={"status": "inactive"},
        headers=_auth_headers(owner_token),
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "inactive"


async def test_employee_without_wallet_permission_forbidden(client):
    owner_token = await _register_and_login_owner(client)
    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Un",
            "phone": "+224711111111",
            "password": "EmployeePass123!",
            "permissions": [],
        },
        headers=_auth_headers(owner_token),
    )
    employee_matricule = create_response.json()["matricule"]
    login_response = await client.post(
        "/api/v1/auth/login", json={"matricule": employee_matricule, "password": "EmployeePass123!"}
    )
    employee_token = login_response.json()["access_token"]

    response = await client.get("/api/v1/wallets", headers=_auth_headers(employee_token))
    assert response.status_code == 403
