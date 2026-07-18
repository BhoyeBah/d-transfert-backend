import uuid

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

from app.core.exceptions import NotFoundError
from app.core.notification_broadcaster import get_notification_broadcaster
from app.models.notification import Notification, NotificationType
from app.repositories import notification_repository
from app.schemas.notification import NotificationResponse

_PENDING_BROADCASTS_KEY = "pending_notification_broadcasts"


async def notify(
    session: AsyncSession,
    company_id: uuid.UUID,
    type: NotificationType,
    message: str,
    link_type: str | None = None,
    link_id: uuid.UUID | None = None,
) -> Notification:
    notification = await notification_repository.create(session, company_id, type, message, link_type, link_id)
    # Mise en attente jusqu'après le commit (cf. _broadcast_after_commit ci-dessous) : si la
    # transaction englobante échoue et annule tout, aucune notification "fantôme" ne doit être
    # diffusée aux clients connectés en direct.
    payload = NotificationResponse.model_validate(notification, from_attributes=True).model_dump(mode="json")
    session.info.setdefault(_PENDING_BROADCASTS_KEY, []).append((company_id, payload))
    return notification


@event.listens_for(SyncSession, "after_commit")
def _broadcast_after_commit(session: SyncSession) -> None:
    pending = session.info.pop(_PENDING_BROADCASTS_KEY, None)
    if not pending:
        return
    broadcaster = get_notification_broadcaster()
    for company_id, payload in pending:
        broadcaster.publish(company_id, payload)


@event.listens_for(SyncSession, "after_rollback")
def _discard_pending_after_rollback(session: SyncSession) -> None:
    session.info.pop(_PENDING_BROADCASTS_KEY, None)


async def list_notifications(session: AsyncSession, company_id: uuid.UUID) -> list[Notification]:
    return await notification_repository.list_by_company(session, company_id)


async def mark_as_read(
    session: AsyncSession, company_id: uuid.UUID, notification_id: uuid.UUID
) -> Notification:
    notification = await notification_repository.get_by_company_and_id(session, company_id, notification_id)
    if notification is None:
        raise NotFoundError("Notification introuvable.")
    notification.is_read = True
    await session.commit()
    return notification
