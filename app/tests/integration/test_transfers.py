async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise Transfert",
        "company_phone": "+224870000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Transfert",
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


async def _create_wallet(client, token, code, currency="GNF"):
    response = await client.post(
        "/api/v1/wallets",
        json={"name": code, "code": code, "type": "cash", "currency": currency},
        headers=_auth_headers(token),
    )
    return response.json()["id"]


async def _setup_accepted_collaboration(client, rate="16", currency="GNF"):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224870000010"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224870000011"
    )
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": currency, "initial_rate": rate},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))
    return collaboration_id, (matricule_a, token_a), (matricule_b, token_b)


async def test_create_transfer_with_currency_conversion(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)

    response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "5000",
            "currency": "XOF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["collaborative_rate_used"] == "16.000000"
    assert body["converted_amount"] == "80000.00"


async def test_transfer_same_currency_as_collaboration_no_conversion(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)

    response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201
    assert response.json()["converted_amount"] == "80000.00"


async def test_transfer_requires_accepted_collaboration(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224870000020"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224870000021"
    )
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]

    response = await client.post(
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
    assert response.status_code == 409


async def test_create_transfer_from_entry_partial_allocation(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_a, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "85000", "currency": "GNF"}]},
        headers=_auth_headers(token_a),
    )
    entry_id = entry.json()["id"]

    response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201

    entry_after = await client.get(f"/api/v1/entries/{entry_id}", headers=_auth_headers(token_a))
    assert entry_after.json()["status"] == "partially_allocated"
    assert entry_after.json()["available_by_currency"] == {"GNF": "5000.00"}


async def test_create_transfer_from_entry_full_allocation(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_a, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "80000", "currency": "GNF"}]},
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
        },
        headers=_auth_headers(token_a),
    )

    entry_after = await client.get(f"/api/v1/entries/{entry_id}", headers=_auth_headers(token_a))
    assert entry_after.json()["status"] == "consumed"
    assert entry_after.json()["available_by_currency"] == {"GNF": "0.00"}


async def test_create_transfer_reliquat_fee_consumes_entry_fully(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_a, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "85000", "currency": "GNF"}]},
        headers=_auth_headers(token_a),
    )
    entry_id = entry.json()["id"]

    response = await client.post(
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
    assert response.status_code == 201
    assert response.json()["client_id"] is None

    entry_after = await client.get(f"/api/v1/entries/{entry_id}", headers=_auth_headers(token_a))
    assert entry_after.json()["status"] == "consumed"
    assert entry_after.json()["available_by_currency"] == {"GNF": "0.00"}


async def test_create_transfer_reliquat_client_credit(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_a, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "85000", "currency": "GNF"}]},
        headers=_auth_headers(token_a),
    )
    entry_id = entry.json()["id"]

    response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
            "reliquat_action": "client_credit",
            "client_name": "Bhoye",
            "client_phone": "+224600011144",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["client_id"] is not None
    assert body["client_debt_amount"] is None

    entry_after = await client.get(f"/api/v1/entries/{entry_id}", headers=_auth_headers(token_a))
    assert entry_after.json()["status"] == "consumed"

    clients_response = await client.get("/api/v1/clients", headers=_auth_headers(token_a))
    clients = clients_response.json()
    assert len(clients) == 1
    assert clients[0]["id"] == body["client_id"]
    assert clients[0]["balance"] == "-5000.00"


async def test_transfer_exceeding_entry_available_without_client_rejected(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_a, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "50000", "currency": "GNF"}]},
        headers=_auth_headers(token_a),
    )
    entry_id = entry.json()["id"]

    response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 409
    assert "client" in response.json()["detail"]


async def test_direct_transfer_without_entry_with_client_creates_full_debt(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)

    response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
            "client_name": "Bhoye",
            "client_phone": "+224600011122",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["client_debt_amount"] == "80000.00"
    assert body["client_id"] is not None

    clients_response = await client.get("/api/v1/clients", headers=_auth_headers(token_a))
    clients = clients_response.json()
    assert len(clients) == 1
    assert clients[0]["id"] == body["client_id"]
    assert clients[0]["phone"] == "+224600011122"
    assert clients[0]["balance"] == "80000.00"


async def test_direct_transfer_without_entry_and_without_client_has_no_debt(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)

    response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["client_debt_amount"] is None
    assert body["client_id"] is None


async def test_only_collaborator_can_approve_and_balance_updates(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)

    create_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = create_response.json()["id"]

    self_approve = await client.post(
        f"/api/v1/transfers/{transfer_id}/approve", json={}, headers=_auth_headers(token_a)
    )
    assert self_approve.status_code == 403

    approve_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/approve", json={}, headers=_auth_headers(token_b)
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    double_approve = await client.post(
        f"/api/v1/transfers/{transfer_id}/approve", json={}, headers=_auth_headers(token_b)
    )
    assert double_approve.status_code == 409

    balance_a = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_a)
    )
    balance_b = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_b)
    )
    assert balance_a.json()["balance"] == "-80000.00"
    assert balance_b.json()["balance"] == "80000.00"


