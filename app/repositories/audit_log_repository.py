import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def create(
    session: AsyncSession,
    company_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    note: str | None = None,
) -> AuditLog:
    log = AuditLog(
        company_id=company_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        note=note,
    )
    session.add(log)
    await session.flush()
    return log


async def list_by_company(session: AsyncSession, company_id: uuid.UUID) -> list[AuditLog]:
    result = await session.execute(
        select(AuditLog).where(AuditLog.company_id == company_id).order_by(AuditLog.created_at.desc())
    )
    return list(result.scalars().all())


async def list_all(session: AsyncSession) -> list[AuditLog]:
    result = await session.execute(select(AuditLog).order_by(AuditLog.created_at.desc()))
    return list(result.scalars().all())
