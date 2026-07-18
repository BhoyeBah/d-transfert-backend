import uuid

from fastapi.responses import StreamingResponse

import app.core.notification_broadcaster as notification_broadcaster_module
from app.core.notification_broadcaster import InMemoryNotificationBroadcaster, NotificationBroadcaster
from app.routers.notifications import stream_notifications


class _RecordingBroadcaster(NotificationBroadcaster):
    """Double de test : enregistre chaque appel à publish() sans faire de vrai pub/sub."""

    def __init__(self) -> None:
        self.published: list[tuple[uuid.UUID, dict]] = []

    def publish(self, company_id: uuid.UUID, payload: dict) -> None:
        self.published.append((company_id, payload))

    def subscribe(self, company_id: uuid.UUID):
        raise NotImplementedError("Non utilisé par ces tests.")


async def _register_and_login_owner(client, **overrides) -> tuple[str, str, str]:
    payload = {
        "company_name": "Entreprise Stream",
        "company_phone": "+224902000001",
        "address": "Conakry",
        "default_currency": "GNF",
        "owner_full_name": "Owner Stream",
        "password": "SuperSecret123!",
        "password_confirmation": "SuperSecret123!",
    }
    payload.update(overrides)
    register_response = await client.post("/api/v1/auth/register", json=payload)
    body = register_response.json()
    login_response = await client.post(
        "/api/v1/auth/login", json={"matricule": body["registration_code"], "password": payload["password"]}
    )
    return body["company_id"], body["registration_code"], login_response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_creating_a_notification_broadcasts_it_after_commit(client, monkeypatch):
    recorder = _RecordingBroadcaster()
    monkeypatch.setattr(notification_broadcaster_module, "_broadcaster", recorder)

    company_a_id, _, token_a = await _register_and_login_owner(
        client, company_name="Entreprise Stream A", company_phone="+224902000001"
    )
    company_b_id, matricule_b, token_b = await _register_and_login_owner(
        client, company_name="Entreprise Stream B", company_phone="+224902000002"
    )

    response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": matricule_b, "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 201

    assert len(recorder.published) == 1
    published_company_id, payload = recorder.published[0]
    assert str(published_company_id) == company_b_id
    assert payload["type"] == "collaboration_request"
    assert "collaboration" in payload["message"].lower() or "Entreprise Stream A" in payload["message"]


async def test_failed_request_does_not_broadcast(client, monkeypatch):
    recorder = _RecordingBroadcaster()
    monkeypatch.setattr(notification_broadcaster_module, "_broadcaster", recorder)

    _, matricule_a, token_a = await _register_and_login_owner(
        client, company_name="Entreprise Stream C", company_phone="+224902000003"
    )

    # Cible inexistante : la requête échoue avant tout commit, rien ne doit être diffusé.
    response = await client.post(
        "/api/v1/collaborations",
        json={"target_matricule": "no-such-matricule", "currency": "GNF", "initial_rate": "16"},
        headers=_auth_headers(token_a),
    )
    assert response.status_code == 404
    assert recorder.published == []


async def test_stream_endpoint_requires_authentication(client):
    response = await client.get("/api/v1/notifications/stream")
    assert response.status_code == 401


async def test_stream_endpoint_returns_event_stream_response():
    # httpx.ASGITransport attend la fin complète de l'app avant de renvoyer quoi que ce soit
    # (voir handle_async_request : `await self.app(...)` puis `assert response_complete.is_set()`),
    # donc un flux SSE volontairement infini (heartbeat toutes les 25s) ne peut jamais être
    # observé via `client.stream()` sans bloquer indéfiniment. On appelle donc directement la
    # fonction de route : le générateur asynchrone qu'elle construit est paresseux (aucun code
    # ne s'exécute avant la première itération), donc inspecter la réponse ne déclenche ni accès
    # base de données ni abonnement au broadcaster.
    response = await stream_notifications(
        company_id=uuid.uuid4(),
        _current_user=None,
        broadcaster=InMemoryNotificationBroadcaster(),
    )

    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/event-stream"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["connection"] == "keep-alive"
