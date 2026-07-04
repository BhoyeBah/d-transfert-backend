import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.client_balance_movement import ClientBalanceMovement


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


async def list_movements(session: AsyncSession, client_id: uuid.UUID) -> list[ClientBalanceMovement]:
    result = await session.execute(
        select(ClientBalanceMovement)
        .where(ClientBalanceMovement.client_id == client_id)
        .order_by(ClientBalanceMovement.created_at)
    )
    return list(result.scalars().all())
