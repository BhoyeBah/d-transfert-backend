import uuid
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnbalancedOperationError
from app.models.national_operation import NationalOperation, NationalOperationStatus, NationalOperationType
from app.models.national_operation_line import NationalOperationLine
from app.models.wallet_movement import MovementDirection
from app.repositories import national_operation_repository, wallet_repository
from app.schemas.national_operation import NationalOperationCreateRequest
from app.services import audit_service, wallet_service
from app.utils.reference import daily_sequence_prefix, format_daily_reference

REFERENCE_MAX_RETRIES = 5
REFERENCE_PREFIX = "OP"


async def _generate_unique_reference(session: AsyncSession, company_id: uuid.UUID) -> str:
    today = date.today()
    prefix = daily_sequence_prefix(REFERENCE_PREFIX, today)
    already_issued = await national_operation_repository.count_by_company_and_reference_prefix(
        session, company_id, prefix
    )
    for attempt in range(REFERENCE_MAX_RETRIES):
        candidate = format_daily_reference(REFERENCE_PREFIX, today, already_issued + 1 + attempt)
        if await national_operation_repository.get_by_company_and_reference(session, company_id, candidate) is None:
            return candidate
    raise ConflictError("Impossible de générer une référence unique, réessayez.")


async def _load_with_lines(
    session: AsyncSession, company_id: uuid.UUID, operation_id: uuid.UUID
) -> tuple[NationalOperation, list[NationalOperationLine]]:
    operation = await national_operation_repository.get_by_company_and_id(session, company_id, operation_id)
    if operation is None:
        raise NotFoundError("Opération nationale introuvable.")
    lines = await national_operation_repository.get_lines(session, operation.id)
    return operation, lines


async def create_operation(
    session: AsyncSession,
    company_id: uuid.UUID,
    operation_type: NationalOperationType,
    created_by_id: uuid.UUID,
    payload: NationalOperationCreateRequest,
) -> tuple[NationalOperation, list[NationalOperationLine]]:
    wallets = {}
    # Verrouiller les wallets dans un ordre stable (trié par id) plutôt que dans l'ordre
    # d'arrivée des lignes, pour éviter tout interblocage entre deux opérations concurrentes
    # portant sur le même ensemble de wallets dans un ordre différent.
    distinct_wallet_ids = sorted({line.wallet_id for line in payload.lines})
    for wallet_id in distinct_wallet_ids:
        wallet = await wallet_repository.lock_by_id(session, wallet_id)
        if wallet is None or wallet.company_id != company_id:
            raise NotFoundError(f"Wallet introuvable : {wallet_id}.")
        wallets[wallet_id] = wallet

    for line in payload.lines:
        wallet = wallets[line.wallet_id]
        if line.currency != wallet.currency:
            raise UnbalancedOperationError(
                f"La devise de la ligne ({line.currency}) ne correspond pas à celle du wallet "
                f"{wallet.name} ({wallet.currency})."
            )

    reference = await _generate_unique_reference(session, company_id)

    operation = NationalOperation(
        company_id=company_id,
        reference=reference,
        type=operation_type,
        status=NationalOperationStatus.VALIDATED,
        client_name=payload.client_name,
        client_phone=payload.client_phone,
        note=payload.note,
        exchange_rate=payload.exchange_rate,
        proof_id=payload.proof_id,
        created_by_id=created_by_id,
        validated_at=datetime.now(timezone.utc),
    )
    session.add(operation)
    await session.flush()

    lines: list[NationalOperationLine] = []
    for line in payload.lines:
        wallet = wallets[line.wallet_id]
        direction = MovementDirection.IN if line.amount_in > 0 else MovementDirection.OUT
        amount = line.amount_in if line.amount_in > 0 else line.amount_out

        movement = await wallet_service.apply_movement(
            session,
            wallet,
            direction,
            amount,
            source_type="national_operation",
            source_id=operation.id,
            created_by_id=created_by_id,
            note=line.note,
        )

        line_row = NationalOperationLine(
            national_operation_id=operation.id,
            wallet_id=wallet.id,
            amount_in=line.amount_in,
            amount_out=line.amount_out,
            currency=line.currency,
            balance_before=movement.balance_before,
            balance_after=movement.balance_after,
            note=line.note,
        )
        session.add(line_row)
        lines.append(line_row)

    await audit_service.log_action(
        session, company_id, created_by_id, "national_operation.create", "national_operation", operation.id,
        note=f"type={operation_type.value}",
    )
    await session.commit()
    return operation, lines


