import uuid
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models.collaboration import Collaboration, CollaborationStatus
from app.models.entry_allocation import EntryAllocation, EntryAllocationTargetType
from app.models.notification import NotificationType
from app.models.payment import Payment, PaymentStatus, PaymentStatusHistory
from app.models.proof import ProofStatus
from app.models.wallet_movement import MovementDirection
from app.repositories import (
    collaboration_repository,
    collaborator_balance_repository,
    entry_repository,
    payment_repository,
    proof_repository,
    wallet_repository,
)
from app.schemas.pagination import PageParams
from app.schemas.payment import PaymentCreateRequest
from app.services import audit_service, client_service, entry_service, notification_service, wallet_service
from app.utils.reference import daily_sequence_prefix, format_daily_reference

REFERENCE_MAX_RETRIES = 5
REFERENCE_PREFIX = "PA"
_CENTS = Decimal("0.01")


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(_CENTS, rounding=ROUND_HALF_UP)


async def _generate_unique_reference(session: AsyncSession, company_id: uuid.UUID) -> str:
    today = date.today()
    prefix = daily_sequence_prefix(REFERENCE_PREFIX, today)
    already_issued = await payment_repository.count_by_company_and_reference_prefix(session, company_id, prefix)
    for attempt in range(REFERENCE_MAX_RETRIES):
        candidate = format_daily_reference(REFERENCE_PREFIX, today, already_issued + 1 + attempt)
        if await payment_repository.get_by_company_and_reference(session, company_id, candidate) is None:
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
        raise ConflictError("Seule une collaboration acceptée permet de créer un paiement.")
    return collaboration


async def _get_payment_for_party(
    session: AsyncSession, company_id: uuid.UUID, payment_id: uuid.UUID, for_update: bool = False
) -> tuple[Payment, Collaboration]:
    if for_update:
        payment = await payment_repository.lock_by_id(session, payment_id)
    else:
        payment = await payment_repository.get_by_id(session, payment_id)
    if payment is None:
        raise NotFoundError("Paiement introuvable.")
    collaboration = await collaboration_repository.get_by_id(session, payment.collaboration_id)
    if collaboration is None or company_id not in (
        collaboration.initiator_company_id,
        collaboration.target_company_id,
    ):
        raise NotFoundError("Paiement introuvable.")
    return payment, collaboration


async def create_payment(
    session: AsyncSession, company_id: uuid.UUID, created_by_id: uuid.UUID, payload: PaymentCreateRequest
) -> Payment:
    collaboration = await _get_collaboration_for_party(session, company_id, payload.collaboration_id)

    if collaboration.current_rate_id is None:
        raise ConflictError("Aucun taux collaboratif actif pour cette collaboration.")
    collaborative_rate = await collaboration_repository.get_rate_by_id(
        session, collaboration.current_rate_id
    )

    # Le sens du mouvement de solde est figé ici selon le solde net du créateur au moment de la
    # création (cf. approve_payment) : s'il est déjà débiteur net, ce paiement règle sa dette
    # (mouvement inversé par rapport à un Transfer) ; sinon c'est une nouvelle avance (même sens
    # qu'un Transfer). Ça permet au débiteur ET au créditeur de créer un paiement indifféremment,
    # la dette se réglant correctement dans les deux cas.
    current_balance = await collaborator_balance_repository.get_balance_for_company(
        session, collaboration.id, company_id
    )
    settles_debt = current_balance < 0

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
                    "Le montant du paiement dépasse le montant disponible de l'entrée "
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
        # Paiement direct (sans entrée) : aucun montant n'a été reçu via une entrée, donc si un
        # client est renseigné, la totalité du montant est une dette du client envers l'entreprise.
        client_debt_amount = _quantize(payload.amount)

    wallet = None
    if payload.wallet_id is not None:
        wallet = await wallet_repository.lock_by_id(session, payload.wallet_id)
        if wallet is None or wallet.company_id != company_id:
            raise NotFoundError(f"Wallet introuvable : {payload.wallet_id}.")
        if wallet.currency != payload.currency:
            raise ConflictError(
                f"La devise du paiement ({payload.currency}) ne correspond pas à celle du wallet "
                f"{wallet.name} ({wallet.currency})."
            )

    converted_amount = _convert_to_collaboration_currency(
        payload.amount, payload.currency, collaboration.currency, collaborative_rate.new_rate
    )

    client = None
    if client_debt_amount > 0 or (reliquat_amount > 0 and payload.reliquat_action == "client_credit"):
        client_name = payload.client_name or (entry.client_name if entry is not None else None)
        client_phone = payload.client_phone or (entry.client_phone if entry is not None else None)
        client = await client_service.get_or_create_client(session, company_id, client_name, client_phone)

    reference = await _generate_unique_reference(session, company_id)
    payment = Payment(
        company_id=company_id,
        collaboration_id=collaboration.id,
        entry_id=payload.entry_id,
        wallet_id=payload.wallet_id,
        client_id=client.id if client else None,
        client_debt_amount=client_debt_amount if client_debt_amount > 0 else None,
        reference=reference,
        amount=_quantize(payload.amount),
        currency=payload.currency,
        client_name=payload.client_name,
        client_phone=payload.client_phone,
        note=payload.note,
        collaborative_rate_used=collaborative_rate.new_rate,
        converted_amount=converted_amount,
        status=PaymentStatus.PENDING,
        created_by_id=created_by_id,
        settles_debt=settles_debt,
    )
    session.add(payment)
    await session.flush()

    if entry is not None and allocation_amount > 0:
        allocation = EntryAllocation(
            entry_id=entry.id,
            target_type=EntryAllocationTargetType.PAYMENT,
            target_id=payment.id,
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
            source_type="payment",
            source_id=payment.id,
            currency=payload.currency,
            created_by_id=created_by_id,
            note=f"Manquant sur le paiement {reference}",
        )

    if client is not None and reliquat_amount > 0 and payload.reliquat_action == "client_credit":
        await client_service.apply_balance_delta(
            session,
            client,
            -reliquat_amount,
            source_type="payment",
            source_id=payment.id,
            currency=payload.currency,
            created_by_id=created_by_id,
            note=f"Reliquat crédité au client sur le paiement {reference}",
        )

    if reliquat_amount > 0:
        await audit_service.log_action(
            session, company_id, created_by_id, "payment.reliquat", "payment", payment.id,
            note=f"action={payload.reliquat_action} amount={reliquat_amount} {payload.currency}",
        )

    history = PaymentStatusHistory(
        payment_id=payment.id, old_status=None, new_status=PaymentStatus.PENDING, company_id=company_id
    )
    session.add(history)

    await audit_service.log_action(
        session, company_id, created_by_id, "payment.create", "payment", payment.id
    )

    await notification_service.notify(
        session,
        _other_party(collaboration, company_id),
        NotificationType.PAYMENT_PENDING,
        f"Nouveau paiement {reference} à valider.",
        link_type="payment",
        link_id=payment.id,
    )

    await session.commit()
    return payment


