import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser, get_company_scope, get_current_user
from app.repositories import company_repository
from app.schemas.company import AdminCompanyUpdateRequest, CompanyMeResponse, CompanyPublicLookupResponse
from app.services import company_service

router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


@router.get("/me", response_model=CompanyMeResponse)
async def get_my_company(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
) -> CompanyMeResponse:
    company = await company_repository.get_by_id(db, company_id)
    if company is None:
        raise NotFoundError("Entreprise introuvable.")
    return CompanyMeResponse.model_validate(company, from_attributes=True)


@router.patch("/me", response_model=CompanyMeResponse)
async def update_my_company(
    payload: AdminCompanyUpdateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CompanyMeResponse:
    if not current_user.is_owner and not current_user.is_super_admin:
        raise PermissionDeniedError("Réservé à l'owner de l'entreprise.")
    company = await company_service.update_my_company(db, company_id, current_user.id, payload)
    return CompanyMeResponse.model_validate(company, from_attributes=True)


@router.get("/lookup/{matricule}", response_model=CompanyPublicLookupResponse)
async def lookup_company(
    matricule: str,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> CompanyPublicLookupResponse:
    company = await company_repository.get_by_registration_code(db, matricule)
    if company is None:
        raise NotFoundError("Entreprise introuvable.")
    return CompanyPublicLookupResponse.model_validate(company, from_attributes=True)
