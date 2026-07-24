import uuid

import pytest

from app.core.exceptions import ConflictError
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.services import admin_service


async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise Admin",
        "company_phone": "+224901000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Admin",
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


async def _create_super_admin(db_session) -> tuple[uuid.UUID, str]:
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
    return super_admin.id, create_access_token(str(super_admin.id), None)


async def _create_super_admin_token(db_session) -> str:
    _, token = await _create_super_admin(db_session)
    return token


async def test_owner_cannot_access_admin_endpoints(client):
    _, token = await _register_and_login_owner(client)
    response = await client.get("/api/v1/admin/companies", headers=_auth_headers(token))
    assert response.status_code == 403


async def test_super_admin_can_list_and_suspend_companies(client, db_session):
    _, owner_token = await _register_and_login_owner(client)
    admin_token = await _create_super_admin_token(db_session)

    list_response = await client.get("/api/v1/admin/companies", headers=_auth_headers(admin_token))
    assert list_response.status_code == 200
    companies = list_response.json()
    assert len(companies) == 1
    company_id = companies[0]["id"]

    suspend_response = await client.patch(
        f"/api/v1/admin/companies/{company_id}/status",
        json={"status": "suspended"},
        headers=_auth_headers(admin_token),
    )
    assert suspend_response.status_code == 200
    assert suspend_response.json()["status"] == "suspended"

    login_after_suspend = await client.post(
        "/api/v1/auth/login",
        json={"matricule": companies[0]["registration_code"], "password": "SuperSecret123!"},
    )
    assert login_after_suspend.status_code == 401


async def test_super_admin_can_create_company(client, db_session):
    admin_token = await _create_super_admin_token(db_session)
    payload = {
        "company_name": "Nouvelle Entreprise",
        "company_phone": "+224901000099",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Nouvelle",
        "password": "SuperSecret123!",
        "password_confirmation": "SuperSecret123!",
    }

    response = await client.post(
        "/api/v1/admin/companies", json=payload, headers=_auth_headers(admin_token)
    )
    assert response.status_code == 201
    body = response.json()
    assert body["registration_code"] == "nouvelle-entreprise"

    companies = (await client.get("/api/v1/admin/companies", headers=_auth_headers(admin_token))).json()
    assert any(company["phone"] == payload["company_phone"] for company in companies)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"matricule": body["registration_code"], "password": payload["password"]},
    )
    assert login_response.status_code == 200