async def approve_payment(
    session: AsyncSession,
    company_id: uuid.UUID,
    approved_by_user_id: uuid.UUID,
    payment_id: uuid.UUID,
    proof_id: uuid.UUID | None,
) -> Payment:
    payment, collaboration = await _get_payment_for_party(
        session, company_id, payment_id, for_update=True
    )

    if company_id != _other_party(collaboration, payment.company_id):
        raise PermissionDeniedError("Seul le collaborateur concerné peut approuver ce paiement.")
    if payment.status != PaymentStatus.PENDING:
        raise ConflictError("Ce paiement n'est plus en attente.")

    # Sens figé à la création (payment.settles_debt) : si le créateur était débiteur net, ce
    # paiement règle sa dette, donc le mouvement l'inverse (créateur=créditeur du mouvement) ;
    # sinon c'est une nouvelle avance, même sens qu'un Transfer (créateur=débiteur).
    if payment.settles_debt:
        debtor_company_id, creditor_company_id = company_id, payment.company_id
    else:
        debtor_company_id, creditor_company_id = payment.company_id, company_id

    await collaborator_balance_repository.create(
        session,
        collaboration_id=collaboration.id,
        source_type="payment",
        source_id=payment.id,
        currency=collaboration.currency,
        amount=payment.converted_amount,
        debtor_company_id=debtor_company_id,
        creditor_company_id=creditor_company_id,
    )

    if payment.wallet_id is not None:
        wallet = await wallet_repository.lock_by_id(session, payment.wallet_id)
        if wallet is None:
            raise NotFoundError(f"Wallet introuvable : {payment.wallet_id}.")
        await wallet_service.apply_movement(
            session,
            wallet,
            MovementDirection.OUT,
            payment.amount,
            source_type="payment",
            source_id=payment.id,
            created_by_id=approved_by_user_id,
            note=f"Paiement collaborateur {payment.reference}",
        )

    if proof_id is not None:
        payment.proof_id = proof_id
    old_status = payment.status
    payment.status = PaymentStatus.APPROVED
    payment.approved_at = datetime.now(timezone.utc)

    await proof_repository.set_status_for_payment(session, payment.id, ProofStatus.VALIDATED)

    history = PaymentStatusHistory(
        payment_id=payment.id,
        old_status=old_status,
        new_status=PaymentStatus.APPROVED,
        company_id=company_id,
    )
    session.add(history)
    await audit_service.log_action(
        session, company_id, approved_by_user_id, "payment.approve", "payment", payment.id
    )
    await session.commit()
    return payment


