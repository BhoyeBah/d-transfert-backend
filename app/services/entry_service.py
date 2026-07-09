import uuid
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnbalancedOperationError
from app.models.entry import Entry, EntryStatus
from app.models.entry_allocation import EntryAllocation
from app.models.entry_line import EntryLine
from app.models.wallet_movement import MovementDirection
from app.repositories import entry_repository, wallet_repository
from app.schemas.entry import EntryCreateRequest, EntryMergeRequest
from app.schemas.pagination import PageParams
from app.services import audit_service, wallet_service
from app.utils.reference import daily_sequence_prefix, format_daily_reference

REFERENCE_MAX_RETRIES = 5
REFERENCE_PREFIX = "EN"

MERGEABLE_STATUSES = (EntryStatus.UNALLOCATED, EntryStatus.PARTIALLY_ALLOCATED)

_CENTS = Decimal("0.01")


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(_CENTS, rounding=ROUND_HALF_UP)


async def _generate_unique_reference(session: AsyncSession, company_id: uuid.UUID) -> str:
    today = date.today()
    prefix = daily_sequence_prefix(REFERENCE_PREFIX, today)
    already_issued = await entry_repository.count_by_company_and_reference_prefix(session, company_id, prefix)
    for attempt in range(REFERENCE_MAX_RETRIES):
        candidate = format_daily_reference(REFERENCE_PREFIX, today, already_issued + 1 + attempt)
        if await entry_repository.get_by_company_and_reference(session, company_id, candidate) is None:
            return candidate
    raise ConflictError("Impossible de générer une référence unique, réessayez.")


def available_by_currency(
    lines: list[EntryLine], allocations: list[EntryAllocation]
) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for line in lines:
        totals[line.currency] += _quantize(line.amount)
    for allocation in allocations:
        totals[allocation.currency] -= _quantize(allocation.amount_allocated)
    return dict(totals)


def recompute_status(lines: list[EntryLine], allocations: list[EntryAllocation]) -> EntryStatus:
    if not allocations:
        return EntryStatus.UNALLOCATED
    remaining = available_by_currency(lines, allocations)
    if all(amount <= 0 for amount in remaining.values()):
        return EntryStatus.CONSUMED
    return EntryStatus.PARTIALLY_ALLOCATED


async def _load_full(
    session: AsyncSession, company_id: uuid.UUID, entry_id: uuid.UUID
) -> tuple[Entry, list[EntryLine], list[EntryAllocation]]:
    entry = await entry_repository.get_by_company_and_id(session, company_id, entry_id)
    if entry is None:
        raise NotFoundError("Entrée introuvable.")
    lines = await entry_repository.get_lines(session, entry.id)
    allocations = await entry_repository.get_allocations(session, entry.id)
    return entry, lines, allocations


async def create_entry(
    session: AsyncSession, company_id: uuid.UUID, created_by_id: uuid.UUID, payload: EntryCreateRequest
) -> tuple[Entry, list[EntryLine]]:
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
    entry = Entry(
        company_id=company_id,
        reference=reference,
        client_name=payload.client_name,
        client_phone=payload.client_phone,
        note=payload.note,
        status=EntryStatus.UNALLOCATED,
        created_by_id=created_by_id,
    )
    session.add(entry)
    await session.flush()

    lines: list[EntryLine] = []
    for line in payload.lines:
        wallet = wallets[line.wallet_id]
        await wallet_service.apply_movement(
            session,
            wallet,
            MovementDirection.IN,
            line.amount,
            source_type="entry",
            source_id=entry.id,
            created_by_id=created_by_id,
            note=line.note,
        )
        line_row = EntryLine(
            entry_id=entry.id,
            wallet_id=wallet.id,
            amount=_quantize(line.amount),
            currency=line.currency,
            note=line.note,
        )
        session.add(line_row)
        lines.append(line_row)

    await audit_service.log_action(session, company_id, created_by_id, "entry.create", "entry", entry.id)
    await session.commit()
    return entry, lines


async def get_entry(
    session: AsyncSession, company_id: uuid.UUID, entry_id: uuid.UUID
) -> tuple[Entry, list[EntryLine], list[EntryAllocation]]:
    return await _load_full(session, company_id, entry_id)


async def list_entries(
    session: AsyncSession, company_id: uuid.UUID
) -> list[tuple[Entry, list[EntryLine], list[EntryAllocation]]]:
    entries = await entry_repository.list_by_company(session, company_id)
    results = []
    for entry in entries:
        lines = await entry_repository.get_lines(session, entry.id)
        allocations = await entry_repository.get_allocations(session, entry.id)
        results.append((entry, lines, allocations))
    return results


