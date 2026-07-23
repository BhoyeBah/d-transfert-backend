import uuid


def _png_file(name="preuve.png"):
    # Minimal valid 1x1 PNG.
    content = bytes.fromhex(
        "89504e470d0a1a0a0000000d494844520000000100000001080600000"
        "01f15c4890000000a49444154789c6360000002000100feff03000006"
        "0005a5d996690000000049454e44ae426082"
    )
    return name, content, "image/png"


async def _upload_proof(client, token, transfer_id):
    name, content, content_type = _png_file()
    response = await client.post(
        f"/api/v1/transfers/{transfer_id}/proofs",
        files={"file": (name, content, content_type)},
        headers=_auth_headers(token),
    )
    return response.json()["id"]


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


async def _create_wallet(client, token, code, currency="GNF", initial_balance=None):
    payload = {"name": code, "code": code, "type": "cash", "currency": currency}
    if initial_balance is not None:
        payload["initial_balance"] = initial_balance
    response = await client.post("/api/v1/wallets", json=payload, headers=_auth_headers(token))
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
    # A private sending rate is required before A can create a transfer; register a broad
    # (company-wide) one matching the collaboration currency so callers don't need to set it
    # up themselves unless they're specifically testing private-rate scoping/conversion.
    await client.post(
        "/api/v1/private-rates",
        json={"currency": currency, "rate": "15"},
        headers=_auth_headers(token_a),
    )
    return collaboration_id, (matricule_a, token_a), (matricule_b, token_b)


async def test_create_transfer_with_currency_conversion(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    await client.post(
        "/api/v1/private-rates",
        json={"currency": "XOF", "rate": "15.5"},
        headers=_auth_headers(token_a),
    )

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
    # The private (sending) rate drives the conversion the collaborator must pay out;
    # the collaborative rate is only recorded for reference/settlement purposes.
    assert body["private_rate_used"] == "15.500000"
    assert body["collaborative_rate_used"] == "16.000000"
    assert body["converted_amount"] == "77500.00"


async def test_private_rate_exact_pair_preferred_over_wildcard(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    await client.post(
        "/api/v1/private-rates",
        json={"currency": "XOF", "rate": "15.5"},
        headers=_auth_headers(token_a),
    )
    await client.post(
        "/api/v1/private-rates",
        json={"currency": "XOF", "target_currency": "GNF", "rate": "16.2"},
        headers=_auth_headers(token_a),
    )

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
    assert response.json()["private_rate_used"] == "16.200000"


async def test_private_rate_pair_scoped_to_different_target_currency_not_used(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    await client.post(
        "/api/v1/private-rates",
        json={"currency": "XOF", "target_currency": "USD", "rate": "1500"},
        headers=_auth_headers(token_a),
    )

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
    assert response.status_code == 409


async def test_private_rate_with_country_set_is_still_found(client):
    # The "Pays" field on a private rate is informational only — a transfer has no destination
    # country to match against, so a rate saved with a country must still be usable, not silently
    # invisible to lookup (regression: country used to be matched with strict equality against
    # the literal None the transfer service always passed in).
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    await client.post(
        "/api/v1/private-rates",
        json={"currency": "XOF", "rate": "15.5", "country": "Sénégal"},
        headers=_auth_headers(token_a),
    )

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
    assert response.json()["private_rate_used"] == "15.500000"
    assert response.json()["converted_amount"] == "77500.00"


async def test_create_transfer_without_private_rate_is_rejected(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise Sans Taux", company_phone="+224870000030"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise Sans Taux B", company_phone="+224870000031"
    )
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))

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


async def test_cancel_transfer_reverses_client_debt(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)

    create_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
            "client_name": "Bhoye",
            "client_phone": "+224600011166",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = create_response.json()["id"]
    client_id = create_response.json()["client_id"]

    clients_before = await client.get("/api/v1/clients", headers=_auth_headers(token_a))
    assert clients_before.json()[0]["balance"] == "80000.00"

    cancel_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/cancel", headers=_auth_headers(token_a)
    )
    assert cancel_response.status_code == 200

    client_after = await client.get(f"/api/v1/clients/{client_id}", headers=_auth_headers(token_a))
    assert client_after.json()["balance"] == "0.00"


