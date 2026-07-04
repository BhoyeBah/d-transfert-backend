import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.notification import Notification, NotificationType
from app.repositories import notification_repository


async def notify(
    session: AsyncSession,
    company_id: uuid.UUID,
    type: NotificationType,
    message: str,
    link_type: str | None = None,
    link_id: uuid.UUID | None = None,
) -> Notification:
    return await notification_repository.create(session, company_id, type, message, link_type, link_id)


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
