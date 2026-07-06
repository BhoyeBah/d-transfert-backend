import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proof import Proof


async def create(session: AsyncSession, proof: Proof) -> Proof:
    session.add(proof)
    await session.flush()
    return proof


async def get_by_id(session: AsyncSession, proof_id: uuid.UUID) -> Proof | None:
    return await session.get(Proof, proof_id)


async def list_by_transfer(session: AsyncSession, transfer_id: uuid.UUID) -> list[Proof]:
    result = await session.execute(
        select(Proof).where(Proof.transfer_id == transfer_id).order_by(Proof.created_at)
    )
    return list(result.scalars().all())


async def list_by_payment(session: AsyncSession, payment_id: uuid.UUID) -> list[Proof]:
    result = await session.execute(
        select(Proof).where(Proof.payment_id == payment_id).order_by(Proof.created_at)
    )
    return list(result.scalars().all())
