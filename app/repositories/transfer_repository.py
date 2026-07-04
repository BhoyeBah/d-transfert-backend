import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collaboration import Collaboration
from app.models.transfer import Transfer, TransferStatusHistory


async def get_by_reference(session: AsyncSession, reference: str) -> Transfer | None:
    result = await session.execute(select(Transfer).where(Transfer.reference == reference))
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, transfer_id: uuid.UUID) -> Transfer | None:
    return await session.get(Transfer, transfer_id)


async def lock_by_id(session: AsyncSession, transfer_id: uuid.UUID) -> Transfer | None:
    result = await session.execute(select(Transfer).where(Transfer.id == transfer_id).with_for_update())
    return result.scalar_one_or_none()


async def list_for_company(session: AsyncSession, company_id: uuid.UUID) -> list[Transfer]:
    result = await session.execute(
        select(Transfer)
        .join(Collaboration, Collaboration.id == Transfer.collaboration_id)
        .where(
            or_(
                Collaboration.initiator_company_id == company_id,
                Collaboration.target_company_id == company_id,
            )
        )
        .order_by(Transfer.created_at.desc())
    )
    return list(result.scalars().all())


async def add_status_history(
    session: AsyncSession, history: TransferStatusHistory
) -> TransferStatusHistory:
    session.add(history)
    await session.flush()
    return history


async def list_status_history(session: AsyncSession, transfer_id: uuid.UUID) -> list[TransferStatusHistory]:
    result = await session.execute(
        select(TransferStatusHistory)
        .where(TransferStatusHistory.transfer_id == transfer_id)
        .order_by(TransferStatusHistory.created_at)
    )
    return list(result.scalars().all())
