from sqlalchemy import select

from app.models.audit_log import AuditLog


async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise Audit",
        "company_phone": "+224899000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Audit",
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


async def test_login_creates_audit_log(client, db_session):
    matricule, token = await _register_and_login_owner(client)
    await client.post("/api/v1/auth/login", json={"matricule": matricule, "password": "SuperSecret123!"})

    result = await db_session.execute(select(AuditLog).where(AuditLog.action == "login"))
    logs = result.scalars().all()
    assert len(logs) >= 1


async def test_employee_create_creates_audit_log(client, db_session):
    _, token = await _register_and_login_owner(client)
    await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Un",
            "phone": "+224899111111",
            "password": "EmployeePass123!",
            "permissions": [],
        },
        headers=_auth_headers(token),
    )

    result = await db_session.execute(select(AuditLog).where(AuditLog.action == "employee.create"))
    logs = result.scalars().all()
    assert len(logs) == 1


async def test_wallet_create_creates_audit_log(client, db_session):
    _, token = await _register_and_login_owner(client)
    await client.post(
        "/api/v1/wallets",
        json={"name": "Cash", "code": "CASH", "type": "cash", "currency": "GNF"},
        headers=_auth_headers(token),
    )

    result = await db_session.execute(select(AuditLog).where(AuditLog.action == "wallet.create"))
    logs = result.scalars().all()
    assert len(logs) == 1


async def test_audit_logs_isolated_between_companies(client):
    _, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224899000010"
    )
    await client.post(
        "/api/v1/wallets",
        json={"name": "Cash", "code": "CASH", "type": "cash", "currency": "GNF"},
        headers=_auth_headers(token_a),
    )

    _, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224899000011"
    )
    response = await client.get("/api/v1/audit-logs", headers=_auth_headers(token_b))
    assert response.status_code == 200
    actions = [log["action"] for log in response.json()]
    assert "wallet.create" not in actions


async def test_collaboration_request_and_accept_create_notifications(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224899000020"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224899000021"
    )

    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]

    notifications_b = await client.get("/api/v1/notifications", headers=_auth_headers(token_b))
    assert notifications_b.status_code == 200
    assert len(notifications_b.json()) == 1
    assert notifications_b.json()[0]["type"] == "collaboration_request"
    assert notifications_b.json()[0]["is_read"] is False

    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))

    notifications_a = await client.get("/api/v1/notifications", headers=_auth_headers(token_a))
    assert len(notifications_a.json()) == 1
    assert notifications_a.json()[0]["type"] == "collaboration_accepted"


async def test_mark_notification_as_read(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224899000030"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224899000031"
    )
    await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    notifications_b = await client.get("/api/v1/notifications", headers=_auth_headers(token_b))
    notification_id = notifications_b.json()[0]["id"]

    response = await client.patch(
        f"/api/v1/notifications/{notification_id}/read", headers=_auth_headers(token_b)
    )
    assert response.status_code == 200
    assert response.json()["is_read"] is True


async def test_notifications_isolated_between_companies(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224899000040"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224899000041"
    )
    _, token_c = await _register_and_login_owner(
        client, company_name="Entreprise C", company_phone="+224899000042"
    )
    await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )

    response = await client.get("/api/v1/notifications", headers=_auth_headers(token_c))
    assert response.status_code == 200
    assert response.json() == []
