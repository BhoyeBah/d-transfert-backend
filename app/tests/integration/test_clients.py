async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise Client",
        "company_phone": "+224895000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Client",
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


async def test_create_client_quick(client):
    _, token = await _register_and_login_owner(client)
    response = await client.post(
        "/api/v1/clients",
        json={"name": "Client Un", "phone": "+224600000001", "note": "Client fidèle"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["balance"] == "0.00"


async def test_duplicate_phone_returns_existing_client(client):
    _, token = await _register_and_login_owner(client)
    payload = {"name": "Client Un", "phone": "+224600000001"}
    first = await client.post("/api/v1/clients", json=payload, headers=_auth_headers(token))
    second = await client.post("/api/v1/clients", json=payload, headers=_auth_headers(token))
    assert first.json()["id"] == second.json()["id"]


async def test_clients_isolated_between_companies(client):
    _, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224895000010"
    )
    await client.post(
        "/api/v1/clients",
        json={"name": "Client A", "phone": "+224600000002"},
        headers=_auth_headers(token_a),
    )

    _, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224895000011"
    )
    response = await client.get("/api/v1/clients", headers=_auth_headers(token_b))
    assert response.status_code == 200
    assert response.json() == []


async def test_clients_page_search_sort_pagination(client):
    _, token = await _register_and_login_owner(client)
    for phone, name in [
        ("+224600000003", "Alpha Client"),
        ("+224600000004", "Beta Client"),
        ("+224600000005", "Gamma Client"),
    ]:
        await client.post(
            "/api/v1/clients", json={"name": name, "phone": phone}, headers=_auth_headers(token)
        )

    response = await client.get(
        "/api/v1/clients/page",
        params={"page": 1, "page_size": 2, "sort_by": "name", "sort_dir": "asc"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert [item["name"] for item in body["items"]] == ["Alpha Client", "Beta Client"]

    response = await client.get(
        "/api/v1/clients/page", params={"search": "gamma"}, headers=_auth_headers(token)
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Gamma Client"


async def test_employee_without_permission_forbidden(client):
    _, token = await _register_and_login_owner(client)
    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé",
            "phone": "+224896111111",
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

    response = await client.get("/api/v1/clients", headers=_auth_headers(employee_token))
    assert response.status_code == 403
