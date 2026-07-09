import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, require_permission
from app.schemas.pagination import Page, PageParams, page_params
from app.schemas.supplier import (
    SupplierBalanceMovementResponse,
    SupplierCreateRequest,
    SupplierRebalanceRequest,
    SupplierResponse,
)
from app.services import supplier_service

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])

_require_manage = require_permission(PermissionCode.SUPPLIER_MANAGE)


@router.get("", response_model=list[SupplierResponse])
async def list_suppliers(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> list[SupplierResponse]:
    suppliers = await supplier_service.list_suppliers(db, company_id)
    return [SupplierResponse.model_validate(supplier, from_attributes=True) for supplier in suppliers]


@router.get("/page", response_model=Page[SupplierResponse])
async def list_suppliers_page(
    company_id: uuid.UUID = Depends(get_company_scope),
    params: PageParams = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> Page[SupplierResponse]:
    suppliers, total = await supplier_service.list_suppliers_page(db, company_id, params)
    items = [SupplierResponse.model_validate(supplier, from_attributes=True) for supplier in suppliers]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> SupplierResponse:
    supplier = await supplier_service.create_supplier(db, company_id, payload)
    return SupplierResponse.model_validate(supplier, from_attributes=True)


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> SupplierResponse:
    supplier = await supplier_service.get_supplier(db, company_id, supplier_id)
    return SupplierResponse.model_validate(supplier, from_attributes=True)


@router.get("/{supplier_id}/movements", response_model=list[SupplierBalanceMovementResponse])
async def get_supplier_movements(
    supplier_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> list[SupplierBalanceMovementResponse]:
    movements = await supplier_service.get_movements(db, company_id, supplier_id)
    return [
        SupplierBalanceMovementResponse.model_validate(movement, from_attributes=True)
        for movement in movements
    ]


@router.post("/{supplier_id}/rebalance", response_model=SupplierBalanceMovementResponse)
async def rebalance_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierRebalanceRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> SupplierBalanceMovementResponse:
    movement = await supplier_service.rebalance_supplier(
        db, company_id, current_user.id, supplier_id, payload
    )
    return SupplierBalanceMovementResponse.model_validate(movement, from_attributes=True)