async def test_reject_transfer_reverses_client_debt(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)

    create_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
            "client_name": "Bhoye",
            "client_phone": "+224600011177",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = create_response.json()["id"]
    client_id = create_response.json()["client_id"]

    reject_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/reject",
        json={"reason": "Bénéficiaire introuvable"},
        headers=_auth_headers(token_b),
    )
    assert reject_response.status_code == 200

    client_after = await client.get(f"/api/v1/clients/{client_id}", headers=_auth_headers(token_a))
    assert client_after.json()["balance"] == "0.00"


async def test_reject_transfer_reverses_reliquat_client_credit(client):
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
            "reliquat_action": "client_credit",
            "client_name": "Bhoye",
            "client_phone": "+224600011188",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = create_response.json()["id"]
    client_id = create_response.json()["client_id"]

    clients_before = await client.get(f"/api/v1/clients/{client_id}", headers=_auth_headers(token_a))
    assert clients_before.json()["balance"] == "-5000.00"

    reject_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/reject",
        json={"reason": "Bénéficiaire introuvable"},
        headers=_auth_headers(token_b),
    )
    assert reject_response.status_code == 200

    client_after = await client.get(f"/api/v1/clients/{client_id}", headers=_auth_headers(token_a))
    assert client_after.json()["balance"] == "0.00"


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


async def test_approve_transfer_requires_wallet_id(client):
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
        f"/api/v1/transfers/{transfer_id}/approve", json={}, headers=_auth_headers(token_b)
    )
    assert response.status_code == 422


async def test_approve_transfer_rejects_wallet_from_other_company(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    wallet_a_id = await _create_wallet(client, token_a, "CASHA", currency="GNF", initial_balance="1000000")
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
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_a_id, "proof_id": str(uuid.uuid4())},
        headers=_auth_headers(token_b),
    )
    assert response.status_code == 404


async def test_approve_transfer_rejects_wallet_currency_mismatch(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    wallet_b_xof = await _create_wallet(client, token_b, "CASHXOF", currency="XOF", initial_balance="1000000")
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
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_b_xof, "proof_id": str(uuid.uuid4())},
        headers=_auth_headers(token_b),
    )
    assert response.status_code == 409


async def test_approve_transfer_rejects_insufficient_wallet_balance(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    wallet_b_id = await _create_wallet(client, token_b, "CASHB", currency="GNF", initial_balance="1000")
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
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_b_id, "proof_id": str(uuid.uuid4())},
        headers=_auth_headers(token_b),
    )
    assert response.status_code == 422


async def test_approve_transfer_requires_proof_id(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    wallet_b_id = await _create_wallet(client, token_b, "CASHB", currency="GNF", initial_balance="1000000")
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
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_b_id},
        headers=_auth_headers(token_b),
    )
    assert response.status_code == 422


async def test_approve_transfer_rejects_proof_from_wrong_company(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    wallet_b_id = await _create_wallet(client, token_b, "CASHB", currency="GNF", initial_balance="1000000")
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
    # A (the creator, not the approver) uploads a proof of its own.
    proof_id = await _upload_proof(client, token_a, transfer_id)

    response = await client.post(
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_b_id, "proof_id": proof_id},
        headers=_auth_headers(token_b),
    )
    assert response.status_code == 404


async def test_only_collaborator_can_approve_and_balance_updates(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    wallet_b_id = await _create_wallet(client, token_b, "CASHB", currency="GNF", initial_balance="1000000")

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
    proof_id = await _upload_proof(client, token_b, transfer_id)

    self_approve = await client.post(
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_b_id, "proof_id": proof_id},
        headers=_auth_headers(token_a),
    )
    assert self_approve.status_code == 403

    approve_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_b_id, "proof_id": proof_id},
        headers=_auth_headers(token_b),
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"
    assert approve_response.json()["wallet_id"] == wallet_b_id
    assert approve_response.json()["proof_id"] == proof_id

    double_approve = await client.post(
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_b_id, "proof_id": proof_id},
        headers=_auth_headers(token_b),
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

    wallet_b_after = await client.get(f"/api/v1/wallets/{wallet_b_id}", headers=_auth_headers(token_b))
    assert wallet_b_after.json()["balance"] == "920000.00"


