import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collaboration import Collaboration
from app.models.transfer import Transfer, TransferStatusHistory
from app.utils.pagination import paginate

_SORTABLE_COLUMNS = {
    "reference": Transfer.reference,
    "amount": Transfer.amount,
    "created_at": Transfer.created_at,
}


async def get_by_company_and_reference(
    session: AsyncSession, company_id: uuid.UUID, reference: str
) -> Transfer | None:
    result = await session.execute(
        select(Transfer).where(Transfer.company_id == company_id, Transfer.reference == reference)
    )
    return result.scalar_one_or_none()


async def count_by_company_and_reference_prefix(
    session: AsyncSession, company_id: uuid.UUID, prefix: str
) -> int:
    result = await session.execute(
        select(func.count()).select_from(Transfer).where(
            Transfer.company_id == company_id, Transfer.reference.like(f"{prefix}%")
        )
    )
    return int(result.scalar_one())


async def get_by_id(session: AsyncSession, transfer_id: uuid.UUID) -> Transfer | None:
    return await session.get(Transfer, transfer_id)


async def lock_by_id(session: AsyncSession, transfer_id: uuid.UUID) -> Transfer | None:
    result = await session.execute(select(Transfer).where(Transfer.id == transfer_id).with_for_update())
    return result.scalar_one_or_none()


async def list_for_company(session: AsyncSession, company_id: uuid.UUID) -> list[Transfer]:
    result = await session.execute(
        select(Transfer)
        .join(Collaboration, Collaboration.id == Transfer.collaboration_id)
        .where(
            or_(
                Collaboration.initiator_company_id == company_id,
                Collaboration.target_company_id == company_id,
            )
        )
        .order_by(Transfer.created_at.desc())
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
) -> tuple[list[Transfer], int]:
    stmt = (
        select(Transfer)
        .join(Collaboration, Collaboration.id == Transfer.collaboration_id)
        .where(
            or_(
                Collaboration.initiator_company_id == company_id,
                Collaboration.target_company_id == company_id,
            )
        )
    )
    if status:
        stmt = stmt.where(Transfer.status == status)
    if start_date:
        stmt = stmt.where(Transfer.created_at >= start_date)
    if end_date:
        from datetime import datetime, time
        end_dt = datetime.combine(end_date, time.max)
        stmt = stmt.where(Transfer.created_at <= end_dt)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Transfer.reference.ilike(pattern),
                Transfer.beneficiary_name.ilike(pattern),
                Transfer.beneficiary_phone.ilike(pattern),
            )
        )
    column = _SORTABLE_COLUMNS.get(sort_by, Transfer.created_at)
    stmt = stmt.order_by(column.asc() if sort_dir == "asc" else column.desc())
    return await paginate(session, stmt, page, page_size)


async def add_status_history(
    session: AsyncSession, history: TransferStatusHistory
) -> TransferStatusHistory:
    session.add(history)
    await session.flush()
    return history


async def list_status_history(session: AsyncSession, transfer_id: uuid.UUID) -> list[TransferStatusHistory]:
    result = await session.execute(
        select(TransferStatusHistory)
        .where(TransferStatusHistory.transfer_id == transfer_id)
        .order_by(TransferStatusHistory.created_at)
    )
    return list(result.scalars().all())


async def count_all(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(Transfer))
    return int(result.scalar_one())


async def sum_amount_by_currency(session: AsyncSession) -> dict[str, Decimal]:
    result = await session.execute(select(Transfer.currency, func.sum(Transfer.amount)).group_by(Transfer.currency))
    return {currency: amount for currency, amount in result.all()}