async def reject_payment(
    session: AsyncSession, company_id: uuid.UUID, acted_by_user_id: uuid.UUID, payment_id: uuid.UUID, reason: str
) -> Payment:
    payment, collaboration = await _get_payment_for_party(
        session, company_id, payment_id, for_update=True
    )

    if company_id != _other_party(collaboration, payment.company_id):
        raise PermissionDeniedError("Seul le collaborateur concerné peut rejeter ce paiement.")
    if payment.status != PaymentStatus.PENDING:
        raise ConflictError("Ce paiement n'est plus en attente.")

    old_status = payment.status
    payment.status = PaymentStatus.REJECTED
    payment.rejected_at = datetime.now(timezone.utc)
    payment.rejection_reason = reason

    if payment.entry_id is not None:
        allocation = await entry_repository.get_allocation_by_target(
            session, EntryAllocationTargetType.PAYMENT, payment.id
        )
        if allocation is not None:
            await session.delete(allocation)
            await session.flush()
        entry, lines, allocations = await entry_service.get_entry(
            session, payment.company_id, payment.entry_id
        )
        entry.status = entry_service.recompute_status(lines, allocations)

    if payment.client_id is not None:
        await client_service.reverse_movements_for_source(
            session, payment.company_id, payment.client_id, "payment", payment.id,
            acted_by_user_id, note=f"Annulation de la dette suite au rejet du paiement {payment.reference}",
        )

    await proof_repository.set_status_for_payment(session, payment.id, ProofStatus.REJECTED)

    history = PaymentStatusHistory(
        payment_id=payment.id,
        old_status=old_status,
        new_status=PaymentStatus.REJECTED,
        company_id=company_id,
        reason=reason,
    )
    session.add(history)
    await audit_service.log_action(
        session, company_id, acted_by_user_id, "payment.reject", "payment", payment.id, note=reason
    )
    await notification_service.notify(
        session,
        payment.company_id,
        NotificationType.PAYMENT_REJECTED,
        f"Votre paiement {payment.reference} a été rejeté : {reason}",
        link_type="payment",
        link_id=payment.id,
    )
    await session.commit()
    return payment


async def cancel_payment(
    session: AsyncSession, company_id: uuid.UUID, acted_by_user_id: uuid.UUID, payment_id: uuid.UUID
) -> Payment:
    payment, collaboration = await _get_payment_for_party(session, company_id, payment_id, for_update=True)

    if payment.company_id != company_id:
        raise PermissionDeniedError("Seule l'entreprise à l'origine du paiement peut l'annuler.")
    if payment.status != PaymentStatus.PENDING:
        raise ConflictError("Ce paiement n'est plus en attente.")

    old_status = payment.status
    payment.status = PaymentStatus.CANCELLED

    if payment.entry_id is not None:
        allocation = await entry_repository.get_allocation_by_target(
            session, EntryAllocationTargetType.PAYMENT, payment.id
        )
        if allocation is not None:
            await session.delete(allocation)
            await session.flush()
        entry, lines, allocations = await entry_service.get_entry(session, payment.company_id, payment.entry_id)
        entry.status = entry_service.recompute_status(lines, allocations)

    if payment.client_id is not None:
        await client_service.reverse_movements_for_source(
            session, payment.company_id, payment.client_id, "payment", payment.id,
            acted_by_user_id, note=f"Annulation de la dette suite à l'annulation du paiement {payment.reference}",
        )

    await proof_repository.set_status_for_payment(session, payment.id, ProofStatus.REJECTED)

    history = PaymentStatusHistory(
        payment_id=payment.id,
        old_status=old_status,
        new_status=PaymentStatus.CANCELLED,
        company_id=company_id,
    )
    session.add(history)
    await audit_service.log_action(
        session, company_id, acted_by_user_id, "payment.cancel", "payment", payment.id
    )
    await notification_service.notify(
        session,
        _other_party(collaboration, company_id),
        NotificationType.PAYMENT_CANCELLED,
        f"Le paiement {payment.reference} a été annulé par son initiateur.",
        link_type="payment",
        link_id=payment.id,
    )
    await session.commit()
    return payment


async def get_payment(session: AsyncSession, company_id: uuid.UUID, payment_id: uuid.UUID) -> Payment:
    payment, _collaboration = await _get_payment_for_party(session, company_id, payment_id)
    return payment


async def list_payments(session: AsyncSession, company_id: uuid.UUID) -> list[Payment]:
    return await payment_repository.list_for_company(session, company_id)


async def list_payments_page(
    session: AsyncSession, company_id: uuid.UUID, params: PageParams
) -> tuple[list[Payment], int]:
    return await payment_repository.list_for_company_page(
        session, company_id, params.page, params.page_size, params.search, params.sort_by, params.sort_dir
    )


async def get_status_history(
    session: AsyncSession, company_id: uuid.UUID, payment_id: uuid.UUID
) -> list[PaymentStatusHistory]:
    await get_payment(session, company_id, payment_id)
    return await payment_repository.list_status_history(session, payment_id)
