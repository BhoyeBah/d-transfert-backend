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
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "16"},
        headers=_auth_headers(token_a),
    )

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


async def test_monthly_report_counts_operations_in_month(client):
    _, token = await _register_and_login_owner(client)
    cash_id_response = await client.post(
        "/api/v1/wallets",
        json={"name": "Cash", "code": "CASH", "type": "cash", "currency": "GNF", "initial_balance": "100000"},
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

    from datetime import date

    today = date.today()
    report = await client.get(
        f"/api/v1/reports/monthly?year={today.year}&month={today.month}", headers=_auth_headers(token)
    )
    assert report.status_code == 200
    assert report.json()["deposits_count"] == 1
    assert report.json()["month"] == f"{today.year:04d}-{today.month:02d}"

    csv_response = await client.get(
        f"/api/v1/reports/monthly/export?year={today.year}&month={today.month}", headers=_auth_headers(token)
    )
    assert csv_response.status_code == 200
    assert "deposits_count" in csv_response.text


async def test_transactions_report_includes_transfers_and_payments(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise Trans A", company_phone="+224900200001"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise Trans B", company_phone="+224900200002"
    )
    create_collab = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_collab.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))
    await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "16"},
        headers=_auth_headers(token_a),
    )

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

    report = await client.get("/api/v1/reports/transactions", headers=_auth_headers(token_a))
    assert report.status_code == 200
    kinds = [row["kind"] for row in report.json()]
    assert "transfer" in kinds

    csv_response = await client.get("/api/v1/reports/transactions/export", headers=_auth_headers(token_a))
    assert csv_response.status_code == 200
    assert "transfer" in csv_response.text


async def test_collaborator_balances_report(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise Bal A", company_phone="+224900300001"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise Bal B", company_phone="+224900300002"
    )
    create_collab = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_collab.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))

    report = await client.get("/api/v1/reports/collaborator-balances", headers=_auth_headers(token_a))
    assert report.status_code == 200
    assert len(report.json()) == 1

    csv_response = await client.get(
        "/api/v1/reports/collaborator-balances/export", headers=_auth_headers(token_a)
    )
    assert csv_response.status_code == 200
    assert "collaboration_id" in csv_response.text


async def test_wallet_history_report(client):
    _, token = await _register_and_login_owner(client, company_name="Entreprise Wallet Hist", company_phone="+224900400001")
    cash_id_response = await client.post(
        "/api/v1/wallets",
        json={"name": "Cash", "code": "CASH", "type": "cash", "currency": "GNF", "initial_balance": "50000"},
        headers=_auth_headers(token),
    )
    cash_id = cash_id_response.json()["id"]

    report = await client.get(f"/api/v1/reports/wallets/{cash_id}/history", headers=_auth_headers(token))
    assert report.status_code == 200
    assert len(report.json()) == 1
    assert report.json()[0]["source_type"] == "wallet_initial"

    csv_response = await client.get(
        f"/api/v1/reports/wallets/{cash_id}/history/export", headers=_auth_headers(token)
    )
    assert csv_response.status_code == 200
    assert "source_type" in csv_response.text


async def test_employee_activity_report(client):
    _, token = await _register_and_login_owner(
        client, company_name="Entreprise Employe Act", company_phone="+224900500001"
    )
    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Actif",
            "phone": "+224900511111",
            "password": "EmployeePass123!",
            "permissions": ["wallet.manage"],
        },
        headers=_auth_headers(token),
    )
    employee_id = create_response.json()["id"]
    employee_matricule = create_response.json()["matricule"]
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"matricule": employee_matricule, "password": "EmployeePass123!"},
    )
    employee_token = login_response.json()["access_token"]

    await client.post(
        "/api/v1/wallets",
        json={"name": "Cash", "code": "CASH", "type": "cash", "currency": "GNF"},
        headers=_auth_headers(employee_token),
    )

    report = await client.get(
        f"/api/v1/reports/employees/{employee_id}/activity", headers=_auth_headers(token)
    )
    assert report.status_code == 200
    assert len(report.json()) >= 1

    csv_response = await client.get(
        f"/api/v1/reports/employees/{employee_id}/activity/export", headers=_auth_headers(token)
    )
    assert csv_response.status_code == 200


