from app.core.config import get_settings
from app.services import proof_service


async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise Preuve",
        "company_phone": "+224890000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Preuve",
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


async def _setup_accepted_collaboration(client, rate="16", currency="GNF"):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224890000010"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224890000011"
    )
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": currency, "initial_rate": rate},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))
    await client.post(
        "/api/v1/private-rates",
        json={"currency": currency, "rate": "15"},
        headers=_auth_headers(token_a),
    )
    return collaboration_id, (matricule_a, token_a), (matricule_b, token_b)


async def _create_transfer(client, collaboration_id, token_a):
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
    return create_response.json()["id"]


async def _create_payment(client, collaboration_id, token_a):
    create_response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "amount": "80000",
            "currency": "GNF",
        },
        headers=_auth_headers(token_a),
    )
    return create_response.json()["id"]


def _png_file(name="recu.png"):
    # Minimal valid 1x1 PNG.
    content = bytes.fromhex(
        "89504e470d0a1a0a0000000d494844520000000100000001080600000"
        "01f15c4890000000a49444154789c6360000002000100feff03000006"
        "0005a5d996690000000049454e44ae426082"
    )
    return name, content, "image/png"


async def test_creator_can_upload_and_list_transfer_proof(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)
    transfer_id = await _create_transfer(client, collaboration_id, token_a)

    name, content, content_type = _png_file()
    upload_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/proofs",
        files={"file": (name, content, content_type)},
        data={"note": "Reçu client"},
        headers=_auth_headers(token_a),
    )
    assert upload_response.status_code == 201
    body = upload_response.json()
    assert body["transfer_id"] == transfer_id
    assert body["file_name"] == name
    assert body["note"] == "Reçu client"

    list_response = await client.get(
        f"/api/v1/transfers/{transfer_id}/proofs", headers=_auth_headers(token_a)
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


async def test_counterparty_can_upload_and_download_transfer_proof(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    transfer_id = await _create_transfer(client, collaboration_id, token_a)

    name, content, content_type = _png_file("preuve-b.png")
    upload_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/proofs",
        files={"file": (name, content, content_type)},
        headers=_auth_headers(token_b),
    )
    assert upload_response.status_code == 201
    proof_id = upload_response.json()["id"]

    download_response = await client.get(
        f"/api/v1/transfers/{transfer_id}/proofs/{proof_id}/file", headers=_auth_headers(token_a)
    )
    assert download_response.status_code == 200
    assert download_response.content == content
    assert download_response.headers["content-type"] == content_type


async def test_proof_status_pending_then_validated_on_transfer_approval(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    transfer_id = await _create_transfer(client, collaboration_id, token_a)

    name, content, content_type = _png_file()
    upload_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/proofs",
        files={"file": (name, content, content_type)},
        headers=_auth_headers(token_a),
    )
    proof_id = upload_response.json()["id"]
    assert upload_response.json()["status"] == "pending"

    wallet_response = await client.post(
        "/api/v1/wallets",
        json={"name": "PAYOUT", "code": "PAYOUT", "type": "cash", "currency": "GNF", "initial_balance": "1000000"},
        headers=_auth_headers(token_b),
    )
    wallet_id = wallet_response.json()["id"]
    # The approver (B) must attach its own proof of payment to approve.
    b_proof_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/proofs",
        files={"file": ("preuve-b.png", content, content_type)},
        headers=_auth_headers(token_b),
    )
    b_proof_id = b_proof_response.json()["id"]
    await client.post(
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_id, "proof_id": b_proof_id},
        headers=_auth_headers(token_b),
    )

    list_response = await client.get(
        f"/api/v1/transfers/{transfer_id}/proofs", headers=_auth_headers(token_a)
    )
    proof_after = next(p for p in list_response.json() if p["id"] == proof_id)
    assert proof_after["status"] == "validated"


