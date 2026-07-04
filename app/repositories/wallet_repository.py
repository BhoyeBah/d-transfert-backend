import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import Wallet


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


async def lock_by_id(session: AsyncSession, wallet_id: uuid.UUID) -> Wallet | None:
    result = await session.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
    return result.scalar_one_or_none()
