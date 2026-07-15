import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.company import Company, CompanyStatus
from app.models.user import User
from app.repositories import company_repository
from app.schemas.company import AdminCompanyUpdateRequest
from app.services import audit_service
from app.utils.reference import generate_company_registration_code

REGISTRATION_CODE_MAX_RETRIES = 5


async def get_my_company(session: AsyncSession, company_id: uuid.UUID) -> Company:
    company = await company_repository.get_by_id(session, company_id)
    if company is None:
        raise NotFoundError("Entreprise introuvable.")
    return company


async def create_company_with_owner(
    session: AsyncSession,
    *,
    company_name: str,
    company_phone: str,
    address: str,
    default_currency: str,
    owner_full_name: str,
    password: str,
    status: CompanyStatus,
) -> tuple[Company, User]:
    if await company_repository.get_by_phone(session, company_phone) is not None:
        raise ConflictError("Ce numéro de téléphone est déjà utilisé par une entreprise.")

    registration_code = None
    for _ in range(REGISTRATION_CODE_MAX_RETRIES):
        candidate = generate_company_registration_code()
        if await company_repository.get_by_registration_code(session, candidate) is None:
            registration_code = candidate
            break
    if registration_code is None:
        raise ConflictError("Impossible de générer un matricule unique, réessayez.")

    company = Company(
        name=company_name,
        registration_code=registration_code,
        address=address,
        phone=company_phone,
        default_currency=default_currency,
        status=status,
    )
    session.add(company)
    await session.flush()

    owner = User(
        company_id=company.id,
        matricule=company.registration_code,
        full_name=owner_full_name,
        phone=company_phone,
        password_hash=hash_password(password),
        is_owner=True,
        is_active=True,
    )
    session.add(owner)
    await session.flush()
    return company, owner


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
