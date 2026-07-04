import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_otp import PasswordResetOTP


async def create(
    session: AsyncSession, user_id: uuid.UUID, code_hash: str, expires_at: datetime
) -> PasswordResetOTP:
    otp = PasswordResetOTP(user_id=user_id, code_hash=code_hash, expires_at=expires_at)
    session.add(otp)
    await session.flush()
    return otp


async def get_latest_unused(session: AsyncSession, user_id: uuid.UUID) -> PasswordResetOTP | None:
    result = await session.execute(
        select(PasswordResetOTP)
        .where(PasswordResetOTP.user_id == user_id, PasswordResetOTP.used_at.is_(None))
        .order_by(PasswordResetOTP.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
