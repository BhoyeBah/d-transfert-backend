async def _register_and_login_owner(client, **overrides) -> str:
    payload = {
        "company_name": "Entreprise Nationale",
        "company_phone": "+224800000001",
        "address": "Conakry",
        "default_currency": "XOF",
        "owner_full_name": "Owner National",
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


async def _create_wallet(client, token, code, initial_balance="0", currency="XOF"):
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


async def test_deposit_balances_two_wallets(client):
    owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH", initial_balance="20000")
    wave_id = await _create_wallet(client, owner_token, "WAVE", initial_balance="0")

    response = await client.post(
        "/api/v1/national-operations/deposits",
        json={
            "note": "Dépôt cash vers Wave",
            "lines": [
                {"wallet_id": cash_id, "amount_in": "0", "amount_out": "10000", "currency": "XOF"},
                {"wallet_id": wave_id, "amount_in": "10000", "amount_out": "0", "currency": "XOF"},
            ],
        },
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "validated"
    assert len(body["lines"]) == 2

    cash_wallet = await client.get(f"/api/v1/wallets/{cash_id}", headers=_auth_headers(owner_token))
    wave_wallet = await client.get(f"/api/v1/wallets/{wave_id}", headers=_auth_headers(owner_token))
    assert cash_wallet.json()["balance"] == "10000.00"
    assert wave_wallet.json()["balance"] == "10000.00"


async def test_withdrawal_no_fee_balances_two_wallets(client):
    owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH", initial_balance="0")
    wave_id = await _create_wallet(client, owner_token, "WAVE", initial_balance="20000")

    response = await client.post(
        "/api/v1/national-operations/withdrawals",
        json={
            "note": "Retrait client",
            "lines": [
                {"wallet_id": wave_id, "amount_in": "0", "amount_out": "10000", "currency": "XOF"},
                {"wallet_id": cash_id, "amount_in": "10000", "amount_out": "0", "currency": "XOF"},
            ],
        },
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "withdrawal"
    assert body["status"] == "validated"
    # No fee field exists anywhere on the operation or its lines: the customer-facing amount
    # withdrawn from Wave (10000) exactly equals the cash handed out (10000).
    for line in body["lines"]:
        assert set(line.keys()) >= {"amount_in", "amount_out", "currency"}
        assert "fee_amount" not in line

    cash_wallet = await client.get(f"/api/v1/wallets/{cash_id}", headers=_auth_headers(owner_token))
    wave_wallet = await client.get(f"/api/v1/wallets/{wave_id}", headers=_auth_headers(owner_token))
    assert cash_wallet.json()["balance"] == "10000.00"
    assert wave_wallet.json()["balance"] == "10000.00"


async def test_multi_wallet_rebalance(client):
    owner_token = await _register_and_login_owner(client)
    wave_id = await _create_wallet(client, owner_token, "WAVE")
    cash_id = await _create_wallet(client, owner_token, "CASH", initial_balance="100000")
    om_id = await _create_wallet(client, owner_token, "OM", initial_balance="100000")

    response = await client.post(
        "/api/v1/national-operations/rebalances",
        json={
            "lines": [
                {"wallet_id": wave_id, "amount_in": "50000", "amount_out": "0", "currency": "XOF"},
                {"wallet_id": cash_id, "amount_in": "0", "amount_out": "30000", "currency": "XOF"},
                {"wallet_id": om_id, "amount_in": "0", "amount_out": "20000", "currency": "XOF"},
            ]
        },
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 201

    wave_wallet = await client.get(f"/api/v1/wallets/{wave_id}", headers=_auth_headers(owner_token))
    cash_wallet = await client.get(f"/api/v1/wallets/{cash_id}", headers=_auth_headers(owner_token))
    om_wallet = await client.get(f"/api/v1/wallets/{om_id}", headers=_auth_headers(owner_token))
    assert wave_wallet.json()["balance"] == "50000.00"
    assert cash_wallet.json()["balance"] == "70000.00"
    assert om_wallet.json()["balance"] == "80000.00"


async def test_unbalanced_operation_rejected(client):
    owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH", initial_balance="100000")
    wave_id = await _create_wallet(client, owner_token, "WAVE")

    response = await client.post(
        "/api/v1/national-operations/exchanges",
        json={
            "lines": [
                {"wallet_id": cash_id, "amount_in": "0", "amount_out": "10000", "currency": "XOF"},
                {"wallet_id": wave_id, "amount_in": "9000", "amount_out": "0", "currency": "XOF"},
            ]
        },
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 422


async def test_insufficient_balance_rejected(client):
    owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH", initial_balance="5000")
    wave_id = await _create_wallet(client, owner_token, "WAVE")

    response = await client.post(
        "/api/v1/national-operations/withdrawals",
        json={
            "lines": [
                {"wallet_id": wave_id, "amount_in": "10000", "amount_out": "0", "currency": "XOF"},
                {"wallet_id": cash_id, "amount_in": "0", "amount_out": "10000", "currency": "XOF"},
            ]
        },
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 422
    assert "Solde insuffisant" in response.json()["detail"]


async def test_currency_mismatch_rejected(client):
    owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH", initial_balance="100000", currency="XOF")
    wave_id = await _create_wallet(client, owner_token, "WAVE", currency="GNF")

    response = await client.post(
        "/api/v1/national-operations/exchanges",
        json={
            "lines": [
                {"wallet_id": cash_id, "amount_in": "0", "amount_out": "10000", "currency": "XOF"},
                {"wallet_id": wave_id, "amount_in": "10000", "amount_out": "0", "currency": "XOF"},
            ]
        },
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 422


async def test_cancel_operation_creates_mirrored_reversal(client):
    owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH", initial_balance="100000")
    wave_id = await _create_wallet(client, owner_token, "WAVE")

    create_response = await client.post(
        "/api/v1/national-operations/exchanges",
        json={
            "lines": [
                {"wallet_id": cash_id, "amount_in": "0", "amount_out": "10000", "currency": "XOF"},
                {"wallet_id": wave_id, "amount_in": "10000", "amount_out": "0", "currency": "XOF"},
            ]
        },
        headers=_auth_headers(owner_token),
    )
    operation_id = create_response.json()["id"]

    cancel_response = await client.post(
        f"/api/v1/national-operations/{operation_id}/cancel", headers=_auth_headers(owner_token)
    )
    assert cancel_response.status_code == 200
    reversal = cancel_response.json()
    assert reversal["reversal_of_id"] == operation_id

    original_response = await client.get(
        f"/api/v1/national-operations/{operation_id}", headers=_auth_headers(owner_token)
    )
    assert original_response.json()["status"] == "cancelled"

    cash_wallet = await client.get(f"/api/v1/wallets/{cash_id}", headers=_auth_headers(owner_token))
    wave_wallet = await client.get(f"/api/v1/wallets/{wave_id}", headers=_auth_headers(owner_token))
    assert cash_wallet.json()["balance"] == "100000.00"
    assert wave_wallet.json()["balance"] == "0.00"


async def test_cancel_already_cancelled_operation_rejected(client):
    owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH", initial_balance="100000")
    wave_id = await _create_wallet(client, owner_token, "WAVE")

    create_response = await client.post(
        "/api/v1/national-operations/exchanges",
        json={
            "lines": [
                {"wallet_id": cash_id, "amount_in": "0", "amount_out": "10000", "currency": "XOF"},
                {"wallet_id": wave_id, "amount_in": "10000", "amount_out": "0", "currency": "XOF"},
            ]
        },
        headers=_auth_headers(owner_token),
    )
    operation_id = create_response.json()["id"]
    await client.post(
        f"/api/v1/national-operations/{operation_id}/cancel", headers=_auth_headers(owner_token)
    )

    second_cancel = await client.post(
        f"/api/v1/national-operations/{operation_id}/cancel", headers=_auth_headers(owner_token)
    )
    assert second_cancel.status_code == 409


async def test_wallet_from_other_company_rejected(client):
    owner_a_token = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224800000020"
    )
    cash_a_id = await _create_wallet(client, owner_a_token, "CASH", initial_balance="100000")

    owner_b_token = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224800000021"
    )
    wave_b_id = await _create_wallet(client, owner_b_token, "WAVE")

    response = await client.post(
        "/api/v1/national-operations/exchanges",
        json={
            "lines": [
                {"wallet_id": cash_a_id, "amount_in": "0", "amount_out": "10000", "currency": "XOF"},
                {"wallet_id": wave_b_id, "amount_in": "10000", "amount_out": "0", "currency": "XOF"},
            ]
        },
        headers=_auth_headers(owner_b_token),
    )
    assert response.status_code == 404


async def test_employee_without_permission_forbidden(client):
    owner_token = await _register_and_login_owner(client)
    matricule_response = await client.get("/api/v1/companies/me", headers=_auth_headers(owner_token))
    matricule = matricule_response.json()["registration_code"]

    await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Un",
            "phone": "+224811111111",
            "password": "EmployeePass123!",
            "permissions": [],
        },
        headers=_auth_headers(owner_token),
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"matricule": matricule, "phone": "+224811111111", "password": "EmployeePass123!"},
    )
    employee_token = login_response.json()["access_token"]

    response = await client.get(
        "/api/v1/national-operations", headers=_auth_headers(employee_token)
    )
    assert response.status_code == 403