async def get_operation(
    session: AsyncSession, company_id: uuid.UUID, operation_id: uuid.UUID
) -> tuple[NationalOperation, list[NationalOperationLine]]:
    return await _load_with_lines(session, company_id, operation_id)


async def list_operations(
    session: AsyncSession, company_id: uuid.UUID
) -> list[tuple[NationalOperation, list[NationalOperationLine]]]:
    operations = await national_operation_repository.list_by_company(session, company_id)
    return [(op, await national_operation_repository.get_lines(session, op.id)) for op in operations]


async def cancel_operation(
    session: AsyncSession, company_id: uuid.UUID, operation_id: uuid.UUID, created_by_id: uuid.UUID
) -> tuple[NationalOperation, list[NationalOperationLine]]:
    operation, original_lines = await _load_with_lines(session, company_id, operation_id)

    if operation.status != NationalOperationStatus.VALIDATED:
        raise ConflictError("Seule une opération validée peut être annulée.")

    wallets = {}
    for line in original_lines:
        if line.wallet_id not in wallets:
            wallet = await wallet_repository.lock_by_id(session, line.wallet_id)
            if wallet is None:
                raise NotFoundError(f"Wallet introuvable : {line.wallet_id}.")
            wallets[line.wallet_id] = wallet

    reference = await _generate_unique_reference(session, company_id)
    reversal = NationalOperation(
        company_id=company_id,
        reference=reference,
        type=operation.type,
        status=NationalOperationStatus.VALIDATED,
        client_name=operation.client_name,
        client_phone=operation.client_phone,
        note=f"Annulation de {operation.reference}",
        exchange_rate=operation.exchange_rate,
        created_by_id=created_by_id,
        validated_at=datetime.now(timezone.utc),
        reversal_of_id=operation.id,
    )
    session.add(reversal)
    await session.flush()

    reversal_lines: list[NationalOperationLine] = []
    for line in original_lines:
        wallet = wallets[line.wallet_id]
        mirrored_amount_in = line.amount_out
        mirrored_amount_out = line.amount_in
        direction = MovementDirection.IN if mirrored_amount_in > 0 else MovementDirection.OUT
        amount = mirrored_amount_in if mirrored_amount_in > 0 else mirrored_amount_out

        movement = await wallet_service.apply_movement(
            session,
            wallet,
            direction,
            amount,
            source_type="national_operation",
            source_id=reversal.id,
            created_by_id=created_by_id,
            note=f"Annulation de {operation.reference}",
        )

        reversal_line = NationalOperationLine(
            national_operation_id=reversal.id,
            wallet_id=wallet.id,
            amount_in=mirrored_amount_in,
            amount_out=mirrored_amount_out,
            currency=line.currency,
            balance_before=movement.balance_before,
            balance_after=movement.balance_after,
            note=f"Annulation de {operation.reference}",
        )
        session.add(reversal_line)
        reversal_lines.append(reversal_line)

    operation.status = NationalOperationStatus.CANCELLED
    operation.cancelled_at = datetime.now(timezone.utc)

    await audit_service.log_action(
        session, company_id, created_by_id, "national_operation.cancel", "national_operation", operation.id,
        note=f"reversal_id={reversal.id}",
    )
    await session.commit()
    return reversal, reversal_lines
