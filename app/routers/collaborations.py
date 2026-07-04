import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, require_permission
from app.models.collaboration import Collaboration, CollaborationRateHistory
from app.schemas.collaboration import (
    CollaborationDecisionRequest,
    CollaborationRateHistoryResponse,
    CollaborationRequestCreate,
    CollaborationResponse,
    RateProposalCreateRequest,
    RateProposalDecisionRequest,
)
from app.schemas.transfer import CollaboratorBalanceResponse
from app.services import collaboration_service

router = APIRouter(prefix="/api/v1/collaborations", tags=["collaborations"])

_require_manage = require_permission(PermissionCode.COLLABORATION_MANAGE)


def _to_response(
    collaboration: Collaboration, current_rate: CollaborationRateHistory | None
) -> CollaborationResponse:
    return CollaborationResponse(
        id=collaboration.id,
        initiator_company_id=collaboration.initiator_company_id,
        target_company_id=collaboration.target_company_id,
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
    return _to_response(collaboration, None)


@router.get("", response_model=list[CollaborationResponse])
async def list_collaborations(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> list[CollaborationResponse]:
    results = await collaboration_service.list_collaborations(db, company_id)
    return [_to_response(collaboration, rate) for collaboration, rate in results]


@router.get("/{collaboration_id}", response_model=CollaborationResponse)
async def get_collaboration(
    collaboration_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
) -> CollaborationResponse:
    collaboration, rate = await collaboration_service.get_collaboration(db, company_id, collaboration_id)
    return _to_response(collaboration, rate)


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
    return _to_response(collaboration, rate)


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
    return _to_response(collaboration, None)


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
    _current_user: CurrentUser = Depends(_require_manage),
) -> CollaborationRateHistoryResponse:
    proposal = await collaboration_service.propose_rate_change(
        db, company_id, collaboration_id, payload.new_rate, payload.note
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
    _current_user: CurrentUser = Depends(_require_manage),
) -> CollaborationRateHistoryResponse:
    proposal = await collaboration_service.reject_rate_proposal(
        db, company_id, collaboration_id, proposal_id, payload.reason
    )
    return CollaborationRateHistoryResponse.model_validate(proposal, from_attributes=True)


@router.get("/{collaboration_id}/rate-history", response_model=list[CollaborationRateHistoryResponse])
async def get_rate_history(
    collaboration_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_manage),
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
