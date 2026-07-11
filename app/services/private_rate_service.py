import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.private_sending_rate import PrivateSendingRate
from app.repositories import private_rate_repository
from app.schemas.private_rate import PrivateRateCreateRequest


async def set_rate(
    session: AsyncSession, company_id: uuid.UUID, created_by_id: uuid.UUID, payload: PrivateRateCreateRequest
) -> PrivateSendingRate:
    existing = await private_rate_repository.get_active_by_scope(
        session, company_id, payload.collaboration_id, payload.currency, payload.operation_type
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


async def set_active_status(
    session: AsyncSession, company_id: uuid.UUID, rate_id: uuid.UUID, is_active: bool
) -> PrivateSendingRate:
    rate = await private_rate_repository.get_by_company_and_id(session, company_id, rate_id)
    if rate is None:
        raise NotFoundError(f"Taux introuvable : {rate_id}.")

    if is_active:
        # Un seul taux peut être actif à la fois pour une même combinaison devise /
        # collaboration / type d'opération, car c'est celui-là qui sera utilisé pour les
        # prochains envois : réactiver ce taux désactive donc celui actuellement actif dans
        # le même emplacement, s'il y en a un autre.
        current_active = await private_rate_repository.get_active_by_scope(
            session, company_id, rate.collaboration_id, rate.currency, rate.operation_type
        )
        if current_active is not None and current_active.id != rate.id:
            current_active.is_active = False
            current_active.deactivated_at = datetime.now(timezone.utc)
        rate.is_active = True
        rate.deactivated_at = None
    else:
        rate.is_active = False
        rate.deactivated_at = datetime.now(timezone.utc)

    await session.commit()
    return rate
