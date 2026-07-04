import re

import pytest


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
