import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.company import Company, CompanyStatus
from app.repositories import company_repository
from app.services import audit_service


async def list_companies(session: AsyncSession) -> list[Company]:
    return await company_repository.list_all(session)


async def set_company_status(
    session: AsyncSession, acted_by_user_id: uuid.UUID, company_id: uuid.UUID, status: CompanyStatus
) -> Company:
    company = await company_repository.get_by_id(session, company_id)
    if company is None:
        raise NotFoundError("Entreprise introuvable.")

    company.status = status
    await audit_service.log_action(
        session, company.id, acted_by_user_id, "admin.company_status_change", "company", company.id,
        note=f"status={status.value}",
    )
    await session.commit()
    return company