async def list_entries_page(
    session: AsyncSession, company_id: uuid.UUID, params: PageParams
) -> tuple[list[tuple[Entry, list[EntryLine], list[EntryAllocation]]], int]:
    entries, total = await entry_repository.list_by_company_page(
        session, company_id, params.page, params.page_size, params.search, params.sort_by, params.sort_dir
    )
    results = []
    for entry in entries:
        lines = await entry_repository.get_lines(session, entry.id)
        allocations = await entry_repository.get_allocations(session, entry.id)
        results.append((entry, lines, allocations))
    return results, total


async def merge_entries(
    session: AsyncSession, company_id: uuid.UUID, created_by_id: uuid.UUID, payload: EntryMergeRequest
) -> tuple[Entry, list[EntryLine]]:
    if len(set(payload.entry_ids)) != len(payload.entry_ids):
        raise ConflictError("La liste des entrées à fusionner contient des doublons.")

    source_entries: list[Entry] = []
    source_lines_by_entry: dict[uuid.UUID, list[EntryLine]] = {}
    for entry_id in payload.entry_ids:
        entry, lines, allocations = await _load_full(session, company_id, entry_id)
        if entry.status not in MERGEABLE_STATUSES:
            raise ConflictError(
                f"L'entrée {entry.reference} ne peut pas être fusionnée (statut : {entry.status})."
            )
        if entry.merged_into_id is not None:
            raise ConflictError(f"L'entrée {entry.reference} a déjà été fusionnée.")
        source_entries.append(entry)
        # Seul le reliquat réellement disponible (montant des lignes moins les affectations déjà
        # consommées) doit être reporté dans l'entrée fusionnée, sinon un montant déjà affecté à un
        # envoi/paiement serait dupliqué (double dépense) lors de la fusion d'une entrée partiellement
        # affectée. On distribue ce reliquat, devise par devise, sur les lignes d'origine (dans l'ordre)
        # pour conserver une trace plausible des wallets d'origine.
        remaining_by_currency = available_by_currency(lines, allocations)
        remaining_lines: list[EntryLine] = []
        for line in lines:
            remaining_for_currency = remaining_by_currency.get(line.currency, Decimal("0"))
            if remaining_for_currency <= 0:
                continue
            take = min(_quantize(line.amount), remaining_for_currency)
            if take <= 0:
                continue
            remaining_lines.append(
                EntryLine(wallet_id=line.wallet_id, amount=take, currency=line.currency)
            )
            remaining_by_currency[line.currency] = remaining_for_currency - take
        source_lines_by_entry[entry.id] = remaining_lines

    aggregated: dict[tuple[uuid.UUID, str], Decimal] = defaultdict(Decimal)
    for lines in source_lines_by_entry.values():
        for line in lines:
            aggregated[(line.wallet_id, line.currency)] += _quantize(line.amount)

    reference = await _generate_unique_reference(session, company_id)
    merged_entry = Entry(
        company_id=company_id,
        reference=reference,
        client_name=source_entries[0].client_name,
        client_phone=source_entries[0].client_phone,
        note=payload.note,
        status=EntryStatus.UNALLOCATED,
        created_by_id=created_by_id,
    )
    session.add(merged_entry)
    await session.flush()

    new_lines: list[EntryLine] = []
    for (wallet_id, currency), amount in aggregated.items():
        line_row = EntryLine(
            entry_id=merged_entry.id, wallet_id=wallet_id, amount=amount, currency=currency
        )
        session.add(line_row)
        new_lines.append(line_row)

    for entry in source_entries:
        entry.merged_into_id = merged_entry.id

    await session.commit()
    return merged_entry, new_lines


async def cancel_entry(
    session: AsyncSession, company_id: uuid.UUID, created_by_id: uuid.UUID, entry_id: uuid.UUID
) -> tuple[Entry, list[EntryLine]]:
    entry, lines, allocations = await _load_full(session, company_id, entry_id)

    if entry.merged_into_id is not None:
        raise ConflictError(
            f"L'entrée {entry.reference} a été fusionnée dans une autre entrée et ne peut plus être annulée directement."
        )
    if allocations:
        raise ConflictError(
            f"L'entrée {entry.reference} ne peut pas être annulée : elle est déjà affectée à un envoi "
            "ou un paiement (même en attente). Rejetez ou annulez d'abord les opérations qui l'utilisent."
        )
    if entry.status not in MERGEABLE_STATUSES:
        raise ConflictError(f"L'entrée {entry.reference} ne peut pas être annulée (statut : {entry.status}).")

    for line in lines:
        wallet = await wallet_repository.lock_by_id(session, line.wallet_id)
        if wallet is None:
            raise NotFoundError(f"Wallet introuvable : {line.wallet_id}.")
        await wallet_service.apply_movement(
            session,
            wallet,
            MovementDirection.OUT,
            line.amount,
            source_type="entry_cancellation",
            source_id=entry.id,
            created_by_id=created_by_id,
            note=f"Annulation de l'entrée {entry.reference}",
        )

    entry.status = EntryStatus.CANCELLED
    await session.commit()
    return entry, lines
