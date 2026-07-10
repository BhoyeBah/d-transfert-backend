import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.private_sending_rate import PrivateSendingRate


async def get_active_by_scope(
    session: AsyncSession,
    company_id: uuid.UUID,
    collaboration_id: uuid.UUID | None,
    country: str | None,
    currency: str,
    operation_type: str | None = None,
) -> PrivateSendingRate | None:
    result = await session.execute(
        select(PrivateSendingRate).where(
            PrivateSendingRate.company_id == company_id,
            PrivateSendingRate.collaboration_id == collaboration_id,
            PrivateSendingRate.country == country,
            PrivateSendingRate.currency == currency,
            PrivateSendingRate.operation_type == operation_type,
            PrivateSendingRate.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def list_active_for_currency(
    session: AsyncSession, company_id: uuid.UUID, currency: str
) -> list[PrivateSendingRate]:
    result = await session.execute(
        select(PrivateSendingRate).where(
            PrivateSendingRate.company_id == company_id,
            PrivateSendingRate.currency == currency,
            PrivateSendingRate.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def list_by_company(session: AsyncSession, company_id: uuid.UUID) -> list[PrivateSendingRate]:
    result = await session.execute(
        select(PrivateSendingRate)
        .where(PrivateSendingRate.company_id == company_id)
        .order_by(PrivateSendingRate.created_at.desc())
    )
    return list(result.scalars().all())


async def get_by_company_and_id(
    session: AsyncSession, company_id: uuid.UUID, rate_id: uuid.UUID
) -> PrivateSendingRate | None:
    result = await session.execute(
        select(PrivateSendingRate).where(
            PrivateSendingRate.company_id == company_id, PrivateSendingRate.id == rate_id
        )
    )
    return result.scalar_one_or_none()