async def test_fees_report_from_reliquat_fee_action(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise Frais A", company_phone="+224900700001"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise Frais B", company_phone="+224900700002"
    )
    create_collab = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_collab.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))
    await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "16"},
        headers=_auth_headers(token_a),
    )

    wallet_response = await client.post(
        "/api/v1/wallets",
        json={"name": "Cash", "code": "CASH", "type": "cash", "currency": "GNF"},
        headers=_auth_headers(token_a),
    )
    cash_id = wallet_response.json()["id"]

    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "85000", "currency": "GNF"}]},
        headers=_auth_headers(token_a),
    )
    entry_id = entry.json()["id"]

    await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
            "reliquat_action": "fee",
        },
        headers=_auth_headers(token_a),
    )

    report = await client.get("/api/v1/reports/fees", headers=_auth_headers(token_a))
    assert report.status_code == 200
    rows = report.json()
    assert len(rows) == 1
    assert rows[0]["amount"] == "5000.00"
    assert rows[0]["currency"] == "GNF"

    csv_response = await client.get("/api/v1/reports/fees/export", headers=_auth_headers(token_a))
    assert csv_response.status_code == 200
    assert "5000" in csv_response.text


async def test_rejected_operations_report(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise Rejet A", company_phone="+224900600001"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise Rejet B", company_phone="+224900600002"
    )
    create_collab = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_collab.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))
    await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "16"},
        headers=_auth_headers(token_a),
    )

    create_transfer = await client.post(
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
    transfer_id = create_transfer.json()["id"]
    await client.post(
        f"/api/v1/transfers/{transfer_id}/reject", json={"reason": "Preuve invalide"}, headers=_auth_headers(token_b)
    )

    report = await client.get("/api/v1/reports/rejected-operations", headers=_auth_headers(token_a))
    assert report.status_code == 200
    assert any(row["kind"] == "transfer" for row in report.json())

    csv_response = await client.get(
        "/api/v1/reports/rejected-operations/export", headers=_auth_headers(token_a)
    )
    assert csv_response.status_code == 200
    assert "transfer" in csv_response.text


async def test_employee_dashboard_scoped_to_own_activity(client):
    _, owner_token = await _register_and_login_owner(
        client, company_name="Entreprise Dashboard Emp", company_phone="+224900800001"
    )
    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Dashboard",
            "phone": "+224900811111",
            "password": "EmployeePass123!",
            "permissions": ["dashboard.view", "entry.manage", "wallet.manage"],
        },
        headers=_auth_headers(owner_token),
    )
    employee_matricule = create_response.json()["matricule"]
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"matricule": employee_matricule, "password": "EmployeePass123!"},
    )
    employee_token = login_response.json()["access_token"]

    wallet_response = await client.post(
        "/api/v1/wallets",
        json={"name": "Cash", "code": "CASH", "type": "cash", "currency": "GNF"},
        headers=_auth_headers(employee_token),
    )
    cash_id = wallet_response.json()["id"]

    await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "50000", "currency": "GNF"}]},
        headers=_auth_headers(employee_token),
    )

    response = await client.get("/api/v1/dashboard/me", headers=_auth_headers(employee_token))
    assert response.status_code == 200
    body = response.json()
    assert body["entries_created_today_count"] == 1
    assert body["transfers_initiated_today_count"] == 0
    assert body["wallets_count"] == 1

    owner_view = await client.get("/api/v1/dashboard/me", headers=_auth_headers(owner_token))
    assert owner_view.status_code == 200
    assert owner_view.json()["entries_created_today_count"] == 0


async def test_employee_dashboard_hides_wallets_without_permission(client):
    _, owner_token = await _register_and_login_owner(
        client, company_name="Entreprise Dashboard NoWallet", company_phone="+224900900001"
    )
    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Sans Wallet",
            "phone": "+224900911111",
            "password": "EmployeePass123!",
            "permissions": ["dashboard.view"],
        },
        headers=_auth_headers(owner_token),
    )
    employee_matricule = create_response.json()["matricule"]
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"matricule": employee_matricule, "password": "EmployeePass123!"},
    )
    employee_token = login_response.json()["access_token"]

    response = await client.get("/api/v1/dashboard/me", headers=_auth_headers(employee_token))
    assert response.status_code == 200
    assert response.json()["wallets_count"] == 0


async def test_employee_without_permission_forbidden_dashboard(client):
    _, token = await _register_and_login_owner(client)
    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé",
            "phone": "+224900111111",
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

    response = await client.get("/api/v1/dashboard", headers=_auth_headers(employee_token))
    assert response.status_code == 403