async def test_super_admin_can_paginate_search_sort_companies(client, db_session):
    admin_token = await _create_super_admin_token(db_session)
    await _register_and_login_owner(client, company_name="Zeta Corp", company_phone="+224900000201")
    await _register_and_login_owner(client, company_name="Alpha Corp", company_phone="+224900000202")

    response = await client.get(
        "/api/v1/admin/companies/page",
        params={"sort_by": "name", "sort_dir": "asc"},
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [c["name"] for c in body["items"]] == ["Alpha Corp", "Zeta Corp"]

    search_response = await client.get(
        "/api/v1/admin/companies/page", params={"search": "zeta"}, headers=_auth_headers(admin_token)
    )
    assert search_response.json()["total"] == 1


async def test_super_admin_can_view_platform_wide_audit_logs(client, db_session):
    _, owner_token = await _register_and_login_owner(client)
    admin_token = await _create_super_admin_token(db_session)

    own_logs = await client.get("/api/v1/admin/audit-logs", headers=_auth_headers(admin_token))
    assert own_logs.status_code == 200
    actions = {log["action"] for log in own_logs.json()}
    assert "login" in actions

    forbidden = await client.get("/api/v1/admin/audit-logs", headers=_auth_headers(owner_token))
    assert forbidden.status_code == 403


async def test_super_admin_can_paginate_audit_logs(client, db_session):
    _, owner_token = await _register_and_login_owner(client)
    admin_token = await _create_super_admin_token(db_session)

    response = await client.get(
        "/api/v1/admin/audit-logs/page", params={"page_size": 1}, headers=_auth_headers(admin_token)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["page_size"] == 1
    assert len(body["items"]) == 1
    assert body["total"] >= 1

    forbidden = await client.get("/api/v1/admin/audit-logs/page", headers=_auth_headers(owner_token))
    assert forbidden.status_code == 403


async def test_super_admin_can_view_platform_stats(client, db_session):
    _, owner_token = await _register_and_login_owner(client)
    admin_token = await _create_super_admin_token(db_session)

    response = await client.get("/api/v1/admin/stats", headers=_auth_headers(admin_token))
    assert response.status_code == 200
    stats = response.json()
    assert stats["companies_total"] >= 1
    assert stats["companies_active"] >= 1
    assert stats["users_total"] >= 1
    assert "volume_by_currency" in stats

    forbidden = await client.get("/api/v1/admin/stats", headers=_auth_headers(owner_token))
    assert forbidden.status_code == 403


async def test_super_admin_can_view_company_detail(client, db_session):
    _, owner_token = await _register_and_login_owner(client)
    admin_token = await _create_super_admin_token(db_session)

    companies = (await client.get("/api/v1/admin/companies", headers=_auth_headers(admin_token))).json()
    company_id = companies[0]["id"]

    detail = await client.get(
        f"/api/v1/admin/companies/{company_id}", headers=_auth_headers(admin_token)
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["users_count"] == 1
    assert body["wallets_count"] == 0
    assert body["entries_count"] == 0

    missing = await client.get(
        f"/api/v1/admin/companies/{uuid.uuid4()}", headers=_auth_headers(admin_token)
    )
    assert missing.status_code == 404

    forbidden = await client.get(
        f"/api/v1/admin/companies/{company_id}", headers=_auth_headers(owner_token)
    )
    assert forbidden.status_code == 403


async def test_super_admin_can_list_and_suspend_company_users(client, db_session):
    _, owner_token = await _register_and_login_owner(client)
    admin_token = await _create_super_admin_token(db_session)

    companies = (await client.get("/api/v1/admin/companies", headers=_auth_headers(admin_token))).json()
    company_id = companies[0]["id"]

    users_response = await client.get(
        f"/api/v1/admin/companies/{company_id}/users", headers=_auth_headers(admin_token)
    )
    assert users_response.status_code == 200
    users = users_response.json()
    assert len(users) == 1
    owner_user = users[0]
    assert owner_user["is_owner"] is True
    assert owner_user["is_active"] is True

    suspend_response = await client.patch(
        f"/api/v1/admin/users/{owner_user['id']}/status",
        json={"is_active": False},
        headers=_auth_headers(admin_token),
    )
    assert suspend_response.status_code == 200
    assert suspend_response.json()["is_active"] is False

    # The now-suspended owner can no longer authenticate.
    login_after_suspend = await client.post(
        "/api/v1/auth/login",
        json={"matricule": companies[0]["registration_code"], "password": "SuperSecret123!"},
    )
    assert login_after_suspend.status_code == 401


async def test_super_admin_can_update_company_user(client, db_session):
    matricule, owner_token = await _register_and_login_owner(client)
    admin_token = await _create_super_admin_token(db_session)

    companies = (await client.get("/api/v1/admin/companies", headers=_auth_headers(admin_token))).json()
    company_id = companies[0]["id"]

    users = (
        await client.get(f"/api/v1/admin/companies/{company_id}/users", headers=_auth_headers(admin_token))
    ).json()
    owner_user_id = users[0]["id"]

    update_response = await client.patch(
        f"/api/v1/admin/companies/{company_id}/users/{owner_user_id}",
        json={"full_name": "Owner Renommé", "phone": "+224900777777", "password": "NouveauSecret123!"},
        headers=_auth_headers(admin_token),
    )
    assert update_response.status_code == 200
    assert update_response.json()["full_name"] == "Owner Renommé"
    assert update_response.json()["phone"] == "+224900777777"

    # The owner can now log in with the reset password.
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"matricule": matricule, "password": "NouveauSecret123!"},
    )
    assert login_response.status_code == 200

    # The old password no longer works.
    old_password_login = await client.post(
        "/api/v1/auth/login",
        json={"matricule": matricule, "password": "SuperSecret123!"},
    )
    assert old_password_login.status_code == 401

    forbidden = await client.patch(
        f"/api/v1/admin/companies/{company_id}/users/{owner_user_id}",
        json={"full_name": "Nope"},
        headers=_auth_headers(owner_token),
    )
    assert forbidden.status_code == 403


async def test_super_admin_can_view_system_logs_from_failed_login(client, db_session):
    matricule, owner_token = await _register_and_login_owner(client)
    admin_token = await _create_super_admin_token(db_session)

    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"matricule": matricule, "password": "wrong-password"},
    )
    assert bad_login.status_code == 401

    logs_response = await client.get("/api/v1/admin/system-logs", headers=_auth_headers(admin_token))
    assert logs_response.status_code == 200
    logs = logs_response.json()
    assert any(log["source"] == "auth" for log in logs)

    forbidden = await client.get("/api/v1/admin/system-logs", headers=_auth_headers(owner_token))
    assert forbidden.status_code == 403


