import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories import audit_log_repository


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
