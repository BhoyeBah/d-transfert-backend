import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.client import Client
from app.models.client_balance_movement import ClientBalanceMovement
from app.repositories import client_repository
from app.schemas.pagination import PageParams

_CENTS = Decimal("0.01")


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(_CENTS, rounding=ROUND_HALF_UP)


async def get_or_create_client(
    session: AsyncSession, company_id: uuid.UUID, name: str, phone: str, note: str | None = None
) -> Client:
    existing = await client_repository.get_by_company_and_phone(session, company_id, phone)
    if existing is not None:
        return existing

    client = Client(company_id=company_id, name=name, phone=phone, note=note, balance=Decimal("0.00"))
    session.add(client)
    await session.flush()
    return client


async def apply_balance_delta(
    session: AsyncSession,
    client: Client,
    delta: Decimal,
    source_type: str,
    source_id: uuid.UUID,
    created_by_id: uuid.UUID,
    note: str | None = None,
) -> ClientBalanceMovement:
    balance_before = client.balance
    client.balance = _quantize(client.balance + delta)

    movement = ClientBalanceMovement(
        client_id=client.id,
        source_type=source_type,
        source_id=source_id,
        delta=_quantize(delta),
        balance_before=balance_before,
        balance_after=client.balance,
        created_by_id=created_by_id,
        note=note,
    )
    session.add(movement)
    await session.flush()
    return movement


async def reverse_movements_for_source(
    session: AsyncSession,
    company_id: uuid.UUID,
    client_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    created_by_id: uuid.UUID,
    note: str | None = None,
) -> ClientBalanceMovement | None:
    """Annule l'effet net déjà appliqué au client pour cette opération source (rejet/annulation),
    sans supprimer l'historique : crée un mouvement inverse compensant exactement le delta net
    déjà enregistré (dette initiale ou crédit de reliquat)."""
    movements = await client_repository.get_by_source(session, client_id, source_type, source_id)
    net = sum((movement.delta for movement in movements), Decimal("0.00"))
    if net == 0:
        return None
    client = await get_client(session, company_id, client_id)
    return await apply_balance_delta(
        session, client, -net, source_type=f"{source_type}_reversal", source_id=source_id,
        created_by_id=created_by_id, note=note,
    )


async def get_client(session: AsyncSession, company_id: uuid.UUID, client_id: uuid.UUID) -> Client:
    client = await client_repository.get_by_company_and_id(session, company_id, client_id)
    if client is None:
        raise NotFoundError("Client introuvable.")
    return client


async def list_clients(session: AsyncSession, company_id: uuid.UUID) -> list[Client]:
    return await client_repository.list_by_company(session, company_id)


async def list_clients_page(
    session: AsyncSession, company_id: uuid.UUID, params: PageParams
) -> tuple[list[Client], int]:
    return await client_repository.list_by_company_page(
        session, company_id, params.page, params.page_size, params.search, params.sort_by, params.sort_dir
    )


async def get_movements(
    session: AsyncSession, company_id: uuid.UUID, client_id: uuid.UUID
) -> list[ClientBalanceMovement]:
    await get_client(session, company_id, client_id)
    return await client_repository.list_movements(session, client_id)


async def create_client(
    session: AsyncSession, company_id: uuid.UUID, name: str, phone: str, note: str | None
) -> Client:
    client = await get_or_create_client(session, company_id, name, phone, note)
    await session.commit()
    return client
