import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company


async def get_by_id(session: AsyncSession, company_id: uuid.UUID) -> Company | None:
    return await session.get(Company, company_id)


async def get_by_registration_code(session: AsyncSession, registration_code: str) -> Company | None:
    result = await session.execute(select(Company).where(Company.registration_code == registration_code))
    return result.scalar_one_or_none()


async def get_by_phone(session: AsyncSession, phone: str) -> Company | None:
    result = await session.execute(select(Company).where(Company.phone == phone))
    return result.scalar_one_or_none()