async def test_proof_status_rejected_on_transfer_rejection(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    transfer_id = await _create_transfer(client, collaboration_id, token_a)

    name, content, content_type = _png_file()
    upload_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/proofs",
        files={"file": (name, content, content_type)},
        headers=_auth_headers(token_a),
    )
    proof_id = upload_response.json()["id"]

    await client.post(
        f"/api/v1/transfers/{transfer_id}/reject",
        json={"reason": "Bénéficiaire introuvable"},
        headers=_auth_headers(token_b),
    )

    list_response = await client.get(
        f"/api/v1/transfers/{transfer_id}/proofs", headers=_auth_headers(token_a)
    )
    proof_after = next(p for p in list_response.json() if p["id"] == proof_id)
    assert proof_after["status"] == "rejected"


async def test_proof_status_validated_on_payment_approval(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    payment_id = await _create_payment(client, collaboration_id, token_a)

    name, content, content_type = _png_file()
    upload_response = await client.post(
        f"/api/v1/payments/{payment_id}/proofs",
        files={"file": (name, content, content_type)},
        headers=_auth_headers(token_a),
    )
    proof_id = upload_response.json()["id"]

    await client.post(f"/api/v1/payments/{payment_id}/approve", json={}, headers=_auth_headers(token_b))

    list_response = await client.get(
        f"/api/v1/payments/{payment_id}/proofs", headers=_auth_headers(token_a)
    )
    proof_after = next(p for p in list_response.json() if p["id"] == proof_id)
    assert proof_after["status"] == "validated"


async def test_third_party_cannot_upload_or_list_transfer_proofs(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)
    transfer_id = await _create_transfer(client, collaboration_id, token_a)

    _, token_c = await _register_and_login_owner(
        client, company_name="Entreprise C", company_phone="+224890000030"
    )
    name, content, content_type = _png_file()
    upload_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/proofs",
        files={"file": (name, content, content_type)},
        headers=_auth_headers(token_c),
    )
    assert upload_response.status_code == 404

    list_response = await client.get(
        f"/api/v1/transfers/{transfer_id}/proofs", headers=_auth_headers(token_c)
    )
    assert list_response.status_code == 404


async def test_upload_rejects_disallowed_content_type(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)
    transfer_id = await _create_transfer(client, collaboration_id, token_a)

    upload_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/proofs",
        files={"file": ("script.exe", b"not-a-real-executable", "application/octet-stream")},
        headers=_auth_headers(token_a),
    )
    assert upload_response.status_code == 400


async def test_upload_rejects_oversized_file(client):
    collaboration_id, (_, token_a), _ = await _setup_accepted_collaboration(client)
    transfer_id = await _create_transfer(client, collaboration_id, token_a)

    settings = get_settings()
    oversized = (settings.max_upload_size_mb * 1024 * 1024) + 1
    upload_response = await client.post(
        f"/api/v1/transfers/{transfer_id}/proofs",
        files={"file": ("gros.png", b"0" * oversized, "image/png")},
        headers=_auth_headers(token_a),
    )
    assert upload_response.status_code == 400


async def test_payment_proof_upload_list_and_download(client):
    collaboration_id, (_, token_a), (_, token_b) = await _setup_accepted_collaboration(client)
    payment_id = await _create_payment(client, collaboration_id, token_a)

    name, content, content_type = _png_file("preuve-paiement.png")
    upload_response = await client.post(
        f"/api/v1/payments/{payment_id}/proofs",
        files={"file": (name, content, content_type)},
        headers=_auth_headers(token_a),
    )
    assert upload_response.status_code == 201
    proof_id = upload_response.json()["id"]

    list_response = await client.get(
        f"/api/v1/payments/{payment_id}/proofs", headers=_auth_headers(token_b)
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    download_response = await client.get(
        f"/api/v1/payments/{payment_id}/proofs/{proof_id}/file", headers=_auth_headers(token_b)
    )
    assert download_response.status_code == 200
    assert download_response.content == content


async def test_validate_file_rejects_empty_content():
    from app.core.exceptions import AppError

    try:
        proof_service._validate_file("image/png", 0)
        assert False, "expected AppError for empty file"
    except AppError as exc:
        assert "vide" in exc.message
