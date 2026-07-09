import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supplier import Supplier
from app.models.supplier_balance_movement import SupplierBalanceMovement


async def get_by_company_and_code(session: AsyncSession, company_id: uuid.UUID, code: str) -> Supplier | None:
    result = await session.execute(
        select(Supplier).where(Supplier.company_id == company_id, Supplier.code == code)
    )
    return result.scalar_one_or_none()


async def get_by_company_and_id(
    session: AsyncSession, company_id: uuid.UUID, supplier_id: uuid.UUID
) -> Supplier | None:
    result = await session.execute(
        select(Supplier).where(Supplier.company_id == company_id, Supplier.id == supplier_id)
    )
    return result.scalar_one_or_none()


async def list_by_company(session: AsyncSession, company_id: uuid.UUID) -> list[Supplier]:
    result = await session.execute(
        select(Supplier).where(Supplier.company_id == company_id).order_by(Supplier.created_at.desc())
    )
    return list(result.scalars().all())


async def get_by_company_and_reference(
    session: AsyncSession, company_id: uuid.UUID, reference: str
) -> SupplierBalanceMovement | None:
    result = await session.execute(
        select(SupplierBalanceMovement).where(
            SupplierBalanceMovement.company_id == company_id, SupplierBalanceMovement.reference == reference
        )
    )
    return result.scalar_one_or_none()


async def count_by_company_and_reference_prefix(session: AsyncSession, company_id: uuid.UUID, prefix: str) -> int:
    result = await session.execute(
        select(func.count()).select_from(SupplierBalanceMovement).where(
            SupplierBalanceMovement.company_id == company_id,
            SupplierBalanceMovement.reference.like(f"{prefix}%"),
        )
    )
    return int(result.scalar_one())


async def list_movements(session: AsyncSession, supplier_id: uuid.UUID) -> list[SupplierBalanceMovement]:
    result = await session.execute(
        select(SupplierBalanceMovement)
        .where(SupplierBalanceMovement.supplier_id == supplier_id)
        .order_by(SupplierBalanceMovement.created_at)
    )
    return list(result.scalars().all())
