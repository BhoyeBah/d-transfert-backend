async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise Fournisseur",
        "company_phone": "+224890000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Fournisseur",
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


async def _create_wallet(client, token, code, currency="GNF", initial_balance="0"):
    response = await client.post(
        "/api/v1/wallets",
        json={
            "name": code,
            "code": code,
            "type": "cash",
            "currency": currency,
            "initial_balance": initial_balance,
        },
        headers=_auth_headers(token),
    )
    return response.json()["id"]


async def test_create_supplier_with_initial_balance(client):
    _, token = await _register_and_login_owner(client)
    response = await client.post(
        "/api/v1/suppliers",
        json={
            "name": "Fournisseur Liquidité",
            "code": "SUP1",
            "currency": "GNF",
            "initial_balance": "10000",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    assert response.json()["balance"] == "10000.00"


async def test_supplier_code_unique_per_company(client):
    _, token = await _register_and_login_owner(client)
    payload = {"name": "Fournisseur A", "code": "SUP1", "currency": "GNF"}
    await client.post("/api/v1/suppliers", json=payload, headers=_auth_headers(token))
    response = await client.post("/api/v1/suppliers", json=payload, headers=_auth_headers(token))
    assert response.status_code == 409


async def test_rebalance_debt_increases_wallet_decreases_supplier_balance(client):
    _, token = await _register_and_login_owner(client)
    wallet_id = await _create_wallet(client, token, "CASH")
    supplier_response = await client.post(
        "/api/v1/suppliers",
        json={"name": "Fournisseur", "code": "SUP1", "currency": "GNF"},
        headers=_auth_headers(token),
    )
    supplier_id = supplier_response.json()["id"]

    response = await client.post(
        f"/api/v1/suppliers/{supplier_id}/rebalance",
        json={"type": "debt", "amount": "50000", "wallet_id": wallet_id},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["balance_after"] == "-50000.00"

    wallet = await client.get(f"/api/v1/wallets/{wallet_id}", headers=_auth_headers(token))
    assert wallet.json()["balance"] == "50000.00"

    supplier = await client.get(f"/api/v1/suppliers/{supplier_id}", headers=_auth_headers(token))
    assert supplier.json()["balance"] == "-50000.00"


async def test_rebalance_payment_decreases_wallet_increases_supplier_balance(client):
    _, token = await _register_and_login_owner(client)
    wallet_id = await _create_wallet(client, token, "CASH", initial_balance="100000")
    supplier_response = await client.post(
        "/api/v1/suppliers",
        json={
            "name": "Fournisseur",
            "code": "SUP1",
            "currency": "GNF",
            "initial_balance": "-50000",
        },
        headers=_auth_headers(token),
    )
    supplier_id = supplier_response.json()["id"]

    response = await client.post(
        f"/api/v1/suppliers/{supplier_id}/rebalance",
        json={"type": "payment", "amount": "50000", "wallet_id": wallet_id},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["balance_after"] == "0.00"

    wallet = await client.get(f"/api/v1/wallets/{wallet_id}", headers=_auth_headers(token))
    assert wallet.json()["balance"] == "50000.00"


async def test_supplier_currency_mismatch_rejected(client):
    _, token = await _register_and_login_owner(client)
    wallet_id = await _create_wallet(client, token, "CASH", currency="XOF")
    supplier_response = await client.post(
        "/api/v1/suppliers",
        json={"name": "Fournisseur", "code": "SUP1", "currency": "GNF"},
        headers=_auth_headers(token),
    )
    supplier_id = supplier_response.json()["id"]

    response = await client.post(
        f"/api/v1/suppliers/{supplier_id}/rebalance",
        json={"type": "debt", "amount": "1000", "wallet_id": wallet_id},
        headers=_auth_headers(token),
    )
    assert response.status_code == 409


async def test_payment_rebalance_insufficient_wallet_balance_rejected(client):
    _, token = await _register_and_login_owner(client)
    wallet_id = await _create_wallet(client, token, "CASH", initial_balance="10000")
    supplier_response = await client.post(
        "/api/v1/suppliers",
        json={"name": "Fournisseur", "code": "SUP1", "currency": "GNF"},
        headers=_auth_headers(token),
    )
    supplier_id = supplier_response.json()["id"]

    response = await client.post(
        f"/api/v1/suppliers/{supplier_id}/rebalance",
        json={"type": "payment", "amount": "50000", "wallet_id": wallet_id},
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    assert "Solde insuffisant" in response.json()["detail"]


async def test_supplier_isolated_between_companies(client):
    _, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224890000010"
    )
    await client.post(
        "/api/v1/suppliers",
        json={"name": "Fournisseur A", "code": "SUP1", "currency": "GNF"},
        headers=_auth_headers(token_a),
    )

    _, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224890000011"
    )
    response = await client.get("/api/v1/suppliers", headers=_auth_headers(token_b))
    assert response.status_code == 200
    assert response.json() == []


async def test_suppliers_page_search_sort_pagination(client):
    _, token = await _register_and_login_owner(client)
    for code, name in [("SUPA", "Alpha Fournisseur"), ("SUPB", "Beta Fournisseur"), ("SUPC", "Gamma Fournisseur")]:
        await client.post(
            "/api/v1/suppliers",
            json={"name": name, "code": code, "currency": "GNF"},
            headers=_auth_headers(token),
        )

    response = await client.get(
        "/api/v1/suppliers/page",
        params={"page": 1, "page_size": 2, "sort_by": "name", "sort_dir": "asc"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert [item["name"] for item in body["items"]] == ["Alpha Fournisseur", "Beta Fournisseur"]

    response = await client.get(
        "/api/v1/suppliers/page", params={"search": "gamma"}, headers=_auth_headers(token)
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["code"] == "SUPC"


async def test_employee_without_permission_forbidden(client):
    _, token = await _register_and_login_owner(client)
    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé",
            "phone": "+224891111111",
            "password": "EmployeePass123!",
            "permissions": [],
        },
        headers=_auth_headers(token),
    )
    employee_matricule = create_response.json()["matricule"]
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"matricule": employee_matricule, "password": "EmployeePass123!"},
    )
    employee_token = login_response.json()["access_token"]

    response = await client.get("/api/v1/suppliers", headers=_auth_headers(employee_token))
    assert response.status_code == 403
