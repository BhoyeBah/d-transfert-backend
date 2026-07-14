import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories import audit_log_repository
from app.schemas.pagination import PageParams


async def log_action(
    session: AsyncSession,
    company_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    note: str | None = None,
) -> AuditLog:
    return await audit_log_repository.create(
        session, company_id, user_id, action, entity_type, entity_id, note
    )


async def list_for_company(session: AsyncSession, company_id: uuid.UUID) -> list[AuditLog]:
    return await audit_log_repository.list_by_company(session, company_id)


async def list_all(session: AsyncSession) -> list[AuditLog]:
    return await audit_log_repository.list_all(session)


async def list_all_page(session: AsyncSession, params: PageParams) -> tuple[list[AuditLog], int]:
    return await audit_log_repository.list_all_page(
        session, params.page, params.page_size, params.search, params.sort_by, params.sort_dir
    )


async def list_for_employee(
    session: AsyncSession, company_id: uuid.UUID, user_id: uuid.UUID
) -> list[AuditLog]:
    return await audit_log_repository.list_by_employee(session, company_id, user_id)

