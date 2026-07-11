import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, require_any_permission, require_permission
from app.schemas.pagination import Page, PageParams, page_params
from app.schemas.wallet import (
    WalletCreateRequest,
    WalletMovementResponse,
    WalletOptionResponse,
    WalletResponse,
    WalletStatusUpdateRequest,
    WalletUpdateRequest,
)
from app.services import wallet_service

router = APIRouter(prefix="/api/v1/wallets", tags=["wallets"])


@router.get("/options", response_model=list[WalletOptionResponse])
async def list_wallet_options(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(
        require_any_permission(
            PermissionCode.ENTRY_MANAGE,
            PermissionCode.TRANSFER_CREATE,
            PermissionCode.PAYMENT_CREATE,
            PermissionCode.OPERATION_VALIDATE,
        )
    ),
) -> list[WalletOptionResponse]:
    """Return the minimum wallet data needed to create and display entries."""
    return await wallet_service.list_wallets(db, company_id)


@router.get("", response_model=list[WalletResponse])
async def list_wallets(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(require_permission(PermissionCode.WALLET_MANAGE)),
) -> list[WalletResponse]:
    return await wallet_service.list_wallets(db, company_id)


@router.get("/page", response_model=Page[WalletResponse])
async def list_wallets_page(
    company_id: uuid.UUID = Depends(get_company_scope),
    params: PageParams = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(require_permission(PermissionCode.WALLET_MANAGE)),
) -> Page[WalletResponse]:
    items, total = await wallet_service.list_wallets_page(db, company_id, params)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    payload: WalletCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(PermissionCode.WALLET_MANAGE)),
) -> WalletResponse:
    return await wallet_service.create_wallet(db, company_id, current_user.id, payload)


@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(
    wallet_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(require_permission(PermissionCode.WALLET_MANAGE)),
) -> WalletResponse:
    return await wallet_service.get_wallet(db, company_id, wallet_id)


@router.patch("/{wallet_id}", response_model=WalletResponse)
async def update_wallet(
    wallet_id: uuid.UUID,
    payload: WalletUpdateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(PermissionCode.WALLET_MANAGE)),
) -> WalletResponse:
    return await wallet_service.update_wallet(db, company_id, current_user.id, wallet_id, payload)


@router.patch("/{wallet_id}/status", response_model=WalletResponse)
async def update_wallet_status(
    wallet_id: uuid.UUID,
    payload: WalletStatusUpdateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(PermissionCode.WALLET_MANAGE)),
) -> WalletResponse:
    return await wallet_service.set_wallet_status(db, company_id, current_user.id, wallet_id, payload.status)


@router.get("/{wallet_id}/movements", response_model=list[WalletMovementResponse])
async def list_wallet_movements(
    wallet_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(require_permission(PermissionCode.WALLET_MANAGE)),
) -> list[WalletMovementResponse]:
    return await wallet_service.list_wallet_movements(db, company_id, wallet_id)
