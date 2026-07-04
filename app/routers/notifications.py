import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, require_permission
from app.schemas.notification import NotificationResponse
from app.services import notification_service

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

_require_view = require_permission(PermissionCode.DASHBOARD_VIEW)


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> list[NotificationResponse]:
    notifications = await notification_service.list_notifications(db, company_id)
    return [
        NotificationResponse.model_validate(notification, from_attributes=True)
        for notification in notifications
    ]


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> NotificationResponse:
    notification = await notification_service.mark_as_read(db, company_id, notification_id)
    return NotificationResponse.model_validate(notification, from_attributes=True)
