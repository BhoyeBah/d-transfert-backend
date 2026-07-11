import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, get_current_user, require_permission
from app.models.entry import Entry
from app.models.entry_allocation import EntryAllocation
from app.models.entry_line import EntryLine
from app.schemas.entry import (
    EntryAllocationResponse,
    EntryCreateRequest,
    EntryLineResponse,
    EntryMergeRequest,
    EntryResponse,
)
from app.schemas.pagination import Page, PageParams, page_params
from app.services import entry_service

router = APIRouter(prefix="/api/v1/entries", tags=["entries"])

_require_manage = require_permission(PermissionCode.ENTRY_MANAGE)

# Créer/fusionner/annuler une entrée reste réservé à entry.manage. Mais un collaborateur ayant
# transfer.create, payment.create ou operation.validate a nécessairement besoin de lire les
# entrées de son entreprise — pour choisir la source d'un envoi/paiement et pour afficher son
# détail depuis un envoi/paiement qui la référence — ces lectures sont déjà bornées à
# l'entreprise de l'appelant (get_company_scope), donc les élargir à ces permissions ne fuite
# rien vers d'autres entreprises.
def _require_view_access(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.is_owner or current_user.is_super_admin:
        return current_user
    if (
        PermissionCode.ENTRY_MANAGE in current_user.permissions
        or PermissionCode.TRANSFER_CREATE in current_user.permissions
        or PermissionCode.PAYMENT_CREATE in current_user.permissions
        or PermissionCode.OPERATION_VALIDATE in current_user.permissions
    ):
        return current_user
    raise PermissionDeniedError(
        f"Permission requise : {PermissionCode.ENTRY_MANAGE}, {PermissionCode.TRANSFER_CREATE}, "
        f"{PermissionCode.PAYMENT_CREATE} ou {PermissionCode.OPERATION_VALIDATE}"
    )


def _to_response(
    entry: Entry, lines: list[EntryLine], allocations: list[EntryAllocation]
) -> EntryResponse:
    return EntryResponse(
        id=entry.id,
        reference=entry.reference,
        status=entry.status,
        client_name=entry.client_name,
        client_phone=entry.client_phone,
        note=entry.note,
        merged_into_id=entry.merged_into_id,
        created_by_id=entry.created_by_id,
        created_at=entry.created_at,
        lines=[EntryLineResponse.model_validate(line, from_attributes=True) for line in lines],
        allocations=[
            EntryAllocationResponse.model_validate(allocation, from_attributes=True)
            for allocation in allocations
        ],
        available_by_currency=entry_service.available_by_currency(lines, allocations),
    )


@router.post("", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    payload: EntryCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> EntryResponse:
    entry, lines = await entry_service.create_entry(db, company_id, current_user.id, payload)
    return _to_response(entry, lines, [])


@router.get("", response_model=list[EntryResponse])
async def list_entries(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> list[EntryResponse]:
    results = await entry_service.list_entries(db, company_id)
    return [_to_response(entry, lines, allocations) for entry, lines, allocations in results]


@router.get("/page", response_model=Page[EntryResponse])
async def list_entries_page(
    company_id: uuid.UUID = Depends(get_company_scope),
    params: PageParams = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> Page[EntryResponse]:
    results, total = await entry_service.list_entries_page(db, company_id, params)
    items = [_to_response(entry, lines, allocations) for entry, lines, allocations in results]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(
    entry_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> EntryResponse:
    entry, lines, allocations = await entry_service.get_entry(db, company_id, entry_id)
    return _to_response(entry, lines, allocations)


@router.post("/merge", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
async def merge_entries(
    payload: EntryMergeRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> EntryResponse:
    entry, lines = await entry_service.merge_entries(db, company_id, current_user.id, payload)
    return _to_response(entry, lines, [])


@router.post("/{entry_id}/cancel", response_model=EntryResponse)
async def cancel_entry(
    entry_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> EntryResponse:
    entry, lines = await entry_service.cancel_entry(db, company_id, current_user.id, entry_id)
    allocations = await entry_service.get_entry(db, company_id, entry_id)
    return _to_response(entry, lines, allocations[2])
