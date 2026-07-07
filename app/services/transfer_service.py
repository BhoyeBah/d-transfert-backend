import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models.collaboration import Collaboration, CollaborationStatus
from app.models.entry_allocation import EntryAllocation, EntryAllocationTargetType
from app.models.notification import NotificationType
from app.models.transfer import Transfer, TransferStatus, TransferStatusHistory
from app.repositories import (
    collaboration_repository,
    collaborator_balance_repository,
    entry_repository,
    private_rate_repository,
    transfer_repository,
)
from app.schemas.transfer import TransferCreateRequest
from app.services import audit_service, client_service, entry_service, notification_service
from app.utils.reference import generate_transfer_reference

REFERENCE_MAX_RETRIES = 5
_CENTS = Decimal("0.01")


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(_CENTS, rounding=ROUND_HALF_UP)


async def _generate_unique_reference(session: AsyncSession) -> str:
    for _ in range(REFERENCE_MAX_RETRIES):
        candidate = generate_transfer_reference()
        if await transfer_repository.get_by_reference(session, candidate) is None:
            return candidate
    raise ConflictError("Impossible de générer une référence unique, réessayez.")


def _convert_to_collaboration_currency(
    amount: Decimal, from_currency: str, collaboration_currency: str, rate: Decimal
) -> Decimal:
    if from_currency == collaboration_currency:
        return _quantize(amount)
    return _quantize(amount * rate)


def _other_party(collaboration: Collaboration, company_id: uuid.UUID) -> uuid.UUID:
    if collaboration.initiator_company_id == company_id:
        return collaboration.target_company_id
    return collaboration.initiator_company_id


async def _get_collaboration_for_party(
    session: AsyncSession, company_id: uuid.UUID, collaboration_id: uuid.UUID
) -> Collaboration:
    collaboration = await collaboration_repository.get_by_id(session, collaboration_id)
    if collaboration is None or company_id not in (
        collaboration.initiator_company_id,
        collaboration.target_company_id,
    ):
        raise NotFoundError("Collaboration introuvable.")
    if collaboration.status != CollaborationStatus.ACCEPTED:
        raise ConflictError("Seule une collaboration acceptée permet de créer un envoi.")
    return collaboration


async def _get_transfer_for_party(
    session: AsyncSession, company_id: uuid.UUID, transfer_id: uuid.UUID, for_update: bool = False
) -> tuple[Transfer, Collaboration]:
    if for_update:
        transfer = await transfer_repository.lock_by_id(session, transfer_id)
    else:
        transfer = await transfer_repository.get_by_id(session, transfer_id)
    if transfer is None:
        raise NotFoundError("Envoi introuvable.")
    collaboration = await collaboration_repository.get_by_id(session, transfer.collaboration_id)
    if collaboration is None or company_id not in (
        collaboration.initiator_company_id,
        collaboration.target_company_id,
    ):
        raise NotFoundError("Envoi introuvable.")
    return transfer, collaboration


