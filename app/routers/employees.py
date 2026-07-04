import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import get_company_scope, require_permission
from app.schemas.employee import (
    EmployeeCreateRequest,
    EmployeePermissionsUpdateRequest,
    EmployeeResponse,
    EmployeeStatusUpdateRequest,
)
from app.services import employee_service

router = APIRouter(prefix="/api/v1/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeResponse])
async def list_employees(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_permission(PermissionCode.EMPLOYEE_MANAGE)),
) -> list[EmployeeResponse]:
    return await employee_service.list_employees(db, company_id)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_permission(PermissionCode.EMPLOYEE_MANAGE)),
) -> EmployeeResponse:
    return await employee_service.create_employee(db, company_id, payload)


@router.patch("/{employee_id}/permissions", response_model=EmployeeResponse)
async def update_employee_permissions(
    employee_id: uuid.UUID,
    payload: EmployeePermissionsUpdateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_permission(PermissionCode.EMPLOYEE_MANAGE)),
) -> EmployeeResponse:
    return await employee_service.update_permissions(
        db, company_id, employee_id, payload.grant, payload.revoke
    )


@router.patch("/{employee_id}/status", response_model=EmployeeResponse)
async def update_employee_status(
    employee_id: uuid.UUID,
    payload: EmployeeStatusUpdateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_permission(PermissionCode.EMPLOYEE_MANAGE)),
) -> EmployeeResponse:
    return await employee_service.set_active_status(db, company_id, employee_id, payload.is_active)
