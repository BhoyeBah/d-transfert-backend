import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.entry_allocation import EntryAllocation, EntryAllocationTargetType
from app.models.entry_line import EntryLine


async def get_by_company_and_reference(
    session: AsyncSession, company_id: uuid.UUID, reference: str
) -> Entry | None:
    result = await session.execute(
        select(Entry).where(Entry.company_id == company_id, Entry.reference == reference)
    )
    return result.scalar_one_or_none()


async def count_by_company_and_reference_prefix(
    session: AsyncSession, company_id: uuid.UUID, prefix: str
) -> int:
    result = await session.execute(
        select(func.count()).select_from(Entry).where(
            Entry.company_id == company_id, Entry.reference.like(f"{prefix}%")
        )
    )
    return int(result.scalar_one())


async def get_by_company_and_id(
    session: AsyncSession, company_id: uuid.UUID, entry_id: uuid.UUID
) -> Entry | None:
    result = await session.execute(
        select(Entry).where(Entry.company_id == company_id, Entry.id == entry_id)
    )
    return result.scalar_one_or_none()


async def list_by_company(session: AsyncSession, company_id: uuid.UUID) -> list[Entry]:
    result = await session.execute(
        select(Entry).where(Entry.company_id == company_id).order_by(Entry.created_at.desc())
    )
    return list(result.scalars().all())


async def get_lines(session: AsyncSession, entry_id: uuid.UUID) -> list[EntryLine]:
    result = await session.execute(
        select(EntryLine).where(EntryLine.entry_id == entry_id).order_by(EntryLine.created_at)
    )
    return list(result.scalars().all())


async def get_allocations(session: AsyncSession, entry_id: uuid.UUID) -> list[EntryAllocation]:
    result = await session.execute(
        select(EntryAllocation)
        .where(EntryAllocation.entry_id == entry_id)
        .order_by(EntryAllocation.created_at)
    )
    return list(result.scalars().all())


async def get_allocation_by_target(
    session: AsyncSession, target_type: EntryAllocationTargetType, target_id: uuid.UUID
) -> EntryAllocation | None:
    result = await session.execute(
        select(EntryAllocation).where(
            EntryAllocation.target_type == target_type, EntryAllocation.target_id == target_id
        )
    )
    return result.scalar_one_or_none()


async def count_all(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(Entry))
    return int(result.scalar_one())
