import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.permissions import get_company_scope, get_current_user
from app.repositories import company_repository
from app.schemas.company import CompanyMeResponse, CompanyPublicLookupResponse

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