async def test_super_admin_can_paginate_system_logs(client, db_session):
    matricule, owner_token = await _register_and_login_owner(client)
    admin_token = await _create_super_admin_token(db_session)

    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"matricule": matricule, "password": "wrong-password"},
    )
    assert bad_login.status_code == 401

    response = await client.get(
        "/api/v1/admin/system-logs/page", params={"search": "auth"}, headers=_auth_headers(admin_token)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert all(log["source"] == "auth" for log in body["items"])

    forbidden = await client.get("/api/v1/admin/system-logs/page", headers=_auth_headers(owner_token))
    assert forbidden.status_code == 403


async def test_super_admin_can_manage_platform_settings(client, db_session):
    _, owner_token = await _register_and_login_owner(client)
    admin_token = await _create_super_admin_token(db_session)

    get_response = await client.get("/api/v1/admin/settings", headers=_auth_headers(admin_token))
    assert get_response.status_code == 200
    assert get_response.json()["maintenance_mode"] is False

    update_response = await client.patch(
        "/api/v1/admin/settings",
        json={"maintenance_mode": True, "supported_currencies": ["XOF", "USD"]},
        headers=_auth_headers(admin_token),
    )
    assert update_response.status_code == 200
    body = update_response.json()
    assert body["maintenance_mode"] is True
    assert body["supported_currencies"] == ["XOF", "USD"]

    forbidden = await client.patch(
        "/api/v1/admin/settings",
        json={"maintenance_mode": True},
        headers=_auth_headers(owner_token),
    )
    assert forbidden.status_code == 403


async def test_super_admin_can_manage_company_subscription(client, db_session):
    _, owner_token = await _register_and_login_owner(client)
    admin_token = await _create_super_admin_token(db_session)

    companies = (await client.get("/api/v1/admin/companies", headers=_auth_headers(admin_token))).json()
    company_id = companies[0]["id"]

    get_response = await client.get(
        f"/api/v1/admin/companies/{company_id}/subscription", headers=_auth_headers(admin_token)
    )
    assert get_response.status_code == 200
    assert get_response.json()["plan"] == "free"

    update_response = await client.patch(
        f"/api/v1/admin/companies/{company_id}/subscription",
        json={"plan": "premium", "status": "active", "price": "49.99", "currency": "USD"},
        headers=_auth_headers(admin_token),
    )
    assert update_response.status_code == 200
    body = update_response.json()
    assert body["plan"] == "premium"
    assert body["price"] == "49.99"

    forbidden = await client.get(
        f"/api/v1/admin/companies/{company_id}/subscription", headers=_auth_headers(owner_token)
    )
    assert forbidden.status_code == 403


async def test_super_admin_can_list_and_create_platform_admins(client, db_session):
    _, owner_token = await _register_and_login_owner(client)
    admin_id, admin_token = await _create_super_admin(db_session)

    list_response = await client.get("/api/v1/admin/platform-admins", headers=_auth_headers(admin_token))
    assert list_response.status_code == 200
    assert {a["id"] for a in list_response.json()} == {str(admin_id)}

    create_response = await client.post(
        "/api/v1/admin/platform-admins",
        json={"full_name": "Nouveau Super Admin", "phone": "+224900555555", "password": "AnotherSecret123!"},
        headers=_auth_headers(admin_token),
    )
    assert create_response.status_code == 201
    new_admin = create_response.json()
    assert new_admin["is_super_admin"] is True
    assert new_admin["is_active"] is True
    assert new_admin["matricule"].startswith("SA-")

    list_after = await client.get("/api/v1/admin/platform-admins", headers=_auth_headers(admin_token))
    assert {a["id"] for a in list_after.json()} == {str(admin_id), new_admin["id"]}

    # The new platform admin can log in.
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"matricule": new_admin["matricule"], "password": "AnotherSecret123!"},
    )
    assert login_response.status_code == 200

    duplicate_phone = await client.post(
        "/api/v1/admin/platform-admins",
        json={"full_name": "Doublon", "phone": "+224900555555", "password": "AnotherSecret123!"},
        headers=_auth_headers(admin_token),
    )
    assert duplicate_phone.status_code == 409

    forbidden = await client.get("/api/v1/admin/platform-admins", headers=_auth_headers(owner_token))
    assert forbidden.status_code == 403

    forbidden_create = await client.post(
        "/api/v1/admin/platform-admins",
        json={"full_name": "Nope", "phone": "+224900666666", "password": "AnotherSecret123!"},
        headers=_auth_headers(owner_token),
    )
    assert forbidden_create.status_code == 403


