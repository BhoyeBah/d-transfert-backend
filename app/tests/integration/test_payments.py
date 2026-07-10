async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise Paiement",
        "company_phone": "+224880000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Paiement",
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


async def _create_wallet(client, token, code, currency="GNF", initial_balance="0"):
    response = await client.post(
        "/api/v1/wallets",
        json={
            "name": code,
            "code": code,
            "type": "cash",
            "currency": currency,
            "initial_balance": initial_balance,
        },
        headers=_auth_headers(token),
    )
    return response.json()["id"]


async def _setup_accepted_collaboration(client, rate="16", currency="GNF"):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224880000010"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224880000011"
    )
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": currency, "initial_rate": rate},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))
    # Transfers (used here as setup to create collaborator debt) require a private sending
    # rate to be configured before they can be created.
    await client.post(
        "/api/v1/private-rates",
        json={"currency": currency, "rate": "15"},
        headers=_auth_headers(token_a),
    )
    return collaboration_id, (matricule_a, token_a), (matricule_b, token_b)


async def _create_and_approve_transfer(client, collaboration_id, token_a, token_b, amount="80000"):
    create_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": amount,
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = create_response.json()["id"]
    await client.post(f"/api/v1/transfers/{transfer_id}/approve", json={}, headers=_auth_headers(token_b))


async def test_payment_from_entry_settles_existing_debt(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)

    await _create_and_approve_transfer(client, collaboration_id, token_a, token_b, amount="80000")

    balance_a_before = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_a)
    )
    assert balance_a_before.json()["balance"] == "-80000.00"

    cash_id = await _create_wallet(client, token_b, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "85000", "currency": "GNF"}]},
        headers=_auth_headers(token_b),
    )
    entry_id = entry.json()["id"]

    payment_response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "amount": "80000",
            "currency": "GNF",
            "note": "Règlement dette A",
        },
        headers=_auth_headers(token_b),
    )
    assert payment_response.status_code == 201
    payment_id = payment_response.json()["id"]

    approve_response = await client.post(
        f"/api/v1/payments/{payment_id}/approve", json={}, headers=_auth_headers(token_a)
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    balance_a_after = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_a)
    )
    balance_b_after = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_b)
    )
    assert balance_a_after.json()["balance"] == "0.00"
    assert balance_b_after.json()["balance"] == "0.00"

    entry_after = await client.get(f"/api/v1/entries/{entry_id}", headers=_auth_headers(token_b))
    assert entry_after.json()["status"] == "partially_allocated"
    assert entry_after.json()["available_by_currency"] == {"GNF": "5000.00"}


async def test_payment_direct_wallet_outflow_deferred_to_approval(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    wallet_id = await _create_wallet(client, token_a, "CASH", initial_balance="100000")

    create_response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "wallet_id": wallet_id,
            "amount": "30000",
            "currency": "GNF",
        },
        headers=_auth_headers(token_a),
    )
    assert create_response.status_code == 201
    payment_id = create_response.json()["id"]

    wallet_before_approval = await client.get(
        f"/api/v1/wallets/{wallet_id}", headers=_auth_headers(token_a)
    )
    assert wallet_before_approval.json()["balance"] == "100000.00"

    approve_response = await client.post(
        f"/api/v1/payments/{payment_id}/approve", json={}, headers=_auth_headers(token_b)
    )
    assert approve_response.status_code == 200

    wallet_after_approval = await client.get(
        f"/api/v1/wallets/{wallet_id}", headers=_auth_headers(token_a)
    )
    assert wallet_after_approval.json()["balance"] == "70000.00"

    balance_a = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_a)
    )
    balance_b = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_b)
    )
    assert balance_a.json()["balance"] == "-30000.00"
    assert balance_b.json()["balance"] == "30000.00"


async def test_payment_reliquat_fee_consumes_entry_fully(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_a, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "85000", "currency": "GNF"}]},
        headers=_auth_headers(token_a),
    )
    entry_id = entry.json()["id"]

    response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "amount": "80000",
            "currency": "GNF",
            "reliquat_action": "fee",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201
    assert response.json()["client_id"] is None

    entry_after = await client.get(f"/api/v1/entries/{entry_id}", headers=_auth_headers(token_a))
    assert entry_after.json()["status"] == "consumed"


async def test_payment_reliquat_client_credit(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_a, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "85000", "currency": "GNF"}]},
        headers=_auth_headers(token_a),
    )
    entry_id = entry.json()["id"]

    response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "amount": "80000",
            "currency": "GNF",
            "reliquat_action": "client_credit",
            "client_name": "Bhoye",
            "client_phone": "+224600011155",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["client_id"] is not None

    clients_response = await client.get("/api/v1/clients", headers=_auth_headers(token_a))
    clients = clients_response.json()
    assert len(clients) == 1
    assert clients[0]["balance"] == "-5000.00"


