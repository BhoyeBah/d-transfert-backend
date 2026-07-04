async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise Dashboard",
        "company_phone": "+224900100001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Dashboard",
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


async def test_dashboard_reflects_wallets_and_pending_transfers(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224900100010"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224900100011"
    )

    await client.post(
        "/api/v1/wallets",
        json={
            "name": "Cash",
            "code": "CASH",
            "type": "cash",
            "currency": "GNF",
            "initial_balance": "50000",
        },
        headers=_auth_headers(token_a),
    )

    create_collab = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_collab.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))

    await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "10000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )

    dashboard = await client.get("/api/v1/dashboard", headers=_auth_headers(token_a))
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["wallets_balance_by_currency"] == {"GNF": "50000.00"}
    assert body["active_collaborations_count"] == 1
    assert body["transfers_pending_count"] == 1
    assert len(body["collaborator_balances"]) == 1


async def test_daily_report_counts_todays_national_operations(client):
    _, token = await _register_and_login_owner(client)
    cash_id_response = await client.post(
        "/api/v1/wallets",
        json={
            "name": "Cash",
            "code": "CASH",
            "type": "cash",
            "currency": "GNF",
            "initial_balance": "100000",
        },
        headers=_auth_headers(token),
    )
    cash_id = cash_id_response.json()["id"]
    wave_id_response = await client.post(
        "/api/v1/wallets",
        json={"name": "Wave", "code": "WAVE", "type": "cash", "currency": "GNF"},
        headers=_auth_headers(token),
    )
    wave_id = wave_id_response.json()["id"]

    await client.post(
        "/api/v1/national-operations/deposits",
        json={
            "lines": [
                {"wallet_id": cash_id, "amount_in": "0", "amount_out": "10000", "currency": "GNF"},
                {"wallet_id": wave_id, "amount_in": "10000", "amount_out": "0", "currency": "GNF"},
            ]
        },
        headers=_auth_headers(token),
    )

    report = await client.get("/api/v1/reports/daily", headers=_auth_headers(token))
    assert report.status_code == 200
    assert report.json()["deposits_count"] == 1

    csv_response = await client.get("/api/v1/reports/daily/export", headers=_auth_headers(token))
    assert csv_response.status_code == 200
    assert "deposits_count" in csv_response.text


async def test_employee_without_permission_forbidden_dashboard(client):
    matricule, token = await _register_and_login_owner(client)
    await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé",
            "phone": "+224900111111",
            "password": "EmployeePass123!",
            "permissions": [],
        },
        headers=_auth_headers(token),
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"matricule": matricule, "phone": "+224900111111", "password": "EmployeePass123!"},
    )
    employee_token = login_response.json()["access_token"]

    response = await client.get("/api/v1/dashboard", headers=_auth_headers(employee_token))
    assert response.status_code == 403
