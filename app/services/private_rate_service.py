import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.private_sending_rate import PrivateSendingRate
from app.repositories import private_rate_repository
from app.schemas.private_rate import PrivateRateCreateRequest


async def set_rate(
    session: AsyncSession, company_id: uuid.UUID, created_by_id: uuid.UUID, payload: PrivateRateCreateRequest
) -> PrivateSendingRate:
    existing = await private_rate_repository.get_active_by_scope(
        session, company_id, payload.collaboration_id, payload.country, payload.currency, payload.operation_type
    )
    if existing is not None:
        existing.is_active = False
        existing.deactivated_at = datetime.now(timezone.utc)

    new_rate = PrivateSendingRate(
        company_id=company_id,
        collaboration_id=payload.collaboration_id,
        country=payload.country,
        operation_type=payload.operation_type,
        currency=payload.currency,
        rate=payload.rate,
        is_active=True,
        created_by_id=created_by_id,
    )
    session.add(new_rate)
    await session.commit()
    return new_rate


async def list_rates(session: AsyncSession, company_id: uuid.UUID) -> list[PrivateSendingRate]:
    return await private_rate_repository.list_by_company(session, company_id)
