import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.national_operation import NationalOperation
from app.models.national_operation_line import NationalOperationLine
from app.utils.pagination import paginate

_SORTABLE_COLUMNS = {
    "reference": NationalOperation.reference,
    "created_at": NationalOperation.created_at,
}


async def get_by_company_and_reference(
    session: AsyncSession, company_id: uuid.UUID, reference: str
) -> NationalOperation | None:
    result = await session.execute(
        select(NationalOperation).where(
            NationalOperation.company_id == company_id, NationalOperation.reference == reference
        )
    )
    return result.scalar_one_or_none()


async def count_by_company_and_reference_prefix(
    session: AsyncSession, company_id: uuid.UUID, prefix: str
) -> int:
    result = await session.execute(
        select(func.count()).select_from(NationalOperation).where(
            NationalOperation.company_id == company_id,
            NationalOperation.reference.like(f"{prefix}%"),
        )
    )
    return int(result.scalar_one())


async def get_by_company_and_id(
    session: AsyncSession, company_id: uuid.UUID, operation_id: uuid.UUID
) -> NationalOperation | None:
    result = await session.execute(
        select(NationalOperation).where(
            NationalOperation.company_id == company_id, NationalOperation.id == operation_id
        )
    )
    return result.scalar_one_or_none()


async def list_by_company(session: AsyncSession, company_id: uuid.UUID) -> list[NationalOperation]:
    result = await session.execute(
        select(NationalOperation)
        .where(NationalOperation.company_id == company_id)
        .order_by(NationalOperation.created_at.desc())
    )
    return list(result.scalars().all())


async def list_by_company_page(
    session: AsyncSession,
    company_id: uuid.UUID,
    page: int,
    page_size: int,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> tuple[list[NationalOperation], int]:
    stmt = select(NationalOperation).where(NationalOperation.company_id == company_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                NationalOperation.reference.ilike(pattern),
                NationalOperation.client_name.ilike(pattern),
                NationalOperation.client_phone.ilike(pattern),
            )
        )
    column = _SORTABLE_COLUMNS.get(sort_by, NationalOperation.created_at)
    stmt = stmt.order_by(column.asc() if sort_dir == "asc" else column.desc())
    return await paginate(session, stmt, page, page_size)


async def get_lines(session: AsyncSession, operation_id: uuid.UUID) -> list[NationalOperationLine]:
    result = await session.execute(
        select(NationalOperationLine)
        .where(NationalOperationLine.national_operation_id == operation_id)
        .order_by(NationalOperationLine.created_at)
    )
    return list(result.scalars().all())


async def count_all(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(NationalOperation))
    return int(result.scalar_one())
