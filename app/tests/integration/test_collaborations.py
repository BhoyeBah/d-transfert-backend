async def _register_and_login_owner(client, **overrides) -> tuple[str, str]:
    payload = {
        "company_name": "Entreprise Collab",
        "company_phone": "+224900000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Collab",
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


async def _setup_pair(client):
    matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise A", company_phone="+224900000010"
    )
    matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise B", company_phone="+224900000011"
    )
    return (matricule_a, token_a), (matricule_b, token_b)


async def test_request_collaboration_by_matricule(client):
    (matricule_a, token_a), (matricule_b, token_b) = await _setup_pair(client)

    response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["current_rate"] is None


async def test_cannot_collaborate_with_self(client):
    matricule_a, token_a = await _register_and_login_owner(client)

    response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_a, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 409


async def test_cannot_duplicate_active_collaboration_request(client):
    (matricule_a, token_a), (matricule_b, token_b) = await _setup_pair(client)
    payload = {"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"}
    await client.post("/api/v1/collaborations", json=payload, headers=_auth_headers(token_a))

    response = await client.post("/api/v1/collaborations", json=payload, headers=_auth_headers(token_a))
    assert response.status_code == 409


async def test_only_target_can_accept_collaboration(client):
    (matricule_a, token_a), (matricule_b, token_b) = await _setup_pair(client)
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]

    forbidden_response = await client.post(
        f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_a)
    )
    assert forbidden_response.status_code == 403

    accept_response = await client.post(
        f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b)
    )
    assert accept_response.status_code == 200
    body = accept_response.json()
    assert body["status"] == "accepted"
    assert body["current_rate"] == "16.000000"


async def test_target_can_reject_collaboration(client):
    (matricule_a, token_a), (matricule_b, token_b) = await _setup_pair(client)
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/collaborations/{collaboration_id}/reject",
        json={"reason": "Pas intéressé"},
        headers=_auth_headers(token_b),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


async def test_collaborative_rate_visible_to_both_companies(client):
    (matricule_a, token_a), (matricule_b, token_b) = await _setup_pair(client)
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))

    view_from_a = await client.get(
        f"/api/v1/collaborations/{collaboration_id}", headers=_auth_headers(token_a)
    )
    view_from_b = await client.get(
        f"/api/v1/collaborations/{collaboration_id}", headers=_auth_headers(token_b)
    )
    assert view_from_a.json()["current_rate"] == "16.000000"
    assert view_from_b.json()["current_rate"] == "16.000000"


async def test_private_rate_never_visible_to_collaborator(client):
    (matricule_a, token_a), (matricule_b, token_b) = await _setup_pair(client)
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))

    await client.post(
        "/api/v1/private-rates",
        json={"collaboration_id": collaboration_id, "currency": "GNF", "rate": "17.5"},
        headers=_auth_headers(token_a),
    )

    rates_from_a = await client.get("/api/v1/private-rates", headers=_auth_headers(token_a))
    rates_from_b = await client.get("/api/v1/private-rates", headers=_auth_headers(token_b))

    assert len(rates_from_a.json()) == 1
    assert rates_from_a.json()[0]["rate"] == "17.500000"
    assert rates_from_b.json() == []


async def test_private_rate_versioning_deactivates_previous(client):
    _, token_a = await _register_and_login_owner(client)

    await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "16"},
        headers=_auth_headers(token_a),
    )
    await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "18"},
        headers=_auth_headers(token_a),
    )

    rates = (await client.get("/api/v1/private-rates", headers=_auth_headers(token_a))).json()
    assert len(rates) == 2
    active = [r for r in rates if r["is_active"]]
    inactive = [r for r in rates if not r["is_active"]]
    assert len(active) == 1
    assert active[0]["rate"] == "18.000000"
    assert len(inactive) == 1
    assert inactive[0]["deactivated_at"] is not None


async def test_private_rate_versioning_ignores_country_label(client):
    """`country` is only an informational label (e.g. "Guinée" for GNF) attached by the
    user — it must not stop a new rate from superseding the previous one for the same
    currency, otherwise the same currency could end up with two ambiguous active rates."""
    _, token_a = await _register_and_login_owner(client)

    await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "14.6", "country": "Guinée"},
        headers=_auth_headers(token_a),
    )
    await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "15.2"},
        headers=_auth_headers(token_a),
    )

    rates = (await client.get("/api/v1/private-rates", headers=_auth_headers(token_a))).json()
    active = [r for r in rates if r["is_active"]]
    assert len(active) == 1
    assert active[0]["rate"] == "15.200000"


