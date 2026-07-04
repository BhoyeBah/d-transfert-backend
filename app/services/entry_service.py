import uuid
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnbalancedOperationError
from app.models.entry import Entry, EntryStatus
from app.models.entry_allocation import EntryAllocation
from app.models.entry_line import EntryLine
from app.models.wallet_movement import MovementDirection
from app.repositories import entry_repository, wallet_repository
from app.schemas.entry import EntryCreateRequest, EntryMergeRequest
from app.services import wallet_service
from app.utils.reference import generate_entry_reference

REFERENCE_MAX_RETRIES = 5

MERGEABLE_STATUSES = (EntryStatus.UNALLOCATED, EntryStatus.PARTIALLY_ALLOCATED)

_CENTS = Decimal("0.01")


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(_CENTS, rounding=ROUND_HALF_UP)


async def _generate_unique_reference(session: AsyncSession) -> str:
    for _ in range(REFERENCE_MAX_RETRIES):
        candidate = generate_entry_reference()
        if await entry_repository.get_by_reference(session, candidate) is None:
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
    for line in payload.lines:
        if line.wallet_id not in wallets:
            wallet = await wallet_repository.lock_by_id(session, line.wallet_id)
            if wallet is None or wallet.company_id != company_id:
                raise NotFoundError(f"Wallet introuvable : {line.wallet_id}.")
            wallets[line.wallet_id] = wallet

        wallet = wallets[line.wallet_id]
        if line.currency != wallet.currency:
            raise UnbalancedOperationError(
                f"La devise de la ligne ({line.currency}) ne correspond pas à celle du wallet "
                f"{wallet.name} ({wallet.currency})."
            )

    reference = await _generate_unique_reference(session)
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


async def merge_entries(
    session: AsyncSession, company_id: uuid.UUID, created_by_id: uuid.UUID, payload: EntryMergeRequest
) -> tuple[Entry, list[EntryLine]]:
    if len(set(payload.entry_ids)) != len(payload.entry_ids):
        raise ConflictError("La liste des entrées à fusionner contient des doublons.")

    source_entries: list[Entry] = []
    source_lines_by_entry: dict[uuid.UUID, list[EntryLine]] = {}
    for entry_id in payload.entry_ids:
        entry, lines, _allocations = await _load_full(session, company_id, entry_id)
        if entry.status not in MERGEABLE_STATUSES:
            raise ConflictError(
                f"L'entrée {entry.reference} ne peut pas être fusionnée (statut : {entry.status})."
            )
        if entry.merged_into_id is not None:
            raise ConflictError(f"L'entrée {entry.reference} a déjà été fusionnée.")
        source_entries.append(entry)
        source_lines_by_entry[entry.id] = lines

    aggregated: dict[tuple[uuid.UUID, str], Decimal] = defaultdict(Decimal)
    for lines in source_lines_by_entry.values():
        for line in lines:
            aggregated[(line.wallet_id, line.currency)] += _quantize(line.amount)

    reference = await _generate_unique_reference(session)
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
    entry, lines, _allocations = await _load_full(session, company_id, entry_id)

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
