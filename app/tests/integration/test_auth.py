import re
import uuid

import pytest

from app.core.security import create_access_token, hash_password
from app.models.user import User


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_super_admin_token(db_session) -> str:
    super_admin = User(
        company_id=None,
        matricule=f"SA-{uuid.uuid4().hex[:10]}",
        full_name="Super Admin",
        phone=f"+000{uuid.uuid4().int % 100000000:08d}",
        password_hash=hash_password("SuperAdminPass123!"),
        is_owner=False,
        is_super_admin=True,
        is_active=True,
    )
    db_session.add(super_admin)
    await db_session.flush()
    return create_access_token(str(super_admin.id), None)


def _register_payload(**overrides):
    payload = {
        "company_name": "Entreprise A",
        "company_phone": "+224600000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner A",
        "password": "SuperSecret123!",
        "password_confirmation": "SuperSecret123!",
    }
    payload.update(overrides)
    return payload


async def test_register_creates_company_and_owner(client):
    response = await client.post("/api/v1/auth/register", json=_register_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["registration_code"]
    assert body["company_id"]
    assert body["owner_user_id"]


async def test_register_rejects_duplicate_company_phone(client):
    await client.post("/api/v1/auth/register", json=_register_payload())
    response = await client.post(
        "/api/v1/auth/register", json=_register_payload(company_name="Autre Entreprise")
    )
    assert response.status_code == 409


async def test_register_rejects_password_mismatch(client):
    response = await client.post(
        "/api/v1/auth/register",
        json=_register_payload(password_confirmation="Mismatch123!"),
    )
    assert response.status_code == 422


async def test_owner_login_success(client):
    register_response = await client.post("/api/v1/auth/register", json=_register_payload())
    matricule = register_response.json()["registration_code"]

    response = await client.post(
        "/api/v1/auth/login", json={"matricule": matricule, "password": "SuperSecret123!"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]


async def test_owner_login_wrong_password_fails(client):
    register_response = await client.post("/api/v1/auth/register", json=_register_payload())
    matricule = register_response.json()["registration_code"]

    response = await client.post("/api/v1/auth/login", json={"matricule": matricule, "password": "WrongPassword!"})
    assert response.status_code == 401


async def test_registration_pending_when_approval_required(client, db_session):
    admin_token = await _create_super_admin_token(db_session)
    await client.patch(
        "/api/v1/admin/settings",
        json={"require_company_approval": True},
        headers=_auth_headers(admin_token),
    )

    register_response = await client.post("/api/v1/auth/register", json=_register_payload())
    matricule = register_response.json()["registration_code"]

    login_response = await client.post(
        "/api/v1/auth/login", json={"matricule": matricule, "password": "SuperSecret123!"}
    )
    assert login_response.status_code == 401
    assert "attente" in login_response.json()["detail"].lower()

    activate_response = await client.patch(
        f"/api/v1/admin/companies/{register_response.json()['company_id']}/status",
        json={"status": "active"},
        headers=_auth_headers(admin_token),
    )
    assert activate_response.status_code == 200

    login_after_activation = await client.post(
        "/api/v1/auth/login", json={"matricule": matricule, "password": "SuperSecret123!"}
    )
    assert login_after_activation.status_code == 200


async def test_registration_active_by_default(client):
    register_response = await client.post("/api/v1/auth/register", json=_register_payload())
    matricule = register_response.json()["registration_code"]

    login_response = await client.post(
        "/api/v1/auth/login", json={"matricule": matricule, "password": "SuperSecret123!"}
    )
    assert login_response.status_code == 200


async def test_login_lockout_after_max_failed_attempts(client):
    register_response = await client.post("/api/v1/auth/register", json=_register_payload())
    matricule = register_response.json()["registration_code"]

    for _ in range(5):
        await client.post("/api/v1/auth/login", json={"matricule": matricule, "password": "WrongPassword!"})

    response = await client.post("/api/v1/auth/login", json={"matricule": matricule, "password": "SuperSecret123!"})
    assert response.status_code == 401
    assert "verrouillé" in response.json()["detail"]


async def test_refresh_token_issues_new_access_token(client):
    register_response = await client.post("/api/v1/auth/register", json=_register_payload())
    matricule = register_response.json()["registration_code"]
    login_response = await client.post(
        "/api/v1/auth/login", json={"matricule": matricule, "password": "SuperSecret123!"}
    )
    refresh_token = login_response.json()["refresh_token"]

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_password_reset_flow(client, caplog):
    register_response = await client.post("/api/v1/auth/register", json=_register_payload())
    matricule = register_response.json()["registration_code"]

    with caplog.at_level("INFO", logger="dtransfert.auth"):
        forgot_response = await client.post("/api/v1/auth/forgot-password", json={"matricule": matricule})
    assert forgot_response.status_code == 204

    match = re.search(r"OTP de réinitialisation généré pour user_id=.*: (\d{6})", caplog.text)
    assert match is not None
    otp_code = match.group(1)

    reset_response = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "matricule": matricule,
            "otp_code": otp_code,
            "new_password": "NewSecret456!",
            "new_password_confirmation": "NewSecret456!",
        },
    )
    assert reset_response.status_code == 204

    old_password_login = await client.post(
        "/api/v1/auth/login", json={"matricule": matricule, "password": "SuperSecret123!"}
    )
    assert old_password_login.status_code == 401

    new_password_login = await client.post(
        "/api/v1/auth/login", json={"matricule": matricule, "password": "NewSecret456!"}
    )
    assert new_password_login.status_code == 200


async def test_company_isolation_between_two_registrations(client):
    resp_a = await client.post("/api/v1/auth/register", json=_register_payload())
    resp_b = await client.post(
        "/api/v1/auth/register",
        json=_register_payload(company_name="Entreprise B", company_phone="+224600000002"),
    )
    assert resp_a.json()["registration_code"] != resp_b.json()["registration_code"]

    login_a = await client.post(
        "/api/v1/auth/login",
        json={"matricule": resp_a.json()["registration_code"], "password": "SuperSecret123!"},
    )
    token_a = login_a.json()["access_token"]

    me_response = await client.get(
        "/api/v1/companies/me", headers={"Authorization": f"Bearer {token_a}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["registration_code"] == resp_a.json()["registration_code"]


async def test_auth_me_returns_profile_and_permissions(client):
    register_response = await client.post("/api/v1/auth/register", json=_register_payload())
    matricule = register_response.json()["registration_code"]
    login_response = await client.post(
        "/api/v1/auth/login", json={"matricule": matricule, "password": "SuperSecret123!"}
    )
    token = login_response.json()["access_token"]

    me_response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    body = me_response.json()
    assert body["matricule"] == matricule
    assert body["is_owner"] is True
    assert body["is_super_admin"] is False
    assert "wallet.manage" in body["permissions"]


async def test_auth_me_requires_authentication(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
