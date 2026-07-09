import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models.collaboration import (
    Collaboration,
    CollaborationRateHistory,
    CollaborationStatus,
    RateProposalStatus,
)
from app.models.notification import NotificationType
from app.repositories import collaboration_repository, collaborator_balance_repository, company_repository
from app.schemas.collaboration import CollaborationRequestCreate
from app.schemas.pagination import PageParams
from app.services import audit_service, notification_service


async def _get_owned_collaboration(
    session: AsyncSession, company_id: uuid.UUID, collaboration_id: uuid.UUID
) -> Collaboration:
    collaboration = await collaboration_repository.get_by_id(session, collaboration_id)
    if collaboration is None or company_id not in (
        collaboration.initiator_company_id,
        collaboration.target_company_id,
    ):
        raise NotFoundError("Collaboration introuvable.")
    return collaboration


async def request_collaboration(
    session: AsyncSession, company_id: uuid.UUID, payload: CollaborationRequestCreate
) -> tuple[Collaboration, CollaborationRateHistory]:
    target = await company_repository.get_by_registration_code(session, payload.target_matricule)
    if target is None:
        raise NotFoundError("Entreprise cible introuvable.")

    if target.id == company_id:
        raise ConflictError("Une entreprise ne peut pas collaborer avec elle-même.")

    if await collaboration_repository.get_active_between(session, company_id, target.id) is not None:
        raise ConflictError("Une collaboration active ou en attente existe déjà avec cette entreprise.")

    collaboration = Collaboration(
        initiator_company_id=company_id,
        target_company_id=target.id,
        currency=payload.currency,
        status=CollaborationStatus.PENDING,
        note=payload.note,
    )
    session.add(collaboration)
    await session.flush()

    proposal = CollaborationRateHistory(
        collaboration_id=collaboration.id,
        old_rate=None,
        new_rate=payload.initial_rate,
        status=RateProposalStatus.PROPOSED,
        proposed_by_company_id=company_id,
        note=payload.note,
    )
    session.add(proposal)

    requester = await company_repository.get_by_id(session, company_id)
    await notification_service.notify(
        session,
        target.id,
        NotificationType.COLLABORATION_REQUEST,
        f"Nouvelle demande de collaboration de {requester.name} ({requester.registration_code}).",
        link_type="collaboration",
        link_id=collaboration.id,
    )

    await session.commit()
    return collaboration, proposal


async def accept_collaboration(
    session: AsyncSession, company_id: uuid.UUID, acted_by_user_id: uuid.UUID, collaboration_id: uuid.UUID
) -> tuple[Collaboration, CollaborationRateHistory | None]:
    collaboration = await _get_owned_collaboration(session, company_id, collaboration_id)

    if collaboration.target_company_id != company_id:
        raise PermissionDeniedError("Seule l'entreprise sollicitée peut accepter la collaboration.")
    if collaboration.status != CollaborationStatus.PENDING:
        raise ConflictError("Cette collaboration n'est plus en attente.")

    proposal = await collaboration_repository.get_pending_proposal(session, collaboration_id)
    if proposal is not None:
        proposal.status = RateProposalStatus.ACCEPTED
        proposal.decided_by_company_id = company_id
        proposal.decided_at = datetime.now(timezone.utc)
        collaboration.current_rate_id = proposal.id

    collaboration.status = CollaborationStatus.ACCEPTED
    await audit_service.log_action(
        session, company_id, acted_by_user_id, "collaboration.accept", "collaboration", collaboration.id
    )
    await notification_service.notify(
        session,
        collaboration.initiator_company_id,
        NotificationType.COLLABORATION_ACCEPTED,
        "Votre demande de collaboration a été acceptée.",
        link_type="collaboration",
        link_id=collaboration.id,
    )
    await session.commit()
    return collaboration, proposal


