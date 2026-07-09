import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.utils.pagination import paginate

_SORTABLE_COLUMNS = {
    "action": AuditLog.action,
    "entity_type": AuditLog.entity_type,
    "created_at": AuditLog.created_at,
}


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


async def list_all_page(
    session: AsyncSession,
    page: int,
    page_size: int,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> tuple[list[AuditLog], int]:
    stmt = select(AuditLog)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(AuditLog.action.ilike(pattern), AuditLog.entity_type.ilike(pattern)))
    column = _SORTABLE_COLUMNS.get(sort_by, AuditLog.created_at)
    stmt = stmt.order_by(column.asc() if sort_dir == "asc" else column.desc())
    return await paginate(session, stmt, page, page_size)
