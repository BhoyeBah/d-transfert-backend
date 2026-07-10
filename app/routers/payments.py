import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, get_current_user, require_permission
from app.schemas.pagination import Page, PageParams, page_params
from app.schemas.payment import (
    PaymentApproveRequest,
    PaymentCreateRequest,
    PaymentRejectRequest,
    PaymentResponse,
    PaymentStatusHistoryResponse,
)
from app.schemas.proof import ProofResponse
from app.services import payment_service, proof_service

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

_require_create = require_permission(PermissionCode.PAYMENT_CREATE)
_require_validate = require_permission(PermissionCode.OPERATION_VALIDATE)


def _require_view_access(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.is_owner or current_user.is_super_admin:
        return current_user
    if (
        PermissionCode.PAYMENT_CREATE in current_user.permissions
        or PermissionCode.OPERATION_VALIDATE in current_user.permissions
    ):
        return current_user
    raise PermissionDeniedError(
        f"Permission requise : {PermissionCode.PAYMENT_CREATE} ou {PermissionCode.OPERATION_VALIDATE}"
    )


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_create),
) -> PaymentResponse:
    payment = await payment_service.create_payment(db, company_id, current_user.id, payload)
    return PaymentResponse.model_validate(payment, from_attributes=True)


@router.get("", response_model=list[PaymentResponse])
async def list_payments(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> list[PaymentResponse]:
    payments = await payment_service.list_payments(db, company_id)
    return [PaymentResponse.model_validate(payment, from_attributes=True) for payment in payments]


@router.get("/page", response_model=Page[PaymentResponse])
async def list_payments_page(
    company_id: uuid.UUID = Depends(get_company_scope),
    params: PageParams = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> Page[PaymentResponse]:
    payments, total = await payment_service.list_payments_page(db, company_id, params)
    items = [PaymentResponse.model_validate(payment, from_attributes=True) for payment in payments]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> PaymentResponse:
    payment = await payment_service.get_payment(db, company_id, payment_id)
    return PaymentResponse.model_validate(payment, from_attributes=True)


@router.get("/{payment_id}/status-history", response_model=list[PaymentStatusHistoryResponse])
async def get_status_history(
    payment_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> list[PaymentStatusHistoryResponse]:
    history = await payment_service.get_status_history(db, company_id, payment_id)
    return [PaymentStatusHistoryResponse.model_validate(item, from_attributes=True) for item in history]


@router.post("/{payment_id}/approve", response_model=PaymentResponse)
async def approve_payment(
    payment_id: uuid.UUID,
    payload: PaymentApproveRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_validate),
) -> PaymentResponse:
    payment = await payment_service.approve_payment(
        db, company_id, current_user.id, payment_id, payload.proof_id
    )
    return PaymentResponse.model_validate(payment, from_attributes=True)


@router.post("/{payment_id}/reject", response_model=PaymentResponse)
async def reject_payment(
    payment_id: uuid.UUID,
    payload: PaymentRejectRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_validate),
) -> PaymentResponse:
    payment = await payment_service.reject_payment(
        db, company_id, current_user.id, payment_id, payload.reason
    )
    return PaymentResponse.model_validate(payment, from_attributes=True)


@router.post("/{payment_id}/cancel", response_model=PaymentResponse)
async def cancel_payment(
    payment_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_create),
) -> PaymentResponse:
    payment = await payment_service.cancel_payment(db, company_id, current_user.id, payment_id)
    return PaymentResponse.model_validate(payment, from_attributes=True)


@router.post("/{payment_id}/proofs", response_model=ProofResponse, status_code=status.HTTP_201_CREATED)
async def upload_payment_proof(
    payment_id: uuid.UUID,
    file: UploadFile = File(...),
    note: str | None = Form(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_view_access),
) -> ProofResponse:
    content = await file.read()
    proof = await proof_service.upload_payment_proof(
        db,
        company_id,
        current_user.id,
        payment_id,
        file.filename or "preuve",
        file.content_type,
        content,
        note,
    )
    return ProofResponse.model_validate(proof, from_attributes=True)


@router.get("/{payment_id}/proofs", response_model=list[ProofResponse])
async def list_payment_proofs(
    payment_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> list[ProofResponse]:
    proofs = await proof_service.list_payment_proofs(db, company_id, payment_id)
    return [ProofResponse.model_validate(proof, from_attributes=True) for proof in proofs]


@router.get("/{payment_id}/proofs/{proof_id}/file")
async def download_payment_proof(
    payment_id: uuid.UUID,
    proof_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> FileResponse:
    proof = await proof_service.get_payment_proof_file(db, company_id, payment_id, proof_id)
    return FileResponse(
        proof.storage_path,
        media_type=proof.content_type,
        filename=proof.file_name,
        content_disposition_type="inline",
    )