async def reject_collaboration(
    session: AsyncSession,
    company_id: uuid.UUID,
    acted_by_user_id: uuid.UUID,
    collaboration_id: uuid.UUID,
    reason: str | None,
) -> Collaboration:
    collaboration = await _get_owned_collaboration(session, company_id, collaboration_id)

    if collaboration.target_company_id != company_id:
        raise PermissionDeniedError("Seule l'entreprise sollicitée peut rejeter la collaboration.")
    if collaboration.status != CollaborationStatus.PENDING:
        raise ConflictError("Cette collaboration n'est plus en attente.")

    proposal = await collaboration_repository.get_pending_proposal(session, collaboration_id)
    if proposal is not None:
        proposal.status = RateProposalStatus.REJECTED
        proposal.decided_by_company_id = company_id
        proposal.decided_at = datetime.now(timezone.utc)
        if reason:
            proposal.note = reason

    collaboration.status = CollaborationStatus.REJECTED
    await audit_service.log_action(
        session, company_id, acted_by_user_id, "collaboration.reject", "collaboration", collaboration.id,
        note=reason,
    )
    await notification_service.notify(
        session,
        collaboration.initiator_company_id,
        NotificationType.COLLABORATION_REJECTED,
        "Votre demande de collaboration a été rejetée.",
        link_type="collaboration",
        link_id=collaboration.id,
    )
    await session.commit()
    return collaboration


async def propose_rate_change(
    session: AsyncSession,
    company_id: uuid.UUID,
    acted_by_user_id: uuid.UUID,
    collaboration_id: uuid.UUID,
    new_rate: Decimal,
    note: str | None,
) -> CollaborationRateHistory:
    collaboration = await _get_owned_collaboration(session, company_id, collaboration_id)

    if collaboration.status != CollaborationStatus.ACCEPTED:
        raise ConflictError("Seule une collaboration active peut voir son taux modifié.")
    if await collaboration_repository.get_pending_proposal(session, collaboration_id) is not None:
        raise ConflictError("Une proposition de taux est déjà en attente pour cette collaboration.")

    current = (
        await collaboration_repository.get_rate_by_id(session, collaboration.current_rate_id)
        if collaboration.current_rate_id
        else None
    )
    proposal = CollaborationRateHistory(
        collaboration_id=collaboration_id,
        old_rate=current.new_rate if current else None,
        new_rate=new_rate,
        status=RateProposalStatus.PROPOSED,
        proposed_by_company_id=company_id,
        note=note,
    )
    session.add(proposal)
    await session.flush()
    await audit_service.log_action(
        session, company_id, acted_by_user_id, "collaboration.rate_propose", "collaboration_rate_history",
        proposal.id, note=f"new_rate={new_rate}",
    )
    other_party_id = (
        collaboration.target_company_id
        if company_id == collaboration.initiator_company_id
        else collaboration.initiator_company_id
    )
    await notification_service.notify(
        session,
        other_party_id,
        NotificationType.RATE_PROPOSED,
        f"Nouvelle proposition de taux collaboratif ({new_rate}) à valider.",
        link_type="collaboration",
        link_id=collaboration.id,
    )
    await session.commit()
    return proposal


async def _get_owned_proposal(
    session: AsyncSession, company_id: uuid.UUID, collaboration_id: uuid.UUID, proposal_id: uuid.UUID
) -> tuple[Collaboration, CollaborationRateHistory]:
    collaboration = await _get_owned_collaboration(session, company_id, collaboration_id)
    proposal = await collaboration_repository.get_rate_proposal_by_id(
        session, collaboration_id, proposal_id
    )
    if proposal is None:
        raise NotFoundError("Proposition de taux introuvable.")
    return collaboration, proposal


