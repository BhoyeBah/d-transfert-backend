import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, get_current_user, require_permission
from app.models.collaboration import Collaboration, CollaborationRateHistory
from app.repositories import company_repository
from app.schemas.collaboration import (
    CollaborationDecisionRequest,
    CollaborationRateHistoryResponse,
    CollaborationRequestCreate,
    CollaborationResponse,
    RateProposalCreateRequest,
    RateProposalDecisionRequest,
)
from app.schemas.pagination import Page, PageParams, page_params
from app.schemas.transfer import CollaboratorBalanceResponse
from app.services import collaboration_service

router = APIRouter(prefix="/api/v1/collaborations", tags=["collaborations"])

_require_manage = require_permission(PermissionCode.COLLABORATION_MANAGE)

# Gérer une collaboration (proposer/accepter un taux, accepter/rejeter la demande) reste
# réservé à collaboration.manage. Mais un collaborateur ayant transfer.create, payment.create
# ou operation.validate a nécessairement besoin de lire les collaborations de son entreprise —
# pour choisir vers qui envoyer, et pour afficher le nom du partenaire / la devise sur le détail
# d'un envoi ou d'un paiement — ces lectures sont déjà bornées à l'entreprise de l'appelant
# (get_company_scope), donc les élargir à ces permissions ne fuite rien vers d'autres entreprises.
def _require_view_access(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.is_owner or current_user.is_super_admin:
        return current_user
    if (
        PermissionCode.COLLABORATION_MANAGE in current_user.permissions
        or PermissionCode.TRANSFER_CREATE in current_user.permissions
        or PermissionCode.PAYMENT_CREATE in current_user.permissions
        or PermissionCode.OPERATION_VALIDATE in current_user.permissions
    ):
        return current_user
    raise PermissionDeniedError(
        f"Permission requise : {PermissionCode.COLLABORATION_MANAGE}, {PermissionCode.TRANSFER_CREATE}, "
        f"{PermissionCode.PAYMENT_CREATE} ou {PermissionCode.OPERATION_VALIDATE}"
    )


def _other_party(collaboration: Collaboration, company_id: uuid.UUID) -> uuid.UUID:
    if collaboration.initiator_company_id == company_id:
        return collaboration.target_company_id
    return collaboration.initiator_company_id


async def _to_response(
    db: AsyncSession,
    company_id: uuid.UUID,
    collaboration: Collaboration,
    current_rate: CollaborationRateHistory | None,
) -> CollaborationResponse:
    counterparty = await company_repository.get_by_id(db, _other_party(collaboration, company_id))
    return CollaborationResponse(
        id=collaboration.id,
        initiator_company_id=collaboration.initiator_company_id,
        target_company_id=collaboration.target_company_id,
        counterparty_company_name=counterparty.name if counterparty else "—",
        counterparty_company_matricule=counterparty.registration_code if counterparty else "—",
        currency=collaboration.currency,
        status=collaboration.status,
        note=collaboration.note,
        current_rate=current_rate.new_rate if current_rate else None,
        created_at=collaboration.created_at,
    )


@router.post("", response_model=CollaborationResponse, status_code=status.HTTP_201_CREATED)
async def request_collaboration(
    payload: CollaborationRequestCreate,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> CollaborationResponse:
    collaboration, _proposal = await collaboration_service.request_collaboration(db, company_id, payload)
    return await _to_response(db, company_id, collaboration, None)


@router.get("", response_model=list[CollaborationResponse])
async def list_collaborations(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> list[CollaborationResponse]:
    results = await collaboration_service.list_collaborations(db, company_id)
    return [await _to_response(db, company_id, collaboration, rate) for collaboration, rate in results]


@router.get("/page", response_model=Page[CollaborationResponse])
async def list_collaborations_page(
    company_id: uuid.UUID = Depends(get_company_scope),
    params: PageParams = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> Page[CollaborationResponse]:
    results, total = await collaboration_service.list_collaborations_page(db, company_id, params)
    items = [await _to_response(db, company_id, collaboration, rate) for collaboration, rate in results]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{collaboration_id}", response_model=CollaborationResponse)
async def get_collaboration(
    collaboration_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> CollaborationResponse:
    collaboration, rate = await collaboration_service.get_collaboration(db, company_id, collaboration_id)
    return await _to_response(db, company_id, collaboration, rate)


@router.post("/{collaboration_id}/accept", response_model=CollaborationResponse)
async def accept_collaboration(
    collaboration_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> CollaborationResponse:
    collaboration, rate = await collaboration_service.accept_collaboration(
        db, company_id, current_user.id, collaboration_id
    )
    return await _to_response(db, company_id, collaboration, rate)


@router.post("/{collaboration_id}/reject", response_model=CollaborationResponse)
async def reject_collaboration(
    collaboration_id: uuid.UUID,
    payload: CollaborationDecisionRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> CollaborationResponse:
    collaboration = await collaboration_service.reject_collaboration(
        db, company_id, current_user.id, collaboration_id, payload.reason
    )
    return await _to_response(db, company_id, collaboration, None)


@router.post(
    "/{collaboration_id}/rate-proposals",
    response_model=CollaborationRateHistoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def propose_rate_change(
    collaboration_id: uuid.UUID,
    payload: RateProposalCreateRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> CollaborationRateHistoryResponse:
    proposal = await collaboration_service.propose_rate_change(
        db, company_id, current_user.id, collaboration_id, payload.new_rate, payload.note
    )
    return CollaborationRateHistoryResponse.model_validate(proposal, from_attributes=True)


@router.post(
    "/{collaboration_id}/rate-proposals/{proposal_id}/accept",
    response_model=CollaborationRateHistoryResponse,
)
async def accept_rate_proposal(
    collaboration_id: uuid.UUID,
    proposal_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> CollaborationRateHistoryResponse:
    proposal = await collaboration_service.accept_rate_proposal(
        db, company_id, current_user.id, collaboration_id, proposal_id
    )
    return CollaborationRateHistoryResponse.model_validate(proposal, from_attributes=True)


@router.post(
    "/{collaboration_id}/rate-proposals/{proposal_id}/reject",
    response_model=CollaborationRateHistoryResponse,
)
async def reject_rate_proposal(
    collaboration_id: uuid.UUID,
    proposal_id: uuid.UUID,
    payload: RateProposalDecisionRequest,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> CollaborationRateHistoryResponse:
    proposal = await collaboration_service.reject_rate_proposal(
        db, company_id, current_user.id, collaboration_id, proposal_id, payload.reason
    )
    return CollaborationRateHistoryResponse.model_validate(proposal, from_attributes=True)


@router.get("/{collaboration_id}/rate-history", response_model=list[CollaborationRateHistoryResponse])
async def get_rate_history(
    collaboration_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view_access),
) -> list[CollaborationRateHistoryResponse]:
    history = await collaboration_service.get_rate_history(db, company_id, collaboration_id)
    return [CollaborationRateHistoryResponse.model_validate(item, from_attributes=True) for item in history]


@router.get("/{collaboration_id}/balance", response_model=CollaboratorBalanceResponse)
async def get_balance(
    collaboration_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> CollaboratorBalanceResponse:
    collaboration, _rate = await collaboration_service.get_collaboration(db, company_id, collaboration_id)
    balance = await collaboration_service.get_balance(db, company_id, collaboration_id)
    return CollaboratorBalanceResponse(
        collaboration_id=collaboration_id, currency=collaboration.currency, balance=balance
    )


@router.post("/{collaboration_id}/suspend", response_model=CollaborationResponse)
async def suspend_collaboration(
    collaboration_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> CollaborationResponse:
    collaboration = await collaboration_service.suspend_collaboration(
        db, company_id, current_user.id, collaboration_id
    )
    # We fetch the rate to return the proper CollaborationResponse
    _, rate = await collaboration_service.get_collaboration(db, company_id, collaboration_id)
    return await _to_response(db, company_id, collaboration, rate)


@router.post("/{collaboration_id}/archive", response_model=CollaborationResponse)
async def archive_collaboration(
    collaboration_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(_require_manage),
) -> CollaborationResponse:
    collaboration = await collaboration_service.archive_collaboration(
        db, company_id, current_user.id, collaboration_id
    )
    _, rate = await collaboration_service.get_collaboration(db, company_id, collaboration_id)
    return await _to_response(db, company_id, collaboration, rate)

