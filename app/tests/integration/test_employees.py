async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise A",
        "company_phone": "+224600000010",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner A",
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


async def test_owner_can_create_employee_with_permissions(client):
    _, owner_token = await _register_and_login_owner(client)

    response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Un",
            "phone": "+224611111111",
            "password": "EmployeePass123!",
            "permissions": ["wallet.manage"],
        },
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["matricule"].startswith("DT-")
    assert body["permissions"] == ["wallet.manage"]
    assert body["is_active"] is True


async def test_duplicate_phone_within_company_rejected(client):
    _, owner_token = await _register_and_login_owner(client)
    payload = {
        "full_name": "Employé Un",
        "phone": "+224611111111",
        "password": "EmployeePass123!",
        "permissions": [],
    }
    await client.post("/api/v1/employees", json=payload, headers=_auth_headers(owner_token))
    response = await client.post("/api/v1/employees", json=payload, headers=_auth_headers(owner_token))
    assert response.status_code == 409


async def test_employee_login_and_permission_enforcement(client):
    matricule, owner_token = await _register_and_login_owner(client)
    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Un",
            "phone": "+224611111111",
            "password": "EmployeePass123!",
            "permissions": [],
        },
        headers=_auth_headers(owner_token),
    )
    employee_matricule = create_response.json()["matricule"]

    login_response = await client.post(
        "/api/v1/auth/login", json={"matricule": employee_matricule, "password": "EmployeePass123!"}
    )
    assert login_response.status_code == 200
    employee_token = login_response.json()["access_token"]

    forbidden_response = await client.get(
        "/api/v1/employees", headers=_auth_headers(employee_token)
    )
    assert forbidden_response.status_code == 403


async def test_owner_grant_permission_enables_employee_access(client):
    matricule, owner_token = await _register_and_login_owner(client)
    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Un",
            "phone": "+224611111111",
            "password": "EmployeePass123!",
            "permissions": [],
        },
        headers=_auth_headers(owner_token),
    )
    employee_id = create_response.json()["id"]

    await client.patch(
        f"/api/v1/employees/{employee_id}/permissions",
        json={"grant": ["employee.manage"], "revoke": []},
        headers=_auth_headers(owner_token),
    )
    employee_matricule = create_response.json()["matricule"]

    login_response = await client.post(
        "/api/v1/auth/login", json={"matricule": employee_matricule, "password": "EmployeePass123!"}
    )
    employee_token = login_response.json()["access_token"]

    allowed_response = await client.get("/api/v1/employees", headers=_auth_headers(employee_token))
    assert allowed_response.status_code == 200


async def test_owner_can_deactivate_employee_and_login_fails(client):
    matricule, owner_token = await _register_and_login_owner(client)
    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Un",
            "phone": "+224611111111",
            "password": "EmployeePass123!",
            "permissions": [],
        },
        headers=_auth_headers(owner_token),
    )
    employee_id = create_response.json()["id"]

    status_response = await client.patch(
        f"/api/v1/employees/{employee_id}/status",
        json={"is_active": False},
        headers=_auth_headers(owner_token),
    )
    assert status_response.status_code == 200
    assert status_response.json()["is_active"] is False
    employee_matricule = create_response.json()["matricule"]

    login_response = await client.post(
        "/api/v1/auth/login", json={"matricule": employee_matricule, "password": "EmployeePass123!"}
    )
    assert login_response.status_code == 401


async def test_employees_page_search_sort_pagination(client):
    _, owner_token = await _register_and_login_owner(client)
    for phone, name in [
        ("+224611111112", "Alpha Diallo"),
        ("+224611111113", "Beta Bah"),
        ("+224611111114", "Gamma Sow"),
    ]:
        await client.post(
            "/api/v1/employees",
            json={
                "full_name": name,
                "phone": phone,
                "password": "EmployeePass123!",
                "permissions": [],
            },
            headers=_auth_headers(owner_token),
        )

    response = await client.get(
        "/api/v1/employees/page",
        params={"page": 1, "page_size": 2, "sort_by": "full_name", "sort_dir": "asc"},
        headers=_auth_headers(owner_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert [item["full_name"] for item in body["items"]] == ["Alpha Diallo", "Beta Bah"]

    response = await client.get(
        "/api/v1/employees/page", params={"search": "gamma"}, headers=_auth_headers(owner_token)
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["full_name"] == "Gamma Sow"


async def test_employee_list_is_isolated_between_companies(client):
    _, owner_a_token = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224600000020"
    )
    await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé A",
            "phone": "+224622222222",
            "password": "EmployeePass123!",
            "permissions": [],
        },
        headers=_auth_headers(owner_a_token),
    )

    _, owner_b_token = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224600000021"
    )

    response = await client.get("/api/v1/employees", headers=_auth_headers(owner_b_token))
    assert response.status_code == 200
    assert response.json() == []
