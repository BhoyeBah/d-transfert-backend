import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.permissions import CurrentUser, get_current_user
from app.schemas.audit_log import AuditLogResponse
from app.schemas.company import AdminCompanyStatusUpdateRequest, CompanyMeResponse
from app.services import admin_service, audit_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _require_super_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not current_user.is_super_admin:
        raise PermissionDeniedError("Réservé au Super Admin de la plateforme.")
    return current_user


@router.get("/companies", response_model=list[CompanyMeResponse])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> list[CompanyMeResponse]:
    companies = await admin_service.list_companies(db)
    return [CompanyMeResponse.model_validate(company, from_attributes=True) for company in companies]


@router.patch("/companies/{company_id}/status", response_model=CompanyMeResponse)
async def update_company_status(
    company_id: uuid.UUID,
    payload: AdminCompanyStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_super_admin),
) -> CompanyMeResponse:
    company = await admin_service.set_company_status(db, current_user.id, company_id, payload.status)
    return CompanyMeResponse.model_validate(company, from_attributes=True)


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_all_audit_logs(
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> list[AuditLogResponse]:
    logs = await audit_service.list_all(db)
    return [AuditLogResponse.model_validate(log, from_attributes=True) for log in logs]
