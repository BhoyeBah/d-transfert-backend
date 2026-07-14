import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collaboration import Collaboration
from app.models.payment import Payment, PaymentStatusHistory
from app.utils.pagination import paginate

_SORTABLE_COLUMNS = {
    "reference": Payment.reference,
    "amount": Payment.amount,
    "created_at": Payment.created_at,
}


async def get_by_company_and_reference(
    session: AsyncSession, company_id: uuid.UUID, reference: str
) -> Payment | None:
    result = await session.execute(
        select(Payment).where(Payment.company_id == company_id, Payment.reference == reference)
    )
    return result.scalar_one_or_none()


async def count_by_company_and_reference_prefix(
    session: AsyncSession, company_id: uuid.UUID, prefix: str
) -> int:
    result = await session.execute(
        select(func.count()).select_from(Payment).where(
            Payment.company_id == company_id, Payment.reference.like(f"{prefix}%")
        )
    )
    return int(result.scalar_one())


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


async def list_for_company_page(
    session: AsyncSession,
    company_id: uuid.UUID,
    page: int,
    page_size: int,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[list[Payment], int]:
    stmt = (
        select(Payment)
        .join(Collaboration, Collaboration.id == Payment.collaboration_id)
        .where(
            or_(
                Collaboration.initiator_company_id == company_id,
                Collaboration.target_company_id == company_id,
            )
        )
    )
    if status:
        stmt = stmt.where(Payment.status == status)
    if start_date:
        stmt = stmt.where(Payment.created_at >= start_date)
    if end_date:
        from datetime import datetime, time
        end_dt = datetime.combine(end_date, time.max)
        stmt = stmt.where(Payment.created_at <= end_dt)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Payment.reference.ilike(pattern),
                Payment.client_name.ilike(pattern),
                Payment.client_phone.ilike(pattern),
            )
        )
    column = _SORTABLE_COLUMNS.get(sort_by, Payment.created_at)
    stmt = stmt.order_by(column.asc() if sort_dir == "asc" else column.desc())
    return await paginate(session, stmt, page, page_size)


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


async def count_all(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(Payment))
    return int(result.scalar_one())


async def sum_amount_by_currency(session: AsyncSession) -> dict[str, Decimal]:
    result = await session.execute(select(Payment.currency, func.sum(Payment.amount)).group_by(Payment.currency))
    return {currency: amount for currency, amount in result.all()}
