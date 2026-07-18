"""Diffusion en temps réel des notifications aux clients connectés (SSE).

Volontairement séparé de `notification_service` (persistance en base) : ce module ne connaît
que le pub/sub par entreprise, ni la base de données ni le protocole de transport HTTP. Toute
implémentation respectant `NotificationBroadcaster` peut se substituer à
`InMemoryNotificationBroadcaster` sans changer le reste du système — utile si l'application
est un jour déployée sur plusieurs instances (l'implémentation en mémoire ne diffuse alors
qu'aux abonnés connectés à la même instance, il faudrait un relais partagé type Redis).
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager


class NotificationBroadcaster(ABC):
    @abstractmethod
    def publish(self, company_id: uuid.UUID, payload: dict) -> None:
        """Diffuse un événement aux abonnés actuellement connectés pour cette entreprise.

        Best-effort : si personne n'est connecté au moment de l'appel, l'événement est perdu
        (la notification reste consultable via l'API classique, ce canal ne sert qu'à
        prévenir les clients déjà ouverts)."""

    @abstractmethod
    def subscribe(self, company_id: uuid.UUID) -> AbstractAsyncContextManager[asyncio.Queue[dict]]:
        """File d'événements pour cette entreprise, valable pour la durée du bloc `async with`."""


class InMemoryNotificationBroadcaster(NotificationBroadcaster):
    def __init__(self) -> None:
        self._subscribers: dict[uuid.UUID, set[asyncio.Queue[dict]]] = {}

    def publish(self, company_id: uuid.UUID, payload: dict) -> None:
        for queue in self._subscribers.get(company_id, ()):
            queue.put_nowait(payload)

    @asynccontextmanager
    async def subscribe(self, company_id: uuid.UUID) -> AsyncIterator[asyncio.Queue[dict]]:
        queue: asyncio.Queue[dict] = asyncio.Queue()
        self._subscribers.setdefault(company_id, set()).add(queue)
        try:
            yield queue
        finally:
            subscribers = self._subscribers.get(company_id)
            if subscribers is not None:
                subscribers.discard(queue)
                if not subscribers:
                    del self._subscribers[company_id]


_broadcaster: NotificationBroadcaster = InMemoryNotificationBroadcaster()


def get_notification_broadcaster() -> NotificationBroadcaster:
    return _broadcaster
