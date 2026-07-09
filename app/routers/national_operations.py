import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, require_permission
from app.models.national_operation import NationalOperation, NationalOperationType
from app.models.national_operation_line import NationalOperationLine
from app.schemas.national_operation import (
    NationalOperationCreateRequest,
    NationalOperationLineResponse,
    NationalOperationResponse,
)
from app.schemas.pagination import Page, PageParams, page_params
from app.services import national_operation_service

router = APIRouter(prefix="/api/v1/national-operations", tags=["national-operations"])

_require_manage = require_permission(PermissionCode.NATIONAL_OPERATION_MANAGE)


def _to_response(
    operation: NationalOperation, lines: list[NationalOperationLine]
) -> NationalOperationResponse:
    return NationalOperationResponse(
        id=operation.id,
        reference=operation.reference,
        type=operation.type,
        status=operation.status,
        client_name=operation.client_name,
        client_phone=operation.client_phone,
        note=operation.note,
        exchange_rate=operation.exchange_rate,
        proof_id=operation.proof_id,
        created_by_id=operation.created_by_id,
        validated_at=operation.validated_at,
        cancelled_at=operation.cancelled_at,
        reversal_of_id=operation.reversal_of_id,
        created_at=operation.created_at,
        lines=[
            NationalOperationLineResponse.model_validate(line, from_attributes=True) for line in lines
        ],
    )


async def _create(
    operation_type: NationalOperationType,
    payload: NationalOperationCreateRequest,
    company_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession,
) -> NationalOperationResponse:
    operation, lines = await national_operation_service.create_operation(
        db, company_id, operation_type, current_user.id, payload
    )
    return _to_response(operation, lines)


@router.post("/deposits", response_model=NationalOperationResponse, status_code=status.HTTP_201_CREATED)
async def create_deposit(
    payload: NationalOperationCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> NationalOperationResponse:
    return await _create(NationalOperationType.DEPOSIT, payload, company_id, current_user, db)


@router.post("/withdrawals", response_model=NationalOperationResponse, status_code=status.HTTP_201_CREATED)
async def create_withdrawal(
    payload: NationalOperationCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> NationalOperationResponse:
    return await _create(NationalOperationType.WITHDRAWAL, payload, company_id, current_user, db)


@router.post("/exchanges", response_model=NationalOperationResponse, status_code=status.HTTP_201_CREATED)
async def create_exchange(
    payload: NationalOperationCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> NationalOperationResponse:
    return await _create(NationalOperationType.EXCHANGE, payload, company_id, current_user, db)


@router.post("/rebalances", response_model=NationalOperationResponse, status_code=status.HTTP_201_CREATED)
async def create_rebalance(
    payload: NationalOperationCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> NationalOperationResponse:
    return await _create(NationalOperationType.REBALANCE, payload, company_id, current_user, db)


@router.get("", response_model=list[NationalOperationResponse])
async def list_operations(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> list[NationalOperationResponse]:
    results = await national_operation_service.list_operations(db, company_id)
    return [_to_response(operation, lines) for operation, lines in results]


@router.get("/page", response_model=Page[NationalOperationResponse])
async def list_operations_page(
    company_id: uuid.UUID = Depends(get_company_scope),
    params: PageParams = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> Page[NationalOperationResponse]:
    results, total = await national_operation_service.list_operations_page(db, company_id, params)
    items = [_to_response(operation, lines) for operation, lines in results]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{operation_id}", response_model=NationalOperationResponse)
async def get_operation(
    operation_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> NationalOperationResponse:
    operation, lines = await national_operation_service.get_operation(db, company_id, operation_id)
    return _to_response(operation, lines)


@router.post("/{operation_id}/cancel", response_model=NationalOperationResponse)
async def cancel_operation(
    operation_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> NationalOperationResponse:
    operation, lines = await national_operation_service.cancel_operation(
        db, company_id, operation_id, current_user.id
    )
    return _to_response(operation, lines)
