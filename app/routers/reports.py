import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, require_permission
from app.schemas.dashboard import DailyReportResponse
from app.services import dashboard_service

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

_require_view = require_permission(PermissionCode.REPORT_VIEW)
_require_export = require_permission(PermissionCode.REPORT_EXPORT)


@router.get("/daily", response_model=DailyReportResponse)
async def get_daily_report(
    report_date: date = Query(default=None, alias="date"),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> DailyReportResponse:
    target_date = report_date or date.today()
    return await dashboard_service.build_daily_report(db, company_id, target_date)


@router.get("/daily/export", response_class=PlainTextResponse)
async def export_daily_report_csv(
    report_date: date = Query(default=None, alias="date"),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_export),
) -> PlainTextResponse:
    target_date = report_date or date.today()
    report = await dashboard_service.build_daily_report(db, company_id, target_date)
    csv_content = dashboard_service.daily_report_to_csv(report)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=rapport-{target_date.isoformat()}.csv"},
    )
