import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, get_current_user, require_permission
from app.schemas.pagination import Page, PageParams, page_params
from app.schemas.proof import ProofResponse
from app.schemas.transfer import (
    TransferApproveRequest,
    TransferCreateRequest,
    TransferRejectRequest,
    TransferResponse,
    TransferStatusHistoryResponse,
)
from app.services import proof_service, transfer_service

router = APIRouter(prefix="/api/v1/transfers", tags=["transfers"])

_require_create = require_permission(PermissionCode.TRANSFER_CREATE)
_require_validate = require_permission(PermissionCode.OPERATION_VALIDATE)


def _require_view_access(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.is_owner or current_user.is_super_admin:
        return current_user
    if (
        PermissionCode.TRANSFER_CREATE in current_user.permissions
        or PermissionCode.OPERATION_VALIDATE in current_user.permissions
    ):
        return current_user
    raise PermissionDeniedError(
        f"Permission requise : {PermissionCode.TRANSFER_CREATE} ou {PermissionCode.OPERATION_VALIDATE}"
    )


def _serialize(transfer, viewer_company_id: uuid.UUID) -> TransferResponse:
    response = TransferResponse.model_validate(transfer, from_attributes=True)
    if transfer.company_id != viewer_company_id:
        # Le taux privé appartient exclusivement à l'entreprise qui a créé l'envoi ;
        # il ne doit jamais être révélé au collaborateur qui consulte/valide l'envoi.
        response.private_rate_used = None
    return response


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    payload: TransferCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_create),
) -> TransferResponse:
    transfer = await transfer_service.create_transfer(db, company_id, current_user.id, payload)
    return _serialize(transfer, company_id)


@router.get("", response_model=list[TransferResponse])
async def list_transfers(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> list[TransferResponse]:
    transfers = await transfer_service.list_transfers(db, company_id)
    return [_serialize(transfer, company_id) for transfer in transfers]


@router.get("/page", response_model=Page[TransferResponse])
async def list_transfers_page(
    company_id: uuid.UUID = Depends(get_company_scope),
    params: PageParams = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> Page[TransferResponse]:
    transfers, total = await transfer_service.list_transfers_page(db, company_id, params)
    items = [_serialize(transfer, company_id) for transfer in transfers]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{transfer_id}", response_model=TransferResponse)
async def get_transfer(
    transfer_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> TransferResponse:
    transfer = await transfer_service.get_transfer(db, company_id, transfer_id)
    return _serialize(transfer, company_id)


@router.get("/{transfer_id}/status-history", response_model=list[TransferStatusHistoryResponse])
async def get_status_history(
    transfer_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> list[TransferStatusHistoryResponse]:
    history = await transfer_service.get_status_history(db, company_id, transfer_id)
    return [TransferStatusHistoryResponse.model_validate(item, from_attributes=True) for item in history]


@router.post("/{transfer_id}/approve", response_model=TransferResponse)
async def approve_transfer(
    transfer_id: uuid.UUID,
    payload: TransferApproveRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_validate),
) -> TransferResponse:
    transfer = await transfer_service.approve_transfer(
        db, company_id, current_user.id, transfer_id, payload.wallet_id, payload.proof_id
    )
    return _serialize(transfer, company_id)


@router.post("/{transfer_id}/reject", response_model=TransferResponse)
async def reject_transfer(
    transfer_id: uuid.UUID,
    payload: TransferRejectRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_validate),
) -> TransferResponse:
    transfer = await transfer_service.reject_transfer(
        db, company_id, current_user.id, transfer_id, payload.reason
    )
    return _serialize(transfer, company_id)


@router.post("/{transfer_id}/cancel", response_model=TransferResponse)
async def cancel_transfer(
    transfer_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_create),
) -> TransferResponse:
    transfer = await transfer_service.cancel_transfer(db, company_id, current_user.id, transfer_id)
    return _serialize(transfer, company_id)


@router.post("/{transfer_id}/proofs", response_model=ProofResponse, status_code=status.HTTP_201_CREATED)
async def upload_transfer_proof(
    transfer_id: uuid.UUID,
    file: UploadFile = File(...),
    note: str | None = Form(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_view_access),
) -> ProofResponse:
    content = await file.read()
    proof = await proof_service.upload_transfer_proof(
        db,
        company_id,
        current_user.id,
        transfer_id,
        file.filename or "preuve",
        file.content_type,
        content,
        note,
    )
    return ProofResponse.model_validate(proof, from_attributes=True)


@router.get("/{transfer_id}/proofs", response_model=list[ProofResponse])
async def list_transfer_proofs(
    transfer_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> list[ProofResponse]:
    proofs = await proof_service.list_transfer_proofs(db, company_id, transfer_id)
    return [ProofResponse.model_validate(proof, from_attributes=True) for proof in proofs]


@router.get("/{transfer_id}/proofs/{proof_id}/file")
async def download_transfer_proof(
    transfer_id: uuid.UUID,
    proof_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> FileResponse:
    proof = await proof_service.get_transfer_proof_file(db, company_id, transfer_id, proof_id)
    return FileResponse(proof.storage_path, media_type=proof.content_type, filename=proof.file_name)
