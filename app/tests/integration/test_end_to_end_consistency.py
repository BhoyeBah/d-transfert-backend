from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.transfer import Transfer, TransferStatus, TransferStatusHistory


async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise E2E",
        "company_phone": "+224910000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner E2E",
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


async def test_full_chain_wallet_entry_transfer_payment_reconciles(client, db_session):
    # Setup: two collaborating companies A and B, GNF, rate 16 (1 XOF = 16 GNF).
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224910000010"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224910000011"
    )
    create_collab = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_collab.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))
    await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "16"},
        headers=_auth_headers(token_a),
    )

    # A receives 100000 GNF from a client into a wallet via an entry.
    cash_a = await _create_wallet(client, token_a, "CASH")
    entry_a = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_a, "amount": "100000", "currency": "GNF"}]},
        headers=_auth_headers(token_a),
    )
    entry_a_id = entry_a.json()["id"]

    wallet_a_after_entry = await client.get(f"/api/v1/wallets/{cash_a}", headers=_auth_headers(token_a))
    assert wallet_a_after_entry.json()["balance"] == "100000.00"

    # A transforms 80000 GNF of that entry into a transfer to B (reliquat of 20000 stays available).
    transfer_response = await client.post(
        "/api/v1/transfers",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_a_id,
            "amount": "80000",
            "currency": "GNF",
            "beneficiary_phone": "+224600000099",
            "send_mode": "cash",
        },
        headers=_auth_headers(token_a),
    )
    transfer_id = transfer_response.json()["id"]

    entry_a_after_transfer = await client.get(
        f"/api/v1/entries/{entry_a_id}", headers=_auth_headers(token_a)
    )
    assert entry_a_after_transfer.json()["status"] == "partially_allocated"
    assert entry_a_after_transfer.json()["available_by_currency"] == {"GNF": "20000.00"}

    # Wallet balance is untouched by the transfer itself (only the entry moved real cash).
    wallet_a_after_transfer = await client.get(f"/api/v1/wallets/{cash_a}", headers=_auth_headers(token_a))
    assert wallet_a_after_transfer.json()["balance"] == "100000.00"

    # B approves: collaborator balance updates, A owes B 80000 GNF. B pays the beneficiary
    # from its own wallet, which must be debited by the converted amount.
    wallet_b_payout = await _create_wallet(client, token_b, "PAYOUT", initial_balance="1000000")
    await client.post(
        f"/api/v1/transfers/{transfer_id}/approve",
        json={"wallet_id": wallet_b_payout},
        headers=_auth_headers(token_b),
    )

    wallet_b_payout_after = await client.get(
        f"/api/v1/wallets/{wallet_b_payout}", headers=_auth_headers(token_b)
    )
    assert wallet_b_payout_after.json()["balance"] == "920000.00"

    balance_a = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_a)
    )
    balance_b = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_b)
    )
    assert balance_a.json()["balance"] == "-80000.00"
    assert balance_b.json()["balance"] == "80000.00"

    # B receives 85000 GNF from a client into a wallet via an entry, and uses 80000 of it
    # to settle A's debt via a payment. B keeps 5000 GNF as reliquat.
    cash_b = await _create_wallet(client, token_b, "CASH")
    entry_b = await client.post(
        "/api/v1/entries",
        json={"lines": [{"wallet_id": cash_b, "amount": "85000", "currency": "GNF"}]},
        headers=_auth_headers(token_b),
    )
    entry_b_id = entry_b.json()["id"]

    payment_response = await client.post(
        "/api/v1/payments",
        json={
            "collaboration_id": collaboration_id,
            "entry_id": entry_b_id,
            "amount": "80000",
            "currency": "GNF",
        },
        headers=_auth_headers(token_b),
    )
    payment_id = payment_response.json()["id"]

    # A (the "concerned collaborator" whose debt is being settled) approves the payment.
    await client.post(f"/api/v1/payments/{payment_id}/approve", json={}, headers=_auth_headers(token_a))

    entry_b_after_payment = await client.get(
        f"/api/v1/entries/{entry_b_id}", headers=_auth_headers(token_b)
    )
    assert entry_b_after_payment.json()["status"] == "partially_allocated"
    assert entry_b_after_payment.json()["available_by_currency"] == {"GNF": "5000.00"}

    # Debt fully settled: both sides now see a zero balance.
    balance_a_final = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_a)
    )
    balance_b_final = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(token_b)
    )
    assert balance_a_final.json()["balance"] == "0.00"
    assert balance_b_final.json()["balance"] == "0.00"

    # No hard deletion anywhere: the transfer/payment rows and their full status history persist.
    transfer_row = await db_session.get(Transfer, transfer_id)
    assert transfer_row is not None
    assert transfer_row.status == TransferStatus.APPROVED

    history_result = await db_session.execute(
        select(TransferStatusHistory).where(TransferStatusHistory.transfer_id == transfer_id)
    )
    history_rows = history_result.scalars().all()
    assert len(history_rows) == 2  # pending -> approved
    assert {row.new_status for row in history_rows} == {TransferStatus.PENDING, TransferStatus.APPROVED}

    # Audit trail captured the sensitive actions end-to-end.
    audit_result = await db_session.execute(
        select(AuditLog.action).where(AuditLog.action.in_(["transfer.approve", "payment.approve"]))
    )
    actions = {row[0] for row in audit_result.all()}
    assert actions == {"transfer.approve", "payment.approve"}
