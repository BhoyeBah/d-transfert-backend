async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise Overflow",
        "company_phone": "+224897000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Overflow",
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
        client, company_name="Entreprise A", company_phone="+224897000010"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224897000011"
    )
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": currency, "initial_rate": rate},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))
    return collaboration_id, (matricule_a, token_a), (matricule_b, token_b)


async def test_transfer_overflow_creates_client_debt_with_explicit_client(client):
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
            "client_name": "Client Débiteur",
            "client_phone": "+224611111111",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["client_debt_amount"] == "30000.00"
    assert body["client_id"] is not None

    entry_after = await client.get(f"/api/v1/entries/{entry_id}", headers=_auth_headers(token_a))
    assert entry_after.json()["status"] == "consumed"
    assert entry_after.json()["available_by_currency"] == {"GNF": "0.00"}

    clients_response = await client.get("/api/v1/clients", headers=_auth_headers(token_a))
    clients = clients_response.json()
    assert len(clients) == 1
    assert clients[0]["balance"] == "30000.00"


async def test_transfer_overflow_uses_entry_client_when_payload_omits(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_a, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={
            "client_name": "Client Entrée",
            "client_phone": "+224622222222",
            "lines": [{"wallet_id": cash_id, "amount": "50000", "currency": "GNF"}],
        },
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
    assert response.json()["client_debt_amount"] == "30000.00"

    clients_response = await client.get("/api/v1/clients", headers=_auth_headers(token_a))
    clients = clients_response.json()
    assert clients[0]["name"] == "Client Entrée"


async def test_transfer_overflow_without_client_info_rejected(client):
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


async def test_payment_overflow_creates_client_debt(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)
    cash_id = await _create_wallet(client, token_a, "CASH")
    entry = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_id, "amount": "20000", "currency": "GNF"}]},
        headers=_auth_headers(token_a),
    )
    entry_id = entry.json()["id"]

    response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_id,
            "amount": "30000",
            "currency": "GNF",
            "client_name": "Client Paiement",
            "client_phone": "+224633333333",
        },
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["client_debt_amount"] == "10000.00"

    entry_after = await client.get(f"/api/v1/entries/{entry_id}", headers=_auth_headers(token_a))
    assert entry_after.json()["status"] == "consumed"
