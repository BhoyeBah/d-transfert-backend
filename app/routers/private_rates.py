import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, require_permission
from app.schemas.private_rate import (
    PrivateRateCreateRequest,
    PrivateRateResponse,
    PrivateRateStatusUpdateRequest,
)
from app.services import private_rate_service

router = APIRouter(prefix="/api/v1/private-rates", tags=["private-rates"])


@router.get("", response_model=list[PrivateRateResponse])
async def list_rates(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(require_permission(PermissionCode.RATE_PRIVATE_VIEW)),
) -> list[PrivateRateResponse]:
    rates = await private_rate_service.list_rates(db, company_id)
    return [PrivateRateResponse.model_validate(rate, from_attributes=True) for rate in rates]


@router.post("", response_model=PrivateRateResponse, status_code=status.HTTP_201_CREATED)
async def set_rate(
    payload: PrivateRateCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(PermissionCode.RATE_PRIVATE_MANAGE)),
) -> PrivateRateResponse:
    rate = await private_rate_service.set_rate(db, company_id, current_user.id, payload)
    return PrivateRateResponse.model_validate(rate, from_attributes=True)


@router.patch("/{rate_id}/status", response_model=PrivateRateResponse)
async def update_rate_status(
    rate_id: uuid.UUID,
    payload: PrivateRateStatusUpdateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(require_permission(PermissionCode.RATE_PRIVATE_MANAGE)),
) -> PrivateRateResponse:
    rate = await private_rate_service.set_active_status(db, company_id, rate_id, payload.is_active)
    return PrivateRateResponse.model_validate(rate, from_attributes=True)