async def accept_rate_proposal(
    session: AsyncSession,
    company_id: uuid.UUID,
    acted_by_user_id: uuid.UUID,
    collaboration_id: uuid.UUID,
    proposal_id: uuid.UUID,
) -> CollaborationRateHistory:
    collaboration, proposal = await _get_owned_proposal(session, company_id, collaboration_id, proposal_id)

    if proposal.status != RateProposalStatus.PROPOSED:
        raise ConflictError("Cette proposition n'est plus en attente.")
    if proposal.proposed_by_company_id == company_id:
        raise PermissionDeniedError("Le proposant ne peut pas accepter sa propre proposition.")

    proposal.status = RateProposalStatus.ACCEPTED
    proposal.decided_by_company_id = company_id
    proposal.decided_at = datetime.now(timezone.utc)
    collaboration.current_rate_id = proposal.id
    await audit_service.log_action(
        session, company_id, acted_by_user_id, "collaboration.rate_accept", "collaboration_rate_history",
        proposal.id, note=f"new_rate={proposal.new_rate}",
    )
    await session.commit()
    return proposal


async def reject_rate_proposal(
    session: AsyncSession,
    company_id: uuid.UUID,
    acted_by_user_id: uuid.UUID,
    collaboration_id: uuid.UUID,
    proposal_id: uuid.UUID,
    reason: str | None,
) -> CollaborationRateHistory:
    _, proposal = await _get_owned_proposal(session, company_id, collaboration_id, proposal_id)

    if proposal.status != RateProposalStatus.PROPOSED:
        raise ConflictError("Cette proposition n'est plus en attente.")
    if proposal.proposed_by_company_id == company_id:
        raise PermissionDeniedError("Le proposant ne peut pas rejeter sa propre proposition.")

    proposal.status = RateProposalStatus.REJECTED
    proposal.decided_by_company_id = company_id
    proposal.decided_at = datetime.now(timezone.utc)
    if reason:
        proposal.note = reason
    await audit_service.log_action(
        session, company_id, acted_by_user_id, "collaboration.rate_reject", "collaboration_rate_history",
        proposal.id, note=reason,
    )
    await session.commit()
    return proposal


async def _current_rate_of(
    session: AsyncSession, collaboration: Collaboration
) -> CollaborationRateHistory | None:
    if collaboration.current_rate_id is None:
        return None
    return await collaboration_repository.get_rate_by_id(session, collaboration.current_rate_id)


async def get_collaboration(
    session: AsyncSession, company_id: uuid.UUID, collaboration_id: uuid.UUID
) -> tuple[Collaboration, CollaborationRateHistory | None]:
    collaboration = await _get_owned_collaboration(session, company_id, collaboration_id)
    return collaboration, await _current_rate_of(session, collaboration)


async def list_collaborations(
    session: AsyncSession, company_id: uuid.UUID
) -> list[tuple[Collaboration, CollaborationRateHistory | None]]:
    collaborations = await collaboration_repository.list_for_company(session, company_id)
    return [(collaboration, await _current_rate_of(session, collaboration)) for collaboration in collaborations]


async def list_collaborations_page(
    session: AsyncSession, company_id: uuid.UUID, params: PageParams
) -> tuple[list[tuple[Collaboration, CollaborationRateHistory | None]], int]:
    collaborations, total = await collaboration_repository.list_for_company_page(
        session, company_id, params.page, params.page_size, params.search, params.sort_by, params.sort_dir
    )
    results = [(collaboration, await _current_rate_of(session, collaboration)) for collaboration in collaborations]
    return results, total


async def get_rate_history(
    session: AsyncSession, company_id: uuid.UUID, collaboration_id: uuid.UUID
) -> list[CollaborationRateHistory]:
    await _get_owned_collaboration(session, company_id, collaboration_id)
    return await collaboration_repository.list_rate_history(session, collaboration_id)


async def get_balance(session: AsyncSession, company_id: uuid.UUID, collaboration_id: uuid.UUID) -> Decimal:
    await _get_owned_collaboration(session, company_id, collaboration_id)
    return await collaborator_balance_repository.get_balance_for_company(
        session, collaboration_id, company_id
    )
