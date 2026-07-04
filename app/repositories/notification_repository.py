import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType


async def create(
    session: AsyncSession,
    company_id: uuid.UUID,
    type: NotificationType,
    message: str,
    link_type: str | None = None,
    link_id: uuid.UUID | None = None,
) -> Notification:
    notification = Notification(
        company_id=company_id, type=type, message=message, link_type=link_type, link_id=link_id
    )
    session.add(notification)
    await session.flush()
    return notification


async def list_by_company(session: AsyncSession, company_id: uuid.UUID) -> list[Notification]:
    result = await session.execute(
        select(Notification)
        .where(Notification.company_id == company_id)
        .order_by(Notification.created_at.desc())
    )
    return list(result.scalars().all())


async def get_by_company_and_id(
    session: AsyncSession, company_id: uuid.UUID, notification_id: uuid.UUID
) -> Notification | None:
    result = await session.execute(
        select(Notification).where(
            Notification.company_id == company_id, Notification.id == notification_id
        )
    )
    return result.scalar_one_or_none()
