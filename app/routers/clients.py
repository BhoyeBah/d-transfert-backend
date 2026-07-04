import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, require_permission
from app.schemas.client import ClientBalanceMovementResponse, ClientCreateRequest, ClientResponse
from app.services import client_service

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])

_require_manage = require_permission(PermissionCode.CLIENT_MANAGE)


@router.get("", response_model=list[ClientResponse])
async def list_clients(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> list[ClientResponse]:
    clients = await client_service.list_clients(db, company_id)
    return [ClientResponse.model_validate(client, from_attributes=True) for client in clients]


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> ClientResponse:
    client = await client_service.create_client(db, company_id, payload.name, payload.phone, payload.note)
    return ClientResponse.model_validate(client, from_attributes=True)


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> ClientResponse:
    client = await client_service.get_client(db, company_id, client_id)
    return ClientResponse.model_validate(client, from_attributes=True)


@router.get("/{client_id}/movements", response_model=list[ClientBalanceMovementResponse])
async def get_client_movements(
    client_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> list[ClientBalanceMovementResponse]:
    movements = await client_service.get_movements(db, company_id, client_id)
    return [
        ClientBalanceMovementResponse.model_validate(movement, from_attributes=True)
        for movement in movements
    ]
