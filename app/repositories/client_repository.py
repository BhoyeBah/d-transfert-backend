import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.client_balance_movement import ClientBalanceMovement
from app.utils.pagination import paginate

_SORTABLE_COLUMNS = {
    "name": Client.name,
    "balance": Client.balance,
    "created_at": Client.created_at,
}


async def get_by_company_and_phone(session: AsyncSession, company_id: uuid.UUID, phone: str) -> Client | None:
    result = await session.execute(
        select(Client).where(Client.company_id == company_id, Client.phone == phone)
    )
    return result.scalar_one_or_none()


async def get_by_company_and_id(
    session: AsyncSession, company_id: uuid.UUID, client_id: uuid.UUID
) -> Client | None:
    result = await session.execute(
        select(Client).where(Client.company_id == company_id, Client.id == client_id)
    )
    return result.scalar_one_or_none()


async def list_by_company(session: AsyncSession, company_id: uuid.UUID) -> list[Client]:
    result = await session.execute(
        select(Client).where(Client.company_id == company_id).order_by(Client.created_at.desc())
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
) -> tuple[list[Client], int]:
    stmt = select(Client).where(Client.company_id == company_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(Client.name.ilike(pattern), Client.phone.ilike(pattern)))
    column = _SORTABLE_COLUMNS.get(sort_by, Client.created_at)
    stmt = stmt.order_by(column.asc() if sort_dir == "asc" else column.desc())
    return await paginate(session, stmt, page, page_size)


async def list_movements(session: AsyncSession, client_id: uuid.UUID) -> list[ClientBalanceMovement]:
    result = await session.execute(
        select(ClientBalanceMovement)
        .where(ClientBalanceMovement.client_id == client_id)
        .order_by(ClientBalanceMovement.created_at)
    )
    return list(result.scalars().all())


async def get_by_source(
    session: AsyncSession, client_id: uuid.UUID, source_type: str, source_id: uuid.UUID
) -> list[ClientBalanceMovement]:
    result = await session.execute(
        select(ClientBalanceMovement).where(
            ClientBalanceMovement.client_id == client_id,
            ClientBalanceMovement.source_type == source_type,
            ClientBalanceMovement.source_id == source_id,
        )
    )
    return list(result.scalars().all())
