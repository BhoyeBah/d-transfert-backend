import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet_movement import MovementDirection, WalletMovement


async def create(
    session: AsyncSession,
    wallet_id: uuid.UUID,
    direction: MovementDirection,
    amount: Decimal,
    currency: str,
    balance_before: Decimal,
    balance_after: Decimal,
    source_type: str,
    source_id: uuid.UUID,
    created_by_id: uuid.UUID,
    note: str | None = None,
) -> WalletMovement:
    movement = WalletMovement(
        wallet_id=wallet_id,
        direction=direction,
        amount=amount,
        currency=currency,
        balance_before=balance_before,
        balance_after=balance_after,
        source_type=source_type,
        source_id=source_id,
        created_by_id=created_by_id,
        note=note,
    )
    session.add(movement)
    await session.flush()
    return movement


async def list_by_wallet(session: AsyncSession, wallet_id: uuid.UUID) -> list[WalletMovement]:
    result = await session.execute(
        select(WalletMovement)
        .where(WalletMovement.wallet_id == wallet_id)
        .order_by(WalletMovement.created_at)
    )
    return list(result.scalars().all())
