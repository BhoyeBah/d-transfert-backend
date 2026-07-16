import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, CompanyStatus
from app.utils.pagination import paginate

_SORTABLE_COLUMNS = {
    "name": Company.name,
    "registration_code": Company.registration_code,
    "status": Company.status,
    "created_at": Company.created_at,
}


async def get_by_id(session: AsyncSession, company_id: uuid.UUID) -> Company | None:
    return await session.get(Company, company_id)


async def get_by_registration_code(session: AsyncSession, registration_code: str) -> Company | None:
    result = await session.execute(select(Company).where(Company.registration_code == registration_code))
    return result.scalar_one_or_none()


async def get_by_phone(session: AsyncSession, phone: str) -> Company | None:
    result = await session.execute(select(Company).where(Company.phone == phone))
    return result.scalar_one_or_none()


async def get_by_name(session: AsyncSession, name: str) -> Company | None:
    result = await session.execute(select(Company).where(func.lower(Company.name) == name.lower()))
    return result.scalar_one_or_none()


async def list_all(session: AsyncSession) -> list[Company]:
    result = await session.execute(select(Company).order_by(Company.created_at.desc()))
    return list(result.scalars().all())


async def list_all_page(
    session: AsyncSession,
    page: int,
    page_size: int,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> tuple[list[Company], int]:
    stmt = select(Company)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Company.name.ilike(pattern),
                Company.registration_code.ilike(pattern),
                Company.phone.ilike(pattern),
            )
        )
    column = _SORTABLE_COLUMNS.get(sort_by, Company.created_at)
    stmt = stmt.order_by(column.asc() if sort_dir == "asc" else column.desc())
    return await paginate(session, stmt, page, page_size)


async def count_by_status(session: AsyncSession) -> dict[CompanyStatus, int]:
    result = await session.execute(
        select(Company.status, func.count()).group_by(Company.status)
    )
    return {status: count for status, count in result.all()}
