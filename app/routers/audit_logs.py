import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, require_permission
from app.schemas.audit_log import AuditLogResponse
from app.services import audit_service

router = APIRouter(prefix="/api/v1/audit-logs", tags=["audit-logs"])

_require_view = require_permission(PermissionCode.REPORT_VIEW)


@router.get("", response_model=list[AuditLogResponse])
async def list_audit_logs(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> list[AuditLogResponse]:
    logs = await audit_service.list_for_company(db, company_id)
    return [AuditLogResponse.model_validate(log, from_attributes=True) for log in logs]
