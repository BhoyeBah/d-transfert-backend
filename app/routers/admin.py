import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.permissions import CurrentUser, get_current_user
from app.schemas.admin import (
    AdminCompanyDetailResponse,
    AdminPlatformStatsResponse,
    AdminUserResponse,
    AdminUserStatusUpdateRequest,
    AdminUserUpdateRequest,
    PlatformAdminCreateRequest,
    PlatformSettingsResponse,
    PlatformSettingsUpdateRequest,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
    SystemLogResponse,
)
from app.schemas.audit_log import AuditLogResponse
from app.schemas.auth import RegisterResponse
from app.schemas.company import (
    AdminCompanyCreateRequest,
    AdminCompanyStatusUpdateRequest,
    AdminCompanyUpdateRequest,
    CompanyMeResponse,
)
from app.schemas.pagination import Page, PageParams, page_params
from app.services import admin_service, audit_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _require_super_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not current_user.is_super_admin:
        raise PermissionDeniedError("Réservé au Super Admin de la plateforme.")
    return current_user


@router.get("/stats", response_model=AdminPlatformStatsResponse)
async def get_platform_stats(
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> AdminPlatformStatsResponse:
    return await admin_service.get_platform_stats(db)


@router.get("/companies", response_model=list[CompanyMeResponse])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> list[CompanyMeResponse]:
    companies = await admin_service.list_companies(db)
    return [CompanyMeResponse.model_validate(company, from_attributes=True) for company in companies]


@router.get("/companies/page", response_model=Page[CompanyMeResponse])
async def list_companies_page(
    params: PageParams = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> Page[CompanyMeResponse]:
    companies, total = await admin_service.list_companies_page(db, params)
    items = [CompanyMeResponse.model_validate(company, from_attributes=True) for company in companies]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("/companies", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: AdminCompanyCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_super_admin),
) -> RegisterResponse:
    return await admin_service.create_company(db, current_user.id, payload)


@router.get("/companies/{company_id}", response_model=AdminCompanyDetailResponse)
async def get_company_detail(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> AdminCompanyDetailResponse:
    return await admin_service.get_company_detail(db, company_id)


@router.patch("/companies/{company_id}", response_model=CompanyMeResponse)
async def update_company(
    company_id: uuid.UUID,
    payload: AdminCompanyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_super_admin),
) -> CompanyMeResponse:
    company = await admin_service.update_company(db, current_user.id, company_id, payload)
    return CompanyMeResponse.model_validate(company, from_attributes=True)


@router.patch("/companies/{company_id}/status", response_model=CompanyMeResponse)
async def update_company_status(
    company_id: uuid.UUID,
    payload: AdminCompanyStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_super_admin),
) -> CompanyMeResponse:
    company = await admin_service.set_company_status(db, current_user.id, company_id, payload.status)
    return CompanyMeResponse.model_validate(company, from_attributes=True)


@router.delete(
    "/companies/{company_id}",
    status_code=status.HTTP_200_OK,
    summary="Supprimer une entreprise et toutes ses données",
)
async def delete_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_super_admin),
) -> dict:
    await admin_service.delete_company(db, current_user.id, company_id)
    return {"detail": "Entreprise et toutes ses données supprimées avec succès.", "company_id": str(company_id)}



@router.get("/companies/{company_id}/users", response_model=list[AdminUserResponse])
async def list_company_users(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> list[AdminUserResponse]:
    return await admin_service.list_company_users(db, company_id)


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
async def update_user_status(
    user_id: uuid.UUID,
    payload: AdminUserStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_super_admin),
) -> AdminUserResponse:
    return await admin_service.set_user_status(db, current_user.id, user_id, payload.is_active)


@router.patch("/platform-admins/{admin_id}", response_model=AdminUserResponse)
async def update_platform_admin(
    admin_id: uuid.UUID,
    payload: AdminUserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_super_admin),
) -> AdminUserResponse:
    return await admin_service.update_platform_admin(db, current_user.id, admin_id, payload)


@router.delete("/platform-admins/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_platform_admin(
    admin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_super_admin),
) -> None:
    await admin_service.delete_platform_admin(db, current_user.id, admin_id)


@router.get("/platform-admins", response_model=list[AdminUserResponse])
async def list_platform_admins(
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> list[AdminUserResponse]:
    return await admin_service.list_platform_admins(db)


@router.get("/platform-admins/page", response_model=Page[AdminUserResponse])
async def list_platform_admins_page(
    params: PageParams = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> Page[AdminUserResponse]:
    items, total = await admin_service.list_platform_admins_page(db, params)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("/platform-admins", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_platform_admin(
    payload: PlatformAdminCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_super_admin),
) -> AdminUserResponse:
    return await admin_service.create_platform_admin(db, current_user.id, payload)


@router.get("/companies/{company_id}/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> SubscriptionResponse:
    return await admin_service.get_subscription(db, company_id)


@router.patch("/companies/{company_id}/subscription", response_model=SubscriptionResponse)
async def update_subscription(
    company_id: uuid.UUID,
    payload: SubscriptionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_super_admin),
) -> SubscriptionResponse:
    return await admin_service.update_subscription(db, current_user.id, company_id, payload)


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_all_audit_logs(
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> list[AuditLogResponse]:
    logs = await audit_service.list_all(db)
    return [AuditLogResponse.model_validate(log, from_attributes=True) for log in logs]


@router.get("/audit-logs/page", response_model=Page[AuditLogResponse])
async def list_all_audit_logs_page(
    params: PageParams = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> Page[AuditLogResponse]:
    logs, total = await audit_service.list_all_page(db, params)
    items = [AuditLogResponse.model_validate(log, from_attributes=True) for log in logs]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/system-logs", response_model=list[SystemLogResponse])
async def list_system_logs(
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> list[SystemLogResponse]:
    return await admin_service.list_system_logs(db)


@router.get("/system-logs/page", response_model=Page[SystemLogResponse])
async def list_system_logs_page(
    params: PageParams = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> Page[SystemLogResponse]:
    items, total = await admin_service.list_system_logs_page(db, params)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/settings", response_model=PlatformSettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_super_admin),
) -> PlatformSettingsResponse:
    return await admin_service.get_settings(db)


@router.patch("/settings", response_model=PlatformSettingsResponse)
async def update_settings(
    payload: PlatformSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_super_admin),
) -> PlatformSettingsResponse:
    return await admin_service.update_settings(db, current_user.id, payload)