async def test_super_admin_can_update_and_delete_platform_admin(client, db_session):
    admin_id, admin_token = await _create_super_admin(db_session)
    _, _ = await _create_super_admin(db_session)

    update_response = await client.patch(
        f"/api/v1/admin/platform-admins/{admin_id}",
        json={"full_name": "Super Admin Modifié", "phone": "+000999999999"},
        headers=_auth_headers(admin_token),
    )
    assert update_response.status_code == 200
    assert update_response.json()["full_name"] == "Super Admin Modifié"
    assert update_response.json()["phone"] == "+000999999999"

    delete_response = await client.delete(
        f"/api/v1/admin/platform-admins/{admin_id}",
        headers=_auth_headers(admin_token),
    )
    assert delete_response.status_code == 204

    list_after = await client.get("/api/v1/admin/platform-admins", headers=_auth_headers(admin_token))
    assert len(list_after.json()) == 1


async def test_super_admin_cannot_suspend_own_account(client, db_session):
    admin_id, admin_token = await _create_super_admin(db_session)

    response = await client.patch(
        f"/api/v1/admin/users/{admin_id}/status",
        json={"is_active": False},
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 409


async def test_cannot_suspend_last_active_super_admin(db_session):
    # Exercised at the service layer: through the API, an actor must hold a
    # valid (active) super admin token, so by the time only one admin is left
    # active, any *other* admin's token is already rejected upstream with 401
    # before this guard is even reached — only the "self-suspend" check (a
    # stricter, unconditional rule) is reachable via HTTP. This test isolates
    # the "last active admin" rule on its own.
    admin_id, _ = await _create_super_admin(db_session)
    other_id, _ = await _create_super_admin(db_session)

    # Two active admins: suspending the other one is fine.
    await admin_service.set_user_status(db_session, admin_id, other_id, False)

    # Only `admin_id` remains active; a different actor suspending it is blocked.
    with pytest.raises(ConflictError):
        await admin_service.set_user_status(db_session, other_id, admin_id, False)


async def test_super_admin_can_update_company_details(client, db_session):
    _, owner_token = await _register_and_login_owner(client)
    admin_token = await _create_super_admin_token(db_session)

    companies = (await client.get("/api/v1/admin/companies", headers=_auth_headers(admin_token))).json()
    company_id = companies[0]["id"]

    update_response = await client.patch(
        f"/api/v1/admin/companies/{company_id}",
        json={"name": "Entreprise Renommée", "address": "Nouvelle adresse", "default_currency": "XOF"},
        headers=_auth_headers(admin_token),
    )
    assert update_response.status_code == 200
    body = update_response.json()
    assert body["name"] == "Entreprise Renommée"
    assert body["address"] == "Nouvelle adresse"
    assert body["default_currency"] == "XOF"
    # Untouched fields are preserved.
    assert body["phone"] == "+224901000001"

    detail = await client.get(
        f"/api/v1/admin/companies/{company_id}", headers=_auth_headers(admin_token)
    )
    assert detail.json()["name"] == "Entreprise Renommée"

    forbidden = await client.patch(
        f"/api/v1/admin/companies/{company_id}",
        json={"name": "Hack"},
        headers=_auth_headers(owner_token),
    )
    assert forbidden.status_code == 403


async def test_super_admin_cannot_reuse_another_companys_phone(client, db_session):
    _, _ = await _register_and_login_owner(client, company_phone="+224901000002")
    _, _ = await _register_and_login_owner(client, company_name="Autre Entreprise", company_phone="+224901000003")
    admin_token = await _create_super_admin_token(db_session)

    companies = (await client.get("/api/v1/admin/companies", headers=_auth_headers(admin_token))).json()
    target = next(c for c in companies if c["phone"] == "+224901000003")

    response = await client.patch(
        f"/api/v1/admin/companies/{target['id']}",
        json={"phone": "+224901000002"},
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 409


async def test_super_admin_can_delete_company(client, db_session):
    # Créer une entreprise
    matricule, _ = await _register_and_login_owner(
        client, company_name="A Supprimer", company_phone="+224901099999"
    )
    admin_token = await _create_super_admin_token(db_session)

    companies = (await client.get("/api/v1/admin/companies", headers=_auth_headers(admin_token))).json()
    assert len(companies) == 1
    company_id = companies[0]["id"]

    # Supprimer l'entreprise
    delete_response = await client.delete(
        f"/api/v1/admin/companies/{company_id}", headers=_auth_headers(admin_token)
    )
    assert delete_response.status_code == 200
    body = delete_response.json()
    assert body["company_id"] == company_id

    # L'entreprise n'existe plus
    get_response = await client.get(
        f"/api/v1/admin/companies/{company_id}", headers=_auth_headers(admin_token)
    )
    assert get_response.status_code == 404

    # La liste est vide
    companies_after = (await client.get("/api/v1/admin/companies", headers=_auth_headers(admin_token))).json()
    assert companies_after == []

    # Un owner ne peut pas appeler cet endpoint
    _, owner_token = await _register_and_login_owner(
        client, company_name="Autre Entreprise", company_phone="+224901099998"
    )
    other_companies = (await client.get("/api/v1/admin/companies", headers=_auth_headers(admin_token))).json()
    other_id = other_companies[0]["id"]
    forbidden = await client.delete(
        f"/api/v1/admin/companies/{other_id}", headers=_auth_headers(owner_token)
    )
    assert forbidden.status_code == 403


async def test_super_admin_can_delete_company_with_shared_collaboration(client, db_session):
    _, token_a = await _register_and_login_owner(
        client, company_name="Entreprise Alpha", company_phone="+224901099997"
    )
    _, token_b = await _register_and_login_owner(
        client, company_name="Entreprise Beta", company_phone="+224901099996"
    )
    admin_token = await _create_super_admin_token(db_session)

    companies = (await client.get("/api/v1/admin/companies", headers=_auth_headers(admin_token))).json()
    company_b = next(company for company in companies if company["phone"] == "+224901099996")

    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": company_b["registration_code"], "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    assert create_response.status_code == 201
    collaboration_id = create_response.json()["id"]

    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))
    await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "15"},
        headers=_auth_headers(token_a),
    )
    transfer_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "1000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    assert transfer_response.status_code == 201

    delete_response = await client.delete(
        f"/api/v1/admin/companies/{company_b['id']}", headers=_auth_headers(admin_token)
    )
    assert delete_response.status_code == 200

    remaining_companies = (await client.get("/api/v1/admin/companies", headers=_auth_headers(admin_token))).json()
    assert len(remaining_companies) == 1

    alpha_detail = await client.get(
        f"/api/v1/admin/companies/{remaining_companies[0]['id']}", headers=_auth_headers(admin_token)
    )
    assert alpha_detail.status_code == 200
    assert alpha_detail.json()["transfers_count"] == 0


async def test_super_admin_delete_company_not_found(client, db_session):
    admin_token = await _create_super_admin_token(db_session)
    response = await client.delete(
        f"/api/v1/admin/companies/{uuid.uuid4()}", headers=_auth_headers(admin_token)
    )
    assert response.status_code == 404
