import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collaborator_balance_movement import CollaboratorBalanceMovement


async def create(
    session: AsyncSession,
    collaboration_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    currency: str,
    amount: Decimal,
    debtor_company_id: uuid.UUID,
    creditor_company_id: uuid.UUID,
    note: str | None = None,
) -> CollaboratorBalanceMovement:
    movement = CollaboratorBalanceMovement(
        collaboration_id=collaboration_id,
        source_type=source_type,
        source_id=source_id,
        currency=currency,
        amount=amount,
        debtor_company_id=debtor_company_id,
        creditor_company_id=creditor_company_id,
        note=note,
    )
    session.add(movement)
    await session.flush()
    return movement


async def get_balance_for_company(
    session: AsyncSession, collaboration_id: uuid.UUID, company_id: uuid.UUID
) -> Decimal:
    credit_result = await session.execute(
        select(func.coalesce(func.sum(CollaboratorBalanceMovement.amount), 0)).where(
            CollaboratorBalanceMovement.collaboration_id == collaboration_id,
            CollaboratorBalanceMovement.creditor_company_id == company_id,
        )
    )
    debit_result = await session.execute(
        select(func.coalesce(func.sum(CollaboratorBalanceMovement.amount), 0)).where(
            CollaboratorBalanceMovement.collaboration_id == collaboration_id,
            CollaboratorBalanceMovement.debtor_company_id == company_id,
        )
    )
    credit_total: Decimal = credit_result.scalar_one()
    debit_total: Decimal = debit_result.scalar_one()
    return Decimal(credit_total) - Decimal(debit_total)


async def list_for_collaboration(
    session: AsyncSession, collaboration_id: uuid.UUID
) -> list[CollaboratorBalanceMovement]:
    result = await session.execute(
        select(CollaboratorBalanceMovement)
        .where(CollaboratorBalanceMovement.collaboration_id == collaboration_id)
        .order_by(CollaboratorBalanceMovement.created_at)
    )
    return list(result.scalars().all())
