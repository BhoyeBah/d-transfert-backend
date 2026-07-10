import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.company import Company
from app.repositories import company_repository
from app.schemas.company import AdminCompanyUpdateRequest
from app.services import audit_service


async def get_my_company(session: AsyncSession, company_id: uuid.UUID) -> Company:
    company = await company_repository.get_by_id(session, company_id)
    if company is None:
        raise NotFoundError("Entreprise introuvable.")
    return company


async def update_my_company(
    session: AsyncSession,
    company_id: uuid.UUID,
    acted_by_user_id: uuid.UUID,
    payload: AdminCompanyUpdateRequest,
) -> Company:
    company = await get_my_company(session, company_id)

    if payload.phone is not None and payload.phone != company.phone:
        existing = await company_repository.get_by_phone(session, payload.phone)
        if existing is not None and existing.id != company.id:
            raise ConflictError("Ce numéro de téléphone est déjà utilisé par une autre entreprise.")
        company.phone = payload.phone
    if payload.name is not None:
        company.name = payload.name
    if payload.address is not None:
        company.address = payload.address
    if payload.default_currency is not None:
        company.default_currency = payload.default_currency

    await audit_service.log_action(
        session, company.id, acted_by_user_id, "company.update", "company", company.id
    )
    await session.commit()
    return company
