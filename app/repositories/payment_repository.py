import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collaboration import Collaboration
from app.models.payment import Payment, PaymentStatusHistory


async def get_by_reference(session: AsyncSession, reference: str) -> Payment | None:
    result = await session.execute(select(Payment).where(Payment.reference == reference))
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    return await session.get(Payment, payment_id)


async def lock_by_id(session: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    result = await session.execute(select(Payment).where(Payment.id == payment_id).with_for_update())
    return result.scalar_one_or_none()


async def list_for_company(session: AsyncSession, company_id: uuid.UUID) -> list[Payment]:
    result = await session.execute(
        select(Payment)
        .join(Collaboration, Collaboration.id == Payment.collaboration_id)
        .where(
            or_(
                Collaboration.initiator_company_id == company_id,
                Collaboration.target_company_id == company_id,
            )
        )
        .order_by(Payment.created_at.desc())
    )
    return list(result.scalars().all())


async def add_status_history(session: AsyncSession, history: PaymentStatusHistory) -> PaymentStatusHistory:
    session.add(history)
    await session.flush()
    return history


async def list_status_history(session: AsyncSession, payment_id: uuid.UUID) -> list[PaymentStatusHistory]:
    result = await session.execute(
        select(PaymentStatusHistory)
        .where(PaymentStatusHistory.payment_id == payment_id)
        .order_by(PaymentStatusHistory.created_at)
    )
    return list(result.scalars().all())