async def test_reject_transfer_reverts_entry_and_leaves_balance_untouched(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_a, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "85000", "currency": "GNF"}]},
        headers=_auth_headers(token_a),
    )
    entry_id = entry.json()["id"]

    create_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = create_response.json()["id"]

    reject_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/reject",
        json={"reason": "Bénéficiaire introuvable"},
        headers=_auth_headers(token_b),
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"
    assert reject_response.json()["rejection_reason"] == "Bénéficiaire introuvable"

    entry_after = await client.get(f"/api/v1/entries/{entry_id}", headers=_auth_headers(token_a))
    assert entry_after.json()["status"] == "unallocated"
    assert entry_after.json()["available_by_currency"] == {"GNF": "85000.00"}

    balance_a = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_a)
    )
    assert balance_a.json()["balance"] == "0"


async def test_creator_can_cancel_pending_transfer_and_entry_reverts(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_a, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "85000", "currency": "GNF"}]},
        headers=_auth_headers(token_a),
    )
    entry_id = entry.json()["id"]

    create_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = create_response.json()["id"]

    cancel_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/cancel", headers=_auth_headers(token_a)
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    entry_after = await client.get(f"/api/v1/entries/{entry_id}", headers=_auth_headers(token_a))
    assert entry_after.json()["status"] == "unallocated"
    assert entry_after.json()["available_by_currency"] == {"GNF": "85000.00"}


async def test_counterparty_cannot_cancel_transfer(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    create_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/transfers/{transfer_id}/cancel", headers=_auth_headers(token_b)
    )
    assert response.status_code == 403


async def test_approved_transfer_cannot_be_cancelled(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    create_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = create_response.json()["id"]
    await client.post(f"/api/v1/transfers/{transfer_id}/approve", json={}, headers=_auth_headers(token_b))

    response = await client.post(
        f"/api/v1/transfers/{transfer_id}/cancel", headers=_auth_headers(token_a)
    )
    assert response.status_code == 409


async def test_reject_requires_reason(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    create_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/transfers/{transfer_id}/reject", json={"reason": ""}, headers=_auth_headers(token_b)
    )
    assert response.status_code == 422


async def test_private_rate_used_hidden_from_counterparty(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    await client.post(
        "/api/v1/private-rates",
        json={"collaboration_id": collaboration_id, "currency": "GNF", "rate": "17.5"},
        headers=_auth_headers(token_a),
    )

    create_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = create_response.json()["id"]
    # A (owner of the private rate) sees its own rate.
    assert create_response.json()["private_rate_used"] == "17.500000"

    view_from_a = await client.get(f"/api/v1/transfers/{transfer_id}", headers=_auth_headers(token_a))
    assert view_from_a.json()["private_rate_used"] == "17.500000"

    # B (the counterparty collaborator) must never see A's private commercial rate.
    view_from_b = await client.get(f"/api/v1/transfers/{transfer_id}", headers=_auth_headers(token_b))
    assert view_from_b.json()["private_rate_used"] is None

    list_from_b = await client.get("/api/v1/transfers", headers=_auth_headers(token_b))
    assert all(item["private_rate_used"] is None for item in list_from_b.json())

    approve_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/approve", json={}, headers=_auth_headers(token_b)
    )
    assert approve_response.json()["private_rate_used"] is None


async def test_approved_transfer_cannot_be_rejected(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)

    create_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = create_response.json()["id"]
    await client.post(f"/api/v1/transfers/{transfer_id}/approve", json={}, headers=_auth_headers(token_b))

    reject_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/reject",
        json={"reason": "Trop tard"},
        headers=_auth_headers(token_b),
    )
    assert reject_response.status_code == 409


async def test_third_party_company_cannot_access_transfer(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    create_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = create_response.json()["id"]

    _, token_c = await _register_and_login_owner(
        client, company_name="Entreprise C", company_phone="+224870000030"
    )
    response = await client.get(f"/api/v1/transfers/{transfer_id}", headers=_auth_headers(token_c))
    assert response.status_code == 404


async def test_employee_permission_gating(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224870000040"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224870000041"
    )
    create_collab = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_collab.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))

    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Sans Droit",
            "phone": "+224871111111",
            "password": "EmployeePass123!",
            "permissions": [],
        },
        headers=_auth_headers(token_a),
    )
    employee_matricule = create_response.json()["matricule"]
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"matricule": employee_matricule, "password": "EmployeePass123!"},
    )
    employee_token = login_response.json()["access_token"]

    response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(employee_token),
    )
    assert response.status_code == 403
