import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, require_permission
from app.schemas.dashboard import DashboardResponse
from app.services import dashboard_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(require_permission(PermissionCode.DASHBOARD_VIEW)),
) -> DashboardResponse:
    return await dashboard_service.build_dashboard(db, company_id)