async def test_direct_payment_without_entry_with_client_creates_full_debt(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)

    response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "amount": "30000",
            "currency": "GNF",
            "client_name": "Bhoye",
            "client_phone": "+224600011133",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["client_debt_amount"] == "30000.00"
    assert body["client_id"] is not None

    clients_response = await client.get("/api/v1/clients", headers=_auth_headers(token_a))
    clients = clients_response.json()
    assert len(clients) == 1
    assert clients[0]["id"] == body["client_id"]
    assert clients[0]["balance"] == "30000.00"


async def test_cancel_payment_reverses_client_debt(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)

    create_response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "amount": "30000",
            "currency": "GNF",
            "client_name": "Bhoye",
            "client_phone": "+224600011199",
        },
        headers=_auth_headers(token_a),
    )
    payment_id = create_response.json()["id"]
    client_id = create_response.json()["client_id"]

    cancel_response = await client.post(
        f"/api/v1/payments/{payment_id}/cancel", headers=_auth_headers(token_a)
    )
    assert cancel_response.status_code == 200

    client_after = await client.get(f"/api/v1/clients/{client_id}", headers=_auth_headers(token_a))
    assert client_after.json()["balance"] == "0.00"


async def test_reject_payment_reverses_client_debt(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)

    create_response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "amount": "30000",
            "currency": "GNF",
            "client_name": "Bhoye",
            "client_phone": "+224600011200",
        },
        headers=_auth_headers(token_a),
    )
    payment_id = create_response.json()["id"]
    client_id = create_response.json()["client_id"]

    reject_response = await client.post(
        f"/api/v1/payments/{payment_id}/reject",
        json={"reason": "Montant incorrect"},
        headers=_auth_headers(token_b),
    )
    assert reject_response.status_code == 200

    client_after = await client.get(f"/api/v1/clients/{client_id}", headers=_auth_headers(token_a))
    assert client_after.json()["balance"] == "0.00"


async def test_direct_payment_without_entry_and_without_client_has_no_debt(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)

    response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "amount": "30000",
            "currency": "GNF",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["client_debt_amount"] is None
    assert body["client_id"] is None


async def test_payment_wallet_and_entry_mutually_exclusive(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_a, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "10000", "currency": "GNF"}]},
        headers=_auth_headers(token_a),
    )
    entry_id = entry.json()["id"]

    response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "wallet_id": cash_id,
            "amount": "1000",
            "currency": "GNF",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 422


async def test_only_other_party_can_approve_and_double_approval_rejected(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)

    create_response = await client.post(
        "/api/v1/payments",
        json={"collaboration_id": collaboration_id, "amount": "10000", "currency": "GNF"},
        headers=_auth_headers(token_a),
    )
    payment_id = create_response.json()["id"]

    self_approve = await client.post(
        f"/api/v1/payments/{payment_id}/approve", json={}, headers=_auth_headers(token_a)
    )
    assert self_approve.status_code == 403

    approve_response = await client.post(
        f"/api/v1/payments/{payment_id}/approve", json={}, headers=_auth_headers(token_b)
    )
    assert approve_response.status_code == 200

    double_approve = await client.post(
        f"/api/v1/payments/{payment_id}/approve", json={}, headers=_auth_headers(token_b)
    )
    assert double_approve.status_code == 409


async def test_approved_payment_cannot_be_rejected(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)

    create_response = await client.post(
        "/api/v1/payments",
        json={"collaboration_id": collaboration_id, "amount": "10000", "currency": "GNF"},
        headers=_auth_headers(token_a),
    )
    payment_id = create_response.json()["id"]
    await client.post(f"/api/v1/payments/{payment_id}/approve", json={}, headers=_auth_headers(token_b))

    reject_response = await client.post(
        f"/api/v1/payments/{payment_id}/reject",
        json={"reason": "Trop tard"},
        headers=_auth_headers(token_b),
    )
    assert reject_response.status_code == 409


