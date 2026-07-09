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


async def test_same_wallet_on_two_lines_rejected(client):
    owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH", initial_balance="100000")

    response = await client.post(
        "/api/v1/national-operations/deposits",
        json={
            "lines": [
                {"wallet_id": cash_id, "amount_in": "0", "amount_out": "10000", "currency": "XOF"},
                {"wallet_id": cash_id, "amount_in": "10000", "amount_out": "0", "currency": "XOF"},
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


async def test_exchange_between_different_currencies_with_rate(client):
    owner_token = await _register_and_login_owner(client)
    xof_id = await _create_wallet(client, owner_token, "CASH-XOF", initial_balance="100000", currency="XOF")
    gnf_id = await _create_wallet(client, owner_token, "CASH-GNF", initial_balance="0", currency="GNF")

    response = await client.post(
        "/api/v1/national-operations/exchanges",
        json={
            "exchange_rate": "17.5",
            "lines": [
                {"wallet_id": xof_id, "amount_in": "0", "amount_out": "1000", "currency": "XOF"},
                {"wallet_id": gnf_id, "amount_in": "17500", "amount_out": "0", "currency": "GNF"},
            ],
        },
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["exchange_rate"] == "17.5"

    xof_wallet = await client.get(f"/api/v1/wallets/{xof_id}", headers=_auth_headers(owner_token))
    gnf_wallet = await client.get(f"/api/v1/wallets/{gnf_id}", headers=_auth_headers(owner_token))
    assert xof_wallet.json()["balance"] == "99000.00"
    assert gnf_wallet.json()["balance"] == "17500.00"


async def test_exchange_missing_rate_for_multi_currency_rejected(client):
    owner_token = await _register_and_login_owner(client)
    xof_id = await _create_wallet(client, owner_token, "CASH-XOF", initial_balance="100000", currency="XOF")
    gnf_id = await _create_wallet(client, owner_token, "CASH-GNF", initial_balance="0", currency="GNF")

    response = await client.post(
        "/api/v1/national-operations/exchanges",
        json={
            "lines": [
                {"wallet_id": xof_id, "amount_in": "0", "amount_out": "1000", "currency": "XOF"},
                {"wallet_id": gnf_id, "amount_in": "17500", "amount_out": "0", "currency": "GNF"},
            ],
        },
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 422


async def test_exchange_rate_inconsistent_with_amounts_rejected(client):
    owner_token = await _register_and_login_owner(client)
    xof_id = await _create_wallet(client, owner_token, "CASH-XOF", initial_balance="100000", currency="XOF")
    gnf_id = await _create_wallet(client, owner_token, "CASH-GNF", initial_balance="0", currency="GNF")

    response = await client.post(
        "/api/v1/national-operations/exchanges",
        json={
            "exchange_rate": "17.5",
            "lines": [
                {"wallet_id": xof_id, "amount_in": "0", "amount_out": "1000", "currency": "XOF"},
                {"wallet_id": gnf_id, "amount_in": "10000", "amount_out": "0", "currency": "GNF"},
            ],
        },
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 422


async def test_cancel_exchange_reversal_mirrors_rate(client):
    owner_token = await _register_and_login_owner(client)
    xof_id = await _create_wallet(client, owner_token, "CASH-XOF", initial_balance="100000", currency="XOF")
    gnf_id = await _create_wallet(client, owner_token, "CASH-GNF", initial_balance="0", currency="GNF")

    create_response = await client.post(
        "/api/v1/national-operations/exchanges",
        json={
            "exchange_rate": "17.5",
            "lines": [
                {"wallet_id": xof_id, "amount_in": "0", "amount_out": "1000", "currency": "XOF"},
                {"wallet_id": gnf_id, "amount_in": "17500", "amount_out": "0", "currency": "GNF"},
            ],
        },
        headers=_auth_headers(owner_token),
    )
    operation_id = create_response.json()["id"]

    cancel_response = await client.post(
        f"/api/v1/national-operations/{operation_id}/cancel", headers=_auth_headers(owner_token)
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["exchange_rate"] == "17.500000"

    xof_wallet = await client.get(f"/api/v1/wallets/{xof_id}", headers=_auth_headers(owner_token))
    gnf_wallet = await client.get(f"/api/v1/wallets/{gnf_id}", headers=_auth_headers(owner_token))
    assert xof_wallet.json()["balance"] == "100000.00"
    assert gnf_wallet.json()["balance"] == "0.00"


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
    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Un",
            "phone": "+224811111111",
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

    response = await client.get(
        "/api/v1/national-operations", headers=_auth_headers(employee_token)
    )
    assert response.status_code == 403


async def test_reference_is_daily_sequential_per_company(client):
    from datetime import date

    owner_token = await _register_and_login_owner(client)
    cash_id = await _create_wallet(client, owner_token, "CASH", initial_balance="20000")
    wave_id = await _create_wallet(client, owner_token, "WAVE", initial_balance="0")

    today_prefix = f"OP-{date.today():%d-%m-%y}-"
    references = []
    for _ in range(2):
        response = await client.post(
            "/api/v1/national-operations/deposits",
            json={
                "lines": [
                    {"wallet_id": cash_id, "amount_in": "0", "amount_out": "1000", "currency": "XOF"},
                    {"wallet_id": wave_id, "amount_in": "1000", "amount_out": "0", "currency": "XOF"},
                ],
            },
            headers=_auth_headers(owner_token),
        )
        assert response.status_code == 201
        references.append(response.json()["reference"])

    assert references[0] == f"{today_prefix}0001"
    assert references[1] == f"{today_prefix}0002"


async def test_reference_sequence_is_isolated_per_company(client):
    from datetime import date

    owner_a_token = await _register_and_login_owner(
        client, company_name="Entreprise A Ref", company_phone="+224800000101"
    )
    owner_b_token = await _register_and_login_owner(
        client, company_name="Entreprise B Ref", company_phone="+224800000102"
    )
    cash_a_id = await _create_wallet(client, owner_a_token, "CASH", initial_balance="20000")
    wave_a_id = await _create_wallet(client, owner_a_token, "WAVE", initial_balance="0")
    cash_b_id = await _create_wallet(client, owner_b_token, "CASH", initial_balance="20000")
    wave_b_id = await _create_wallet(client, owner_b_token, "WAVE", initial_balance="0")

    today_prefix = f"OP-{date.today():%d-%m-%y}-"

    response_a = await client.post(
        "/api/v1/national-operations/deposits",
        json={
            "lines": [
                {"wallet_id": cash_a_id, "amount_in": "0", "amount_out": "1000", "currency": "XOF"},
                {"wallet_id": wave_a_id, "amount_in": "1000", "amount_out": "0", "currency": "XOF"},
            ],
        },
        headers=_auth_headers(owner_a_token),
    )
    response_b = await client.post(
        "/api/v1/national-operations/deposits",
        json={
            "lines": [
                {"wallet_id": cash_b_id, "amount_in": "0", "amount_out": "1000", "currency": "XOF"},
                {"wallet_id": wave_b_id, "amount_in": "1000", "amount_out": "0", "currency": "XOF"},
            ],
        },
        headers=_auth_headers(owner_b_token),
    )
    assert response_a.status_code == 201
    assert response_b.status_code == 201
    assert response_a.json()["reference"] == f"{today_prefix}0001"
    assert response_b.json()["reference"] == f"{today_prefix}0001"
