from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.revoked_token import RevokedToken


async def revoke(session: AsyncSession, jti: str, expires_at: datetime) -> None:
    # on_conflict_do_nothing : /auth/logout peut être appelé deux fois avec le même token
    # (double-clic, retry réseau) sans que ce soit une erreur.
    await session.execute(
        insert(RevokedToken)
        .values(jti=jti, expires_at=expires_at)
        .on_conflict_do_nothing(index_elements=["jti"])
    )
    await session.flush()


async def is_revoked(session: AsyncSession, jti: str) -> bool:
    result = await session.execute(select(RevokedToken.id).where(RevokedToken.jti == jti))
    return result.scalar_one_or_none() is not None