async def create_transfer(
    session: AsyncSession, company_id: uuid.UUID, created_by_id: uuid.UUID, payload: TransferCreateRequest
) -> Transfer:
    collaboration = await _get_collaboration_for_party(session, company_id, payload.collaboration_id)

    if collaboration.current_rate_id is None:
        raise ConflictError("Aucun taux collaboratif actif pour cette collaboration.")
    collaborative_rate = await collaboration_repository.get_rate_by_id(
        session, collaboration.current_rate_id
    )

    private_rate_row = await private_rate_repository.get_active_by_scope(
        session, company_id, collaboration.id, None, payload.currency
    )
    if private_rate_row is None:
        private_rate_row = await private_rate_repository.get_active_by_scope(
            session, company_id, None, None, payload.currency
        )
    private_rate_used = private_rate_row.rate if private_rate_row else None

    entry = None
    lines: list = []
    allocations: list = []
    allocation_amount = _quantize(payload.amount)
    client_debt_amount = Decimal("0.00")
    reliquat_amount = Decimal("0.00")
    if payload.entry_id is not None:
        entry, lines, allocations = await entry_service.get_entry(session, company_id, payload.entry_id)
        if entry.merged_into_id is not None:
            raise ConflictError(
                f"L'entrée {entry.reference} a été fusionnée dans une autre entrée et ne peut plus être "
                "utilisée directement."
            )
        if entry.status not in entry_service.MERGEABLE_STATUSES:
            raise ConflictError(
                f"L'entrée {entry.reference} ne peut pas être affectée (statut : {entry.status})."
            )
        available = entry_service.available_by_currency(lines, allocations)
        available_for_currency = available.get(payload.currency, Decimal("0"))
        if payload.amount > available_for_currency:
            client_debt_amount = _quantize(payload.amount - available_for_currency)
            allocation_amount = _quantize(available_for_currency)
            if not (payload.client_name and payload.client_phone) and not (
                entry.client_name and entry.client_phone
            ):
                raise ConflictError(
                    "Le montant de l'envoi dépasse le montant disponible de l'entrée "
                    f"({available_for_currency} {payload.currency} disponible) : un client "
                    "(nom et téléphone) est requis pour enregistrer la dette du manquant."
                )
        elif payload.amount < available_for_currency and payload.reliquat_action != "unallocated":
            # Reliquat : le montant déclaré est inférieur au disponible. Selon le choix de
            # l'utilisateur, ce reliquat est soit conservé comme frais (l'entrée est totalement
            # consommée, sans autre effet), soit crédité au solde du client.
            reliquat_amount = _quantize(available_for_currency - payload.amount)
            allocation_amount = _quantize(available_for_currency)
            if payload.reliquat_action == "client_credit" and not (
                payload.client_name and payload.client_phone
            ) and not (entry.client_name and entry.client_phone):
                raise ConflictError(
                    "Le crédit du reliquat au client nécessite un client (nom et téléphone)."
                )
    elif payload.client_name and payload.client_phone:
        # Envoi direct (solde direct) : aucun montant n'a été reçu via une entrée, donc si un
        # client est renseigné, la totalité du montant est une dette du client envers l'entreprise.
        client_debt_amount = _quantize(payload.amount)

    converted_amount = _convert_to_collaboration_currency(
        payload.amount, payload.currency, collaboration.currency, collaborative_rate.new_rate
    )

    client = None
    if client_debt_amount > 0 or (reliquat_amount > 0 and payload.reliquat_action == "client_credit"):
        client_name = payload.client_name or (entry.client_name if entry is not None else None)
        client_phone = payload.client_phone or (entry.client_phone if entry is not None else None)
        client = await client_service.get_or_create_client(session, company_id, client_name, client_phone)

    reference = await _generate_unique_reference(session)
    transfer = Transfer(
        company_id=company_id,
        collaboration_id=collaboration.id,
        entry_id=payload.entry_id,
        client_id=client.id if client else None,
        client_debt_amount=client_debt_amount if client_debt_amount > 0 else None,
        reference=reference,
        amount=_quantize(payload.amount),
        currency=payload.currency,
        beneficiary_name=payload.beneficiary_name,
        beneficiary_phone=payload.beneficiary_phone,
        send_mode=payload.send_mode,
        note=payload.note,
        private_rate_used=private_rate_used,
        collaborative_rate_used=collaborative_rate.new_rate,
        converted_amount=converted_amount,
        status=TransferStatus.PENDING,
        created_by_id=created_by_id,
    )
    session.add(transfer)
    await session.flush()

    if entry is not None and allocation_amount > 0:
        allocation = EntryAllocation(
            entry_id=entry.id,
            target_type=EntryAllocationTargetType.TRANSFER,
            target_id=transfer.id,
            currency=payload.currency,
            amount_allocated=allocation_amount,
        )
        session.add(allocation)
        await session.flush()
        entry.status = entry_service.recompute_status(lines, [*allocations, allocation])

    if client is not None and client_debt_amount > 0:
        await client_service.apply_balance_delta(
            session,
            client,
            client_debt_amount,
            source_type="transfer",
            source_id=transfer.id,
            created_by_id=created_by_id,
            note=f"Manquant sur l'envoi {reference}",
        )

    if client is not None and reliquat_amount > 0 and payload.reliquat_action == "client_credit":
        await client_service.apply_balance_delta(
            session,
            client,
            -reliquat_amount,
            source_type="transfer",
            source_id=transfer.id,
            created_by_id=created_by_id,
            note=f"Reliquat crédité au client sur l'envoi {reference}",
        )

    if reliquat_amount > 0:
        await audit_service.log_action(
            session, company_id, created_by_id, "transfer.reliquat", "transfer", transfer.id,
            note=f"action={payload.reliquat_action} amount={reliquat_amount} {payload.currency}",
        )

    history = TransferStatusHistory(
        transfer_id=transfer.id, old_status=None, new_status=TransferStatus.PENDING, company_id=company_id
    )
    session.add(history)

    await audit_service.log_action(
        session, company_id, created_by_id, "transfer.create", "transfer", transfer.id
    )

    await notification_service.notify(
        session,
        _other_party(collaboration, company_id),
        NotificationType.TRANSFER_PENDING,
        f"Nouvel envoi {reference} à valider.",
        link_type="transfer",
        link_id=transfer.id,
    )

    await session.commit()
    return transfer


