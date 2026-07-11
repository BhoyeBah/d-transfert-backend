import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, require_permission
from app.models.client import Client
from app.schemas.client import (
    ClientBalanceMovementResponse,
    ClientCreateRequest,
    ClientCurrencyBalance,
    ClientResponse,
)
from app.schemas.pagination import Page, PageParams, page_params
from app.services import client_service

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])

_require_manage = require_permission(PermissionCode.CLIENT_MANAGE)


def _to_response(client: Client, balances: list[tuple[str, Decimal]]) -> ClientResponse:
    response = ClientResponse.model_validate(client, from_attributes=True)
    response.balances = [ClientCurrencyBalance(currency=currency, balance=balance) for currency, balance in balances]
    return response


@router.get("", response_model=list[ClientResponse])
async def list_clients(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> list[ClientResponse]:
    clients = await client_service.list_clients(db, company_id)
    balances_by_client = await client_service.get_balances_by_currency_for_clients(
        db, [client.id for client in clients]
    )
    return [_to_response(client, balances_by_client.get(client.id, [])) for client in clients]


@router.get("/page", response_model=Page[ClientResponse])
async def list_clients_page(
    company_id: uuid.UUID = Depends(get_company_scope),
    params: PageParams = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> Page[ClientResponse]:
    clients, total = await client_service.list_clients_page(db, company_id, params)
    balances_by_client = await client_service.get_balances_by_currency_for_clients(
        db, [client.id for client in clients]
    )
    items = [_to_response(client, balances_by_client.get(client.id, [])) for client in clients]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> ClientResponse:
    client = await client_service.create_client(db, company_id, payload.name, payload.phone, payload.note)
    return _to_response(client, [])


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> ClientResponse:
    client = await client_service.get_client(db, company_id, client_id)
    balances = await client_service.get_balances_by_currency(db, client_id)
    return _to_response(client, balances)


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