async def test_reactivating_a_rate_deactivates_the_current_active_one(client):
    _, token_a = await _register_and_login_owner(client)

    first = await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "14.6"},
        headers=_auth_headers(token_a),
    )
    first_id = first.json()["id"]
    second = await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "18"},
        headers=_auth_headers(token_a),
    )
    second_id = second.json()["id"]

    reactivate_response = await client.patch(
        f"/api/v1/private-rates/{first_id}/status",
        json={"is_active": True},
        headers=_auth_headers(token_a),
    )
    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["is_active"] is True
    assert reactivate_response.json()["deactivated_at"] is None

    rates = {r["id"]: r for r in (await client.get("/api/v1/private-rates", headers=_auth_headers(token_a))).json()}
    assert rates[first_id]["is_active"] is True
    assert rates[second_id]["is_active"] is False
    assert rates[second_id]["deactivated_at"] is not None


async def test_deactivating_a_rate_leaves_currency_without_active_rate(client):
    _, token_a = await _register_and_login_owner(client)

    created = await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "14.6"},
        headers=_auth_headers(token_a),
    )
    rate_id = created.json()["id"]

    deactivate_response = await client.patch(
        f"/api/v1/private-rates/{rate_id}/status",
        json={"is_active": False},
        headers=_auth_headers(token_a),
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False
    assert deactivate_response.json()["deactivated_at"] is not None

    rates = (await client.get("/api/v1/private-rates", headers=_auth_headers(token_a))).json()
    assert all(not r["is_active"] for r in rates)


async def test_deactivating_the_only_rate_blocks_transfers_in_that_currency(client):
    (matricule_a, token_a), (matricule_b, token_b) = await _setup_pair(client)
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))

    rate = await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "14.6"},
        headers=_auth_headers(token_a),
    )
    rate_id = rate.json()["id"]

    await client.patch(
        f"/api/v1/private-rates/{rate_id}/status",
        json={"is_active": False},
        headers=_auth_headers(token_a),
    )

    transfer_response = await client.post(
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
    assert transfer_response.status_code == 409


async def test_rate_status_update_requires_manage_permission(client):
    _, token_a = await _register_and_login_owner(client)
    rate = await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "14.6"},
        headers=_auth_headers(token_a),
    )
    rate_id = rate.json()["id"]

    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé",
            "phone": "+224900222222",
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

    response = await client.patch(
        f"/api/v1/private-rates/{rate_id}/status",
        json={"is_active": False},
        headers=_auth_headers(employee_token),
    )
    assert response.status_code == 403


async def test_rate_status_update_unknown_rate_returns_404(client):
    _, token_a = await _register_and_login_owner(client)
    response = await client.patch(
        f"/api/v1/private-rates/{'00000000-0000-0000-0000-000000000000'}/status",
        json={"is_active": False},
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 404


async def test_rate_status_update_isolated_between_companies(client):
    (matricule_a, token_a), (_, token_b) = await _setup_pair(client)
    rate = await client.post(
        "/api/v1/private-rates",
        json={"currency": "GNF", "rate": "14.6"},
        headers=_auth_headers(token_a),
    )
    rate_id = rate.json()["id"]

    response = await client.patch(
        f"/api/v1/private-rates/{rate_id}/status",
        json={"is_active": False},
        headers=_auth_headers(token_b),
    )
    assert response.status_code == 404


async def test_rate_proposal_notifies_other_party(client):
    (matricule_a, token_a), (matricule_b, token_b) = await _setup_pair(client)
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))

    await client.post(
        f"/api/v1/collaborations/{collaboration_id}/rate-proposals",
        json={"new_rate": "20", "note": "Ajustement du marché"},
        headers=_auth_headers(token_a),
    )

    notifications_b = await client.get("/api/v1/notifications", headers=_auth_headers(token_b))
    types = [n["type"] for n in notifications_b.json()]
    assert "rate_proposed" in types

    notifications_a = await client.get("/api/v1/notifications", headers=_auth_headers(token_a))
    assert "rate_proposed" not in [n["type"] for n in notifications_a.json()]


