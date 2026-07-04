import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, InsufficientBalanceError, NotFoundError
from app.models.wallet import Wallet, WalletStatus
from app.models.wallet_movement import MovementDirection, WalletMovement
from app.repositories import wallet_movement_repository, wallet_repository
from app.schemas.wallet import WalletCreateRequest, WalletUpdateRequest

_CENTS = Decimal("0.01")


async def apply_movement(
    session: AsyncSession,
    wallet: Wallet,
    direction: MovementDirection,
    amount: Decimal,
    source_type: str,
    source_id: uuid.UUID,
    created_by_id: uuid.UUID,
    note: str | None = None,
) -> WalletMovement:
    if amount <= 0:
        raise ValueError("Le montant d'un mouvement doit être strictement positif.")

    amount = amount.quantize(_CENTS, rounding=ROUND_HALF_UP)

    if wallet.status != WalletStatus.ACTIVE:
        raise ConflictError(f"Le wallet {wallet.name} est inactif et ne peut pas être utilisé.")

    balance_before = wallet.balance
    if direction == MovementDirection.OUT:
        if wallet.balance < amount:
            raise InsufficientBalanceError(
                f"Solde insuffisant dans le wallet {wallet.name}. "
                f"Solde disponible : {balance_before} {wallet.currency}. "
                f"Montant demandé : {amount} {wallet.currency}."
            )
        wallet.balance = (wallet.balance - amount).quantize(_CENTS, rounding=ROUND_HALF_UP)
    else:
        wallet.balance = (wallet.balance + amount).quantize(_CENTS, rounding=ROUND_HALF_UP)

    return await wallet_movement_repository.create(
        session,
        wallet_id=wallet.id,
        direction=direction,
        amount=amount,
        currency=wallet.currency,
        balance_before=balance_before,
        balance_after=wallet.balance,
        source_type=source_type,
        source_id=source_id,
        created_by_id=created_by_id,
        note=note,
    )


async def create_wallet(
    session: AsyncSession, company_id: uuid.UUID, created_by_id: uuid.UUID, payload: WalletCreateRequest
) -> Wallet:
    if await wallet_repository.get_by_company_and_code(session, company_id, payload.code) is not None:
        raise ConflictError("Ce code wallet est déjà utilisé dans cette entreprise.")

    wallet = Wallet(
        company_id=company_id,
        name=payload.name,
        code=payload.code,
        type=payload.type,
        phone=payload.phone,
        currency=payload.currency,
        balance=Decimal("0.00"),
        status=WalletStatus.ACTIVE,
        description=payload.description,
    )
    session.add(wallet)
    await session.flush()

    if payload.initial_balance > 0:
        await apply_movement(
            session,
            wallet,
            MovementDirection.IN,
            payload.initial_balance,
            source_type="wallet_initial",
            source_id=wallet.id,
            created_by_id=created_by_id,
            note="Solde initial",
        )

    await session.commit()
    return wallet


async def list_wallets(session: AsyncSession, company_id: uuid.UUID) -> list[Wallet]:
    return await wallet_repository.list_by_company(session, company_id)


async def get_wallet(session: AsyncSession, company_id: uuid.UUID, wallet_id: uuid.UUID) -> Wallet:
    wallet = await wallet_repository.get_by_company_and_id(session, company_id, wallet_id)
    if wallet is None:
        raise NotFoundError("Wallet introuvable.")
    return wallet


async def update_wallet(
    session: AsyncSession, company_id: uuid.UUID, wallet_id: uuid.UUID, payload: WalletUpdateRequest
) -> Wallet:
    wallet = await get_wallet(session, company_id, wallet_id)

    if payload.name is not None:
        wallet.name = payload.name
    if payload.phone is not None:
        wallet.phone = payload.phone
    if payload.description is not None:
        wallet.description = payload.description

    await session.commit()
    return wallet


async def set_wallet_status(
    session: AsyncSession, company_id: uuid.UUID, wallet_id: uuid.UUID, status: WalletStatus
) -> Wallet:
    wallet = await get_wallet(session, company_id, wallet_id)
    wallet.status = status
    await session.commit()
    return wallet


async def list_wallet_movements(
    session: AsyncSession, company_id: uuid.UUID, wallet_id: uuid.UUID
) -> list[WalletMovement]:
    await get_wallet(session, company_id, wallet_id)
    return await wallet_movement_repository.list_by_wallet(session, wallet_id)
