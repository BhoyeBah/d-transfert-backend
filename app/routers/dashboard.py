import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, require_permission
from app.schemas.dashboard import DashboardResponse, EmployeeDashboardResponse
from app.services import dashboard_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(require_permission(PermissionCode.DASHBOARD_VIEW)),
) -> DashboardResponse:
    return await dashboard_service.build_dashboard(db, company_id)


@router.get("/me", response_model=EmployeeDashboardResponse)
async def get_employee_dashboard(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(PermissionCode.DASHBOARD_VIEW)),
) -> EmployeeDashboardResponse:
    include_wallets = PermissionCode.WALLET_MANAGE in current_user.permissions
    return await dashboard_service.build_employee_dashboard(db, company_id, current_user.id, include_wallets)
