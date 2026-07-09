import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import Wallet
from app.utils.pagination import paginate

_SORTABLE_COLUMNS = {
    "name": Wallet.name,
    "code": Wallet.code,
    "balance": Wallet.balance,
    "created_at": Wallet.created_at,
}


async def get_by_company_and_id(
    session: AsyncSession, company_id: uuid.UUID, wallet_id: uuid.UUID
) -> Wallet | None:
    result = await session.execute(
        select(Wallet).where(Wallet.company_id == company_id, Wallet.id == wallet_id)
    )
    return result.scalar_one_or_none()


async def get_by_company_and_code(session: AsyncSession, company_id: uuid.UUID, code: str) -> Wallet | None:
    result = await session.execute(
        select(Wallet).where(Wallet.company_id == company_id, Wallet.code == code)
    )
    return result.scalar_one_or_none()


async def list_by_company(session: AsyncSession, company_id: uuid.UUID) -> list[Wallet]:
    result = await session.execute(
        select(Wallet).where(Wallet.company_id == company_id).order_by(Wallet.created_at)
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
) -> tuple[list[Wallet], int]:
    stmt = select(Wallet).where(Wallet.company_id == company_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(Wallet.name.ilike(pattern), Wallet.code.ilike(pattern), Wallet.phone.ilike(pattern)))
    column = _SORTABLE_COLUMNS.get(sort_by, Wallet.created_at)
    stmt = stmt.order_by(column.asc() if sort_dir == "asc" else column.desc())
    return await paginate(session, stmt, page, page_size)


async def lock_by_id(session: AsyncSession, wallet_id: uuid.UUID) -> Wallet | None:
    result = await session.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
    return result.scalar_one_or_none()


async def count_all(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(Wallet))
    return int(result.scalar_one())
