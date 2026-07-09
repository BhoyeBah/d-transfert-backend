import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_log import SystemLog, SystemLogLevel
from app.utils.pagination import paginate

_SORTABLE_COLUMNS = {
    "level": SystemLog.level,
    "source": SystemLog.source,
    "created_at": SystemLog.created_at,
}


async def create(
    session: AsyncSession,
    level: SystemLogLevel,
    source: str,
    message: str,
    company_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> SystemLog:
    log = SystemLog(
        level=level, source=source, message=message[:1000], company_id=company_id, user_id=user_id
    )
    session.add(log)
    await session.flush()
    return log


async def list_recent(session: AsyncSession, limit: int = 500) -> list[SystemLog]:
    result = await session.execute(
        select(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def list_page(
    session: AsyncSession,
    page: int,
    page_size: int,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> tuple[list[SystemLog], int]:
    stmt = select(SystemLog)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(SystemLog.message.ilike(pattern), SystemLog.source.ilike(pattern)))
    column = _SORTABLE_COLUMNS.get(sort_by, SystemLog.created_at)
    stmt = stmt.order_by(column.asc() if sort_dir == "asc" else column.desc())
    return await paginate(session, stmt, page, page_size)