async def test_transfer_target_currency_can_differ_from_collaboration_currency(client):
    # Reproduces the reported case: a collaboration settled in XOF (the collaboration currency
    # only drives the mutual balance / collaborator payments), but the sender wants to pay THIS
    # beneficiary in GNF using their own XOF -> GNF private rate — decoupled from whatever
    # currency the collaboration itself happens to be fixed to.
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(
        client, currency="XOF"
    )
    await client.post(
        "/api/v1/private-rates",
        json={"currency": "XOF", "target_currency": "GNF", "rate": "16.2"},
        headers=_auth_headers(token_a),
    )
    wallet_b_xof = await _create_wallet(client, token_b, "CASHXOF", currency="XOF", initial_balance="1000000")
    wallet_b_gnf = await _create_wallet(client, token_b, "CASHGNF", currency="GNF", initial_balance="1000000")

    create_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "5000",
            "currency": "XOF",
            "target_currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["target_currency"] == "GNF"
    assert body["converted_amount"] == "81000.00"
    transfer_id = body["id"]
    proof_id = await _upload_proof(client, token_b, transfer_id)

    # The wallet used to pay the beneficiary must be in the transfer's target currency (GNF),
    # not the collaboration's currency (XOF).
    wrong_wallet = await client.post(
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_b_xof, "proof_id": proof_id},
        headers=_auth_headers(token_b),
    )
    assert wrong_wallet.status_code == 409

    approve_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_b_gnf, "proof_id": proof_id},
        headers=_auth_headers(token_b),
    )
    assert approve_response.status_code == 200

    balance_b = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_b)
    )
    assert balance_b.json()["balance"] == "81000.00"


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
    wallet_b_id = await _create_wallet(client, token_b, "CASHB", currency="GNF", initial_balance="1000000")
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
    proof_id = await _upload_proof(client, token_b, transfer_id)
    await client.post(
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_b_id, "proof_id": proof_id},
        headers=_auth_headers(token_b),
    )

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


async def test_private_rate_scoped_to_operation_type_takes_priority(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    await client.post(
        "/api/v1/private-rates",
        json={"collaboration_id": collaboration_id, "currency": "GNF", "rate": "17.5"},
        headers=_auth_headers(token_a),
    )
    await client.post(
        "/api/v1/private-rates",
        json={
            "collaboration_id": collaboration_id,
            "currency": "GNF",
            "rate": "19.0",
            "operation_type": "wave",
        },
        headers=_auth_headers(token_a),
    )

    cash_transfer = await client.post(
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
    assert cash_transfer.json()["private_rate_used"] == "17.500000"

    wave_transfer = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "wave",
        },
        headers=_auth_headers(token_a),
    )
    assert wave_transfer.json()["private_rate_used"] == "19.000000"


async def test_private_rate_used_hidden_from_counterparty(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    wallet_b_id = await _create_wallet(client, token_b, "CASHB", currency="GNF", initial_balance="1000000")
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

    proof_id = await _upload_proof(client, token_b, transfer_id)
    approve_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_b_id, "proof_id": proof_id},
        headers=_auth_headers(token_b),
    )
    assert approve_response.json()["private_rate_used"] is None


async def test_approved_transfer_cannot_be_rejected(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    wallet_b_id = await _create_wallet(client, token_b, "CASHB", currency="GNF", initial_balance="1000000")

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
    proof_id = await _upload_proof(client, token_b, transfer_id)
    await client.post(
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_b_id, "proof_id": proof_id},
        headers=_auth_headers(token_b),
    )

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


async def test_transfers_page_search_sort_pagination(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)

    for phone, amount in [("+224600000001", "1000"), ("+224600000002", "2000"), ("+224600000003", "3000")]:
        await client.post(
            "/api/v1/transfers",
            json={
                "collaboration_id": collaboration_id,
                "amount": amount,
                "currency": "GNF",
                "beneficiary_phone": phone,
                "send_mode": "cash",
            },
            headers=_auth_headers(token_a),
        )

    response = await client.get(
        "/api/v1/transfers/page",
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
        "/api/v1/transfers/page", params={"search": "600000002"}, headers=_auth_headers(token_a)
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["beneficiary_phone"] == "+224600000002"
