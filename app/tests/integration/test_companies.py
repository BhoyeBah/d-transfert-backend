async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise Company",
        "company_phone": "+224800000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Company",
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


async def test_owner_can_update_own_company(client):
    _, token = await _register_and_login_owner(client)

    response = await client.patch(
        "/api/v1/companies/me",
        json={
            "name": "Entreprise Mise à Jour",
            "address": "Nouvelle adresse",
            "phone": "+224800000099",
            "default_currency": "XOF",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Entreprise Mise à Jour"
    assert body["address"] == "Nouvelle adresse"
    assert body["phone"] == "+224800000099"
    assert body["default_currency"] == "XOF"

    me_response = await client.get("/api/v1/companies/me", headers=_auth_headers(token))
    assert me_response.status_code == 200
    assert me_response.json()["name"] == "Entreprise Mise à Jour"


async def test_employee_cannot_update_company(client):
    _, token = await _register_and_login_owner(client)
    employee_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Company",
            "phone": "+224800000002",
            "password": "EmployeePass123!",
            "permissions": [],
        },
        headers=_auth_headers(token),
    )
    employee_matricule = employee_response.json()["matricule"]
    login_response = await client.post(
        "/api/v1/auth/login", json={"matricule": employee_matricule, "password": "EmployeePass123!"}
    )
    employee_token = login_response.json()["access_token"]

    response = await client.patch(
        "/api/v1/companies/me",
        json={
            "name": "Hack",
            "address": "Hack",
            "phone": "+224800000003",
            "default_currency": "USD",
        },
        headers=_auth_headers(employee_token),
    )
    assert response.status_code == 403
