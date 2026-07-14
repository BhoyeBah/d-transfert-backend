import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.private_sending_rate import PrivateSendingRate


async def get_active_by_scope(
    session: AsyncSession,
    company_id: uuid.UUID,
    collaboration_id: uuid.UUID | None,
    currency: str,
    target_currency: str | None,
    operation_type: str | None = None,
) -> PrivateSendingRate | None:
    # `country` is purely an informational label the user attaches to a rate (e.g. "Guinée"
    # for GNF) — it must NOT be part of what identifies "the same rate slot", otherwise
    # changing the label (or leaving it blank) when updating a rate would leave the old rate
    # active alongside the new one instead of superseding it.
    result = await session.execute(
        select(PrivateSendingRate).where(
            PrivateSendingRate.company_id == company_id,
            PrivateSendingRate.collaboration_id == collaboration_id,
            PrivateSendingRate.currency == currency,
            PrivateSendingRate.target_currency == target_currency,
            PrivateSendingRate.operation_type == operation_type,
            PrivateSendingRate.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def list_active_for_pair(
    session: AsyncSession, company_id: uuid.UUID, currency: str, target_currency: str
) -> list[PrivateSendingRate]:
    # Inclut aussi les taux "toutes destinations" (target_currency NULL) : au niveau appelant,
    # une correspondance exacte de devise cible est toujours préférée à ce joker.
    result = await session.execute(
        select(PrivateSendingRate).where(
            PrivateSendingRate.company_id == company_id,
            PrivateSendingRate.currency == currency,
            or_(
                PrivateSendingRate.target_currency == target_currency,
                PrivateSendingRate.target_currency.is_(None),
            ),
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