async def approve_transfer(
    session: AsyncSession,
    company_id: uuid.UUID,
    acted_by_user_id: uuid.UUID,
    transfer_id: uuid.UUID,
    proof_id: uuid.UUID | None,
) -> Transfer:
    transfer, collaboration = await _get_transfer_for_party(
        session, company_id, transfer_id, for_update=True
    )

    if company_id != _other_party(collaboration, transfer.company_id):
        raise PermissionDeniedError("Seul le collaborateur sollicité peut approuver cet envoi.")
    if transfer.status != TransferStatus.PENDING:
        raise ConflictError("Cet envoi n'est plus en attente.")

    await collaborator_balance_repository.create(
        session,
        collaboration_id=collaboration.id,
        source_type="transfer",
        source_id=transfer.id,
        currency=collaboration.currency,
        amount=transfer.converted_amount,
        debtor_company_id=transfer.company_id,
        creditor_company_id=company_id,
    )

    if proof_id is not None:
        transfer.proof_id = proof_id
    old_status = transfer.status
    transfer.status = TransferStatus.APPROVED
    transfer.approved_at = datetime.now(timezone.utc)

    history = TransferStatusHistory(
        transfer_id=transfer.id,
        old_status=old_status,
        new_status=TransferStatus.APPROVED,
        company_id=company_id,
    )
    session.add(history)
    await audit_service.log_action(
        session, company_id, acted_by_user_id, "transfer.approve", "transfer", transfer.id
    )
    await session.commit()
    return transfer


async def reject_transfer(
    session: AsyncSession, company_id: uuid.UUID, acted_by_user_id: uuid.UUID, transfer_id: uuid.UUID, reason: str
) -> Transfer:
    transfer, collaboration = await _get_transfer_for_party(
        session, company_id, transfer_id, for_update=True
    )

    if company_id != _other_party(collaboration, transfer.company_id):
        raise PermissionDeniedError("Seul le collaborateur sollicité peut rejeter cet envoi.")
    if transfer.status != TransferStatus.PENDING:
        raise ConflictError("Cet envoi n'est plus en attente.")

    old_status = transfer.status
    transfer.status = TransferStatus.REJECTED
    transfer.rejected_at = datetime.now(timezone.utc)
    transfer.rejection_reason = reason

    if transfer.entry_id is not None:
        allocation = await entry_repository.get_allocation_by_target(
            session, EntryAllocationTargetType.TRANSFER, transfer.id
        )
        if allocation is not None:
            await session.delete(allocation)
            await session.flush()
        entry, lines, allocations = await entry_service.get_entry(
            session, transfer.company_id, transfer.entry_id
        )
        entry.status = entry_service.recompute_status(lines, allocations)

    history = TransferStatusHistory(
        transfer_id=transfer.id,
        old_status=old_status,
        new_status=TransferStatus.REJECTED,
        company_id=company_id,
        reason=reason,
    )
    session.add(history)
    await audit_service.log_action(
        session, company_id, acted_by_user_id, "transfer.reject", "transfer", transfer.id, note=reason
    )
    await notification_service.notify(
        session,
        transfer.company_id,
        NotificationType.TRANSFER_REJECTED,
        f"Votre envoi {transfer.reference} a été rejeté : {reason}",
        link_type="transfer",
        link_id=transfer.id,
    )
    await session.commit()
    return transfer


async def cancel_transfer(
    session: AsyncSession, company_id: uuid.UUID, acted_by_user_id: uuid.UUID, transfer_id: uuid.UUID
) -> Transfer:
    transfer, _collaboration = await _get_transfer_for_party(session, company_id, transfer_id, for_update=True)

    if transfer.company_id != company_id:
        raise PermissionDeniedError("Seule l'entreprise à l'origine de l'envoi peut l'annuler.")
    if transfer.status != TransferStatus.PENDING:
        raise ConflictError("Cet envoi n'est plus en attente.")

    old_status = transfer.status
    transfer.status = TransferStatus.CANCELLED

    if transfer.entry_id is not None:
        allocation = await entry_repository.get_allocation_by_target(
            session, EntryAllocationTargetType.TRANSFER, transfer.id
        )
        if allocation is not None:
            await session.delete(allocation)
            await session.flush()
        entry, lines, allocations = await entry_service.get_entry(session, transfer.company_id, transfer.entry_id)
        entry.status = entry_service.recompute_status(lines, allocations)

    history = TransferStatusHistory(
        transfer_id=transfer.id,
        old_status=old_status,
        new_status=TransferStatus.CANCELLED,
        company_id=company_id,
    )
    session.add(history)
    await audit_service.log_action(
        session, company_id, acted_by_user_id, "transfer.cancel", "transfer", transfer.id
    )
    await session.commit()
    return transfer


async def get_transfer(session: AsyncSession, company_id: uuid.UUID, transfer_id: uuid.UUID) -> Transfer:
    transfer, _collaboration = await _get_transfer_for_party(session, company_id, transfer_id)
    return transfer


async def list_transfers(session: AsyncSession, company_id: uuid.UUID) -> list[Transfer]:
    return await transfer_repository.list_for_company(session, company_id)


async def get_status_history(
    session: AsyncSession, company_id: uuid.UUID, transfer_id: uuid.UUID
) -> list[TransferStatusHistory]:
    await get_transfer(session, company_id, transfer_id)
    return await transfer_repository.list_status_history(session, transfer_id)