async def test_payment_requires_accepted_collaboration(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224880000020"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224880000021"
    )
    create_collab = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_collab.json()["id"]

    response = await client.post(
        "/api/v1/payments",
        json={"collaboration_id": collaboration_id, "amount": "1000", "currency": "GNF"},
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 409


async def test_reject_payment_reverts_entry_and_leaves_balance_untouched(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_b, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "50000", "currency": "GNF"}]},
        headers=_auth_headers(token_b),
    )
    entry_id = entry.json()["id"]

    create_response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "amount": "30000",
            "currency": "GNF",
        },
        headers=_auth_headers(token_b),
    )
    payment_id = create_response.json()["id"]

    reject_response = await client.post(
        f"/api/v1/payments/{payment_id}/reject",
        json={"reason": "Montant incorrect"},
        headers=_auth_headers(token_a),
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"

    entry_after = await client.get(f"/api/v1/entries/{entry_id}", headers=_auth_headers(token_b))
    assert entry_after.json()["status"] == "unallocated"
    assert entry_after.json()["available_by_currency"] == {"GNF": "50000.00"}

    balance = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_a)
    )
    assert balance.json()["balance"] == "0"


async def test_creator_can_cancel_pending_payment_and_entry_reverts(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_b, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "50000", "currency": "GNF"}]},
        headers=_auth_headers(token_b),
    )
    entry_id = entry.json()["id"]

    create_response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "amount": "30000",
            "currency": "GNF",
        },
        headers=_auth_headers(token_b),
    )
    payment_id = create_response.json()["id"]

    cancel_response = await client.post(
        f"/api/v1/payments/{payment_id}/cancel", headers=_auth_headers(token_b)
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    entry_after = await client.get(f"/api/v1/entries/{entry_id}", headers=_auth_headers(token_b))
    assert entry_after.json()["status"] == "unallocated"
    assert entry_after.json()["available_by_currency"] == {"GNF": "50000.00"}


async def test_counterparty_cannot_cancel_payment(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    create_response = await client.post(
        "/api/v1/payments",
        json={"collaboration_id": collaboration_id, "amount": "10000", "currency": "GNF"},
        headers=_auth_headers(token_b),
    )
    payment_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/payments/{payment_id}/cancel", headers=_auth_headers(token_a)
    )
    assert response.status_code == 403


async def test_approved_payment_cannot_be_cancelled(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    create_response = await client.post(
        "/api/v1/payments",
        json={"collaboration_id": collaboration_id, "amount": "10000", "currency": "GNF"},
        headers=_auth_headers(token_b),
    )
    payment_id = create_response.json()["id"]
    await client.post(f"/api/v1/payments/{payment_id}/approve", json={}, headers=_auth_headers(token_a))

    response = await client.post(
        f"/api/v1/payments/{payment_id}/cancel", headers=_auth_headers(token_b)
    )
    assert response.status_code == 409


async def test_reject_requires_reason(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    create_response = await client.post(
        "/api/v1/payments",
        json={"collaboration_id": collaboration_id, "amount": "10000", "currency": "GNF"},
        headers=_auth_headers(token_a),
    )
    payment_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/payments/{payment_id}/reject", json={"reason": ""}, headers=_auth_headers(token_b)
    )
    assert response.status_code == 422


async def test_third_party_company_cannot_access_payment(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    create_response = await client.post(
        "/api/v1/payments",
        json={"collaboration_id": collaboration_id, "amount": "10000", "currency": "GNF"},
        headers=_auth_headers(token_a),
    )
    payment_id = create_response.json()["id"]

    _, token_c = await _register_and_login_owner(
        client, company_name="Entreprise C", company_phone="+224880000030"
    )
    response = await client.get(f"/api/v1/payments/{payment_id}", headers=_auth_headers(token_c))
    assert response.status_code == 404


async def test_employee_permission_gating(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224880000040"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224880000041"
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
            "phone": "+224881111111",
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
        "/api/v1/payments",
        json={"collaboration_id": collaboration_id, "amount": "10000", "currency": "GNF"},
        headers=_auth_headers(employee_token),
    )
    assert response.status_code == 403


async def test_payments_page_search_sort_pagination(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)

    for client_name, amount in [("Alice", "1000"), ("Bob", "2000"), ("Charlie", "3000")]:
        await client.post(
            "/api/v1/payments",
            json={
                "collaboration_id": collaboration_id,
                "amount": amount,
                "currency": "GNF",
                "client_name": client_name,
                "client_phone": "+224600000000",
            },
            headers=_auth_headers(token_a),
        )

    response = await client.get(
        "/api/v1/payments/page",
        params={"page": 1, "page_size": 2, "sort_by": "amount", "sort_dir": "asc"},
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert [item["amount"] for item in body["items"]] == ["1000.00", "2000.00"]

    response = await client.get(
        "/api/v1/payments/page", params={"search": "bob"}, headers=_auth_headers(token_a)
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["client_name"] == "Bob"
