import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proof import Proof, ProofStatus


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


async def set_status_for_transfer(session: AsyncSession, transfer_id: uuid.UUID, status: ProofStatus) -> None:
    await session.execute(update(Proof).where(Proof.transfer_id == transfer_id).values(status=status))


async def set_status_for_payment(session: AsyncSession, payment_id: uuid.UUID, status: ProofStatus) -> None:
    await session.execute(update(Proof).where(Proof.payment_id == payment_id).values(status=status))