async def test_rate_proposal_cross_acceptance_required(client):
    (matricule_a, token_a), (matricule_b, token_b) = await _setup_pair(client)
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))

    proposal_response = await client.post(
        f"/api/v1/collaborations/{collaboration_id}/rate-proposals",
        json={"new_rate": "20", "note": "Ajustement du marché"},
        headers=_auth_headers(token_a),
    )
    assert proposal_response.status_code == 201
    proposal_id = proposal_response.json()["id"]
    assert proposal_response.json()["old_rate"] == "16.000000"

    self_accept_response = await client.post(
        f"/api/v1/collaborations/{collaboration_id}/rate-proposals/{proposal_id}/accept",
        headers=_auth_headers(token_a),
    )
    assert self_accept_response.status_code == 403

    accept_response = await client.post(
        f"/api/v1/collaborations/{collaboration_id}/rate-proposals/{proposal_id}/accept",
        headers=_auth_headers(token_b),
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "accepted"

    collaboration_view = await client.get(
        f"/api/v1/collaborations/{collaboration_id}", headers=_auth_headers(token_a)
    )
    assert collaboration_view.json()["current_rate"] == "20.000000"

    history_response = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/rate-history", headers=_auth_headers(token_a)
    )
    history = history_response.json()
    assert len(history) == 2
    assert history[0]["new_rate"] == "16.000000"
    assert history[1]["new_rate"] == "20.000000"


async def test_employee_without_permission_forbidden(client):
    _, token_a = await _register_and_login_owner(client)
    create_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Un",
            "phone": "+224911111111",
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

    response = await client.get("/api/v1/collaborations", headers=_auth_headers(employee_token))
    assert response.status_code == 403


async def test_transfer_create_permission_grants_read_only_collaboration_access(client):
    """Un employé qui peut créer des envois (transfer.create) doit pouvoir lire les
    collaborations de son entreprise — pour choisir vers qui envoyer, et pour afficher le
    partenaire/la devise sur le détail d'un envoi — même sans collaboration.manage. Les
    lectures sont bornées à l'entreprise de l'appelant, donc ça ne fuite rien vers d'autres
    entreprises ; les actions de gestion (accepter/rejeter/proposer un taux) restent, elles,
    réservées à collaboration.manage."""
    (matricule_a, token_a), (matricule_b, token_b) = await _setup_pair(client)
    create_response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    collaboration_id = create_response.json()["id"]
    await client.post(f"/api/v1/collaborations/{collaboration_id}/accept", headers=_auth_headers(token_b))

    employee_response = await client.post(
        "/api/v1/employees",
        json={
            "full_name": "Employé Envois",
            "phone": "+224913333333",
            "password": "EmployeePass123!",
            "permissions": ["transfer.create"],
        },
        headers=_auth_headers(token_a),
    )
    employee_matricule = employee_response.json()["matricule"]
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"matricule": employee_matricule, "password": "EmployeePass123!"},
    )
    employee_token = login_response.json()["access_token"]

    list_response = await client.get("/api/v1/collaborations", headers=_auth_headers(employee_token))
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    page_response = await client.get("/api/v1/collaborations/page", headers=_auth_headers(employee_token))
    assert page_response.status_code == 200

    get_response = await client.get(
        f"/api/v1/collaborations/{collaboration_id}", headers=_auth_headers(employee_token)
    )
    assert get_response.status_code == 200
    assert get_response.json()["id"] == collaboration_id

    history_response = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/rate-history", headers=_auth_headers(employee_token)
    )
    assert history_response.status_code == 200

    # Mais la gestion reste réservée à collaboration.manage.
    accept_response = await client.post(
        f"/api/v1/collaborations/{collaboration_id}/rate-proposals",
        json={"new_rate": "20"},
        headers=_auth_headers(employee_token),
    )
    assert accept_response.status_code == 403

    balance_response = await client.get(
        f"/api/v1/collaborations/{collaboration_id}/balance", headers=_auth_headers(employee_token)
    )
    assert balance_response.status_code == 403
